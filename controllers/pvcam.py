from .controller import Controller,DetectorController
from ctypes import *
import attr
import asyncio
import time
import numpy
from PIL import Image
import pvcam_h as pv
class PVCamDLL(CDLL):
    pass
    """
    Minimum viable product (iter 0):
    1. inits and deinits connection to camera. Done
    2. Opens camera connection. Done
    3. temperature monitor loop.
    4. acquire image.
    (iter 1):
    1. Get a parameter
    2. Set a parameter
    3. Make parameter transactions safe
    (iter 2):
    1. Deal with connection loss, sanitize inputs
    2. Enforce order restrictions where required
    """
    def __init__(self):
        self.raw1394 = CDLL("libraw1394.so.11", RTLD_GLOBAL)
        CDLL.__init__(self, "libpvcam.so", RTLD_GLOBAL)
        self.pl_pvcam_init()
        # Init complete
    
    def reinit(self):
        self.pl_pvcam_init()
        self.pl_pvcam_uninit()

    
    def __del__(self):
        self.pl_pvcam_uninit()

@attr.s
class Controller(Controller):
    config = attr.ib()
    cbs = attr.ib(default=None)
    rpc_target = attr.ib(default=None)
    pvcam = attr.ib()
    _handle = attr.ib()
    temperature = attr.ib(default=None)
    status_poll = attr.ib()
    metadata = attr.ib()
    acquire_lock = attr.ib()
    settings = attr.ib()
    @handle.default
    def gen_handle(self):
        return self.cam_open(self.config['name'], pv.OPEN_EXCLUSIVE)
    @pvcam.default
    def instantiate_dll(self):
        return PVCamDLL()

    @status_poll.default
    def def_status_poll(self):
        if 'status_poll' in self.config.keys():
            return self.config['status_poll']
        return 1
    @metadata.default
    def get_metadata(self):
        sensor_size = {
            "width": self.get_param(pv.PARAM_SER_SIZE, pv.ATTR_DEFAULT),
            "height": self.get_param(pv.PARAM_PAR_SIZE, pv.ATTR_DEFAULT)
        }
        chip = self.get_param(pv.PARAM_CHIP_NAME)
         if "InGaAs" in chip:
            # InGaAs detectors don't support binning (written in the
            # specification). In practice, it stops sending images if binning > 1.
            max_binning =  {"width": 1, "height": 1}
        else:
            max_binning = sensor_size
        metadata = {
            "sensor_dimensions": sensor_size,
            "min_resolution": {
                "width": self.get_param(pv.PARAM_SER_SIZE, pv.ATTR_MIN),
                "height": self.get_param(pv.PARAM_PAR_SIZE, pv.ATTR_MIN)
            },
            "pixel_dimensions": {
                "width": self.get_param(pv.PARAM_PIX_SER_DIST, pv.ATTR_DEFAULT) * 1e-9,
                "height": self.get_param(pv.PARAM_PIX_PAR_DIST, pv.ATTR_DEFAULT) * 1e-9
            },
            "temperature_range": {
                "min": self.get_param(pv.PARAM_TEMP_SETPOINT, pv.ATTR_MIN) / 100,
                "max": self.get_param(pv.PARAM_TEMP_SETPOINT, pv.ATTR_MAX) / 100
            },
            "readout_rates": self._getAvailableReadoutRates(),
            "max_binning": max_binnings
        }
        return metadata

    def _getAvailableReadoutRates(self):
        """
        Find the readout rates supported by the device
        returns (dict int -> float): for each index: frequency in Hz
        Note: this is for the current output amplifier and bit depth
        """
        # It depends on the port (output amplifier), bit depth, which we
        # consider both fixed.
        # PARAM_PIX_TIME (ns): the time per pixel
        # PARAM_SPDTAB_INDEX: the speed index
        # The only way to find out the rate of a speed, is to set the speed, and
        # see the new time per pixel.
        # Note: setting the spdtab idx resets the gain

        mins = self.get_param(pv.PARAM_SPDTAB_INDEX, pv.ATTR_MIN)
        maxs = self.get_param(pv.PARAM_SPDTAB_INDEX, pv.ATTR_MAX)
        # save the current value
        current_spdtab = self.get_param(pv.PARAM_SPDTAB_INDEX)
        current_gain = self.get_param(pv.PARAM_GAIN_INDEX)

        rates = {}
        for i in range(mins, maxs + 1):
            # Try with this given speed tab
            self.set_param(pv.PARAM_SPDTAB_INDEX, i)
            pixel_time = self.get_param(pv.PARAM_PIX_TIME) # ns
            if pixel_time == 0:
                logging.warning("Camera reporting pixel readout time of 0 ns!")
                pixel_time = 1
            rates[i] = 1 / (pixel_time * 1e-9)

        # restore the current values
        self.set_param(pv.PARAM_SPDTAB_INDEX, current_spdtab)
        self.set_param(pv.PARAM_GAIN_INDEX, current_gain)
        return rates
    @acquire_lock.default
    def gen_acquire_lock(self):
        return asyncio.Lock()
    @settings.default
    def gen_settings(self):
        return self.config['defaults']

    # Init
    def __attrs_post_init__(self):
        # Register rpcs
        rpc_target.register(self.describe,f"{rpc_target.namespace}.princeton.describe")
        rpc_target.register(self.acquire, f"{rpc_target.namespace}.princetion.acquire")
        # Add generic settings update RPC

    # TODO: flesh out, with live reflection of parameter attributes
    def describe(self):
        return {**self.config, **{"metadata": self.metadata}}

    # Boilerplate/low level

    def cam_get_name(self, num):
        """
        return the name, from the device number
        num (int >= 0): camera number
        return (string): name
        """
        assert(num >= 0)
        cam_name = create_string_buffer(pv.CAM_NAME_LEN)
        self.pvcam.pl_cam_get_name(num, cam_name)
        return cam_name.value

    def cam_open(self, name, mode):
        """
        Reserve and initializes the camera hardware
        name (string): camera name
        mode (int): open mode
        returns (int): handle
        """
        handle = c_int16()
        self.pvcam.pl_cam_open(name, byref(handle), mode)
        return handle

    pv_type_to_ctype = {
         pv.TYPE_INT8: c_int8,
         pv.TYPE_INT16: c_int16,
         pv.TYPE_INT32: c_int32,
         pv.TYPE_UNS8: c_uint8,
         pv.TYPE_UNS16: c_uint16,
         pv.TYPE_UNS32: c_uint32,
         pv.TYPE_UNS64: c_uint64,
         pv.TYPE_FLT64: c_double, # hopefully true on all platforms?
         pv.TYPE_BOOLEAN: c_byte,
         pv.TYPE_ENUM: c_uint32,
         }
    def get_param(self, param, value=pv.ATTR_CURRENT):
        """
        Read the current (or other) value of a parameter.
        Note: for the enumerated parameters, this it the actual value, not the
        index.
        param (int): parameter ID (cf pv.PARAM_*)
        value (int from pv.ATTR_*): which value to read (current, default, min, max, increment)
        return (value): the value of the parameter, whose type depend on the parameter
        """
        assert(value in (pv.ATTR_DEFAULT, pv.ATTR_CURRENT, pv.ATTR_MIN,
                         pv.ATTR_MAX, pv.ATTR_INCREMENT))

        # find out the type of the parameter
        tp = c_uint16()
        self.pvcam.pl_get_param(self._handle, param, pv.ATTR_TYPE, byref(tp))
        if tp.value == pv.TYPE_CHAR_PTR:
            # a string => need to find out the length
            count = c_uint32()
            self.pvcam.pl_get_param(self._handle, param, pv.ATTR_COUNT, byref(count))
            content = create_string_buffer(count.value)
        elif tp.value in self.pv_type_to_ctype:
            content = self.pv_type_to_ctype[tp.value]()
        elif tp.value in (pv.TYPE_VOID_PTR, pv.TYPE_VOID_PTR_PTR):
            raise ValueError("Cannot handle arguments of type pointer")
        else:
            raise NotImplementedError("Argument of unknown type %d" % tp.value)

        # read the parameter
        self.pvcam.pl_get_param(self._handle, param, value, byref(content))
        return content.value

    def get_param_access(self, param):
        """
        gives the access rights for a given parameter.
        param (int): parameter ID (cf pv.PARAM_*)
        returns (int): value as in pv.ACC_*
        """
        rights = c_uint16()
        self.pvcam.pl_get_param(self._handle, param, pv.ATTR_ACCESS, byref(rights))
        return rights.value

    def set_param(self, param, value):
        """
        Write the current value of a parameter.
        Note: for the enumerated parameter, this is the actual value to set, not
        the index.
        param (int): parameter ID (cf pv.PARAM_*)
        value (should be of the right type): value to write
        Warning: it seems to not always complain if the value written is incorrect,
        just using default instead.
        """
        # find out the type of the parameter
        tp = c_uint16()
        self.pvcam.pl_get_param(self._handle, param, pv.ATTR_TYPE, byref(tp))
        if tp.value == pv.TYPE_CHAR_PTR:
            content = str(value)
        elif tp.value in self.pv_type_to_ctype:
            content = self.pv_type_to_ctype[tp.value](value)
        elif tp.value in (pv.TYPE_VOID_PTR, pv.TYPE_VOID_PTR_PTR):
            raise ValueError("Cannot handle arguments of type pointer")
        else:
            raise NotImplementedError("Argument of unknown type %d" % tp.value)

        self.pvcam.pl_set_param(self._handle, param, byref(content))

    def get_enum_available(self, param):
        """
        Get all the available values for a given enumerated parameter.
        param (int): parameter ID (cf pv.PARAM_*), it must be an enumerated one
        return (dict (int -> string)): value to description
        """
        count = c_uint32()
        self.pvcam.pl_get_param(self._handle, param, pv.ATTR_COUNT, byref(count))

        ret = {} # int -> str
        for i in range(count.value):
            length = c_uint32()
            content = c_uint32()
            self.pvcam.pl_enum_str_length(self._handle, param, i, byref(length))
            desc = create_string_buffer(length.value)
            self.pvcam.pl_get_enum_param(self._handle, param, i, byref(content),
                                         desc, length)
            ret[content.value] = desc.value
        return ret

    def exp_check_status(self):
        """
        Checks the status of the current exposure (acquisition)
        returns (int): status as in pv.* (cf documentation)
        """
        status = c_int16()
        byte_cnt = c_uint32() # number of bytes already acquired: unused
        self.pvcam.pl_exp_check_status(self._handle, byref(status), byref(byte_cnt))
        return status.value

    def _buffer_as_array(self, cbuffer, size):
        """
        Converts the buffer allocated for the image as an ndarray. zero-copy
        size (2-tuple of int): width, height
        return an ndarray
        """
        p = cast(cbuffer, POINTER(c_uint16))
        ndbuffer = numpy.ctypeslib.as_array(p, (size[1], size[0])) # numpy shape is H, W
        return ndbuffer

    # Always run this in an executor
    async def _acquire(self):
        cbuffer = None
        with self.acquire_lock:
            self._start_acquisition(cbuffer)
            start = time.time()
            path = f"{self.config['id']}.{start}.tiff"
            expected_end = start + duration
            timeout = expected_end + 1
            array = self._buffer_as_array(cbuffer, size, metadata)
            status = self.exp_check_status()
            while status in STATUS_IN_PROGRESS:
                now = time.time()
                if now > timeout:
                    raise IOError("Timeout after %g s" % (now - start))
                # exponential backoff
                asyncio.sleep((now-start-timeout)/2)
                status = self.exp_check_status()
            # Now we've got a (H,W) ndarray, convert and write it to disk
            out = Image.fromarray(array.astype('uint8')).convert('RGBA')
            out.save(path)
            return path

    async def acquire(self):
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self._acquire)
        acquisition_path = await future
        self.cbs['status']({"id": self.conf['id'], "telemetry": {
            "acquisition": acquisition_path
        }})
        return acquisition_path
    # Concrete actions

    def get_temperature(self):
        """
        returns (float) the current temperature of the captor in C
        """
        # it's in 1/100 of C
        temp = self.get_param(pv.PARAM_TEMP) / 100
        return temp

    async def start_status_loop(self):
        
        while True:
            # Monolithic controller, like Marlabs
            self.temperature = self.get_temperature()
            self.cbs['status']({"id": self.conf['id'], "telemetry": {
                "temperature": self.temperature
            }})
            await asyncio.sleep(self.status_poll)
