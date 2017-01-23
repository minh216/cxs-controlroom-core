from .controller import MotorController,Controller
import pyAPT
import pylibftdi
import asyncio

class Controller(Controller):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.config = conf
        self.cbs = cbs
        self.status_poll = conf['status_poll']
        self.controllers = {}

        if True:
            # Get info of all axes, create a controller for each
            drv = pylibftdi.Driver()
            controllers = drv.list_devices()
            rpc_target.register(self.describe,
                "{}.thorlabs.describe".format(rpc_target.namespace))
            for controller in controllers:
                id = controller[2].decode('latin-1')
                self.controllers[id] = MotorController({"serial_number": id, "label": None}, cbs=self.cbs, rpc_target=rpc_target)
            self.config['controllers'] = self.generate_config()

    def generate_config(self):
        print(self.controllers)
        ret_val = []
        for i, (k,v) in enumerate(self.controllers.items()):
            ret_val.append({
                "min": v.linear_range[0],
                "max": v.linear_range[1],
                "id": k,
                "name": "Thorlabs Axis {}".format(i),
                "type": "motor",
                "units": "mm",
                "group": "thorlabs"
            })
        return ret_val

    def describe(self):
        return self.config

    async def start_status_loop(self):
        while True:
            for controller in self.controllers.values():
                controller.check_status()
                pass
            await asyncio.sleep(self.status_poll)

    def __del__(self):
        pass

class MotorController(pyAPT.mts50.MTS50):

    def status_transform(self, statusObj):
        print(statusObj)
        return {
            "position": statusObj.position,
            "velocity": statusObj.velocity,
            "position_apt": statusObj.position_apt,
            "velocity_apt": statusObj.velocity_apt
        }

    def check_status(self):
        self.status = super(MotorController, self).status()

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(MotorController, self).__init__(conf['serial_number'], conf['label'])
        self.cbs = cbs
        self._status = None
        self.status = super(MotorController, self).status()
        print(super(MotorController, self).status().shortstatus)
        # Get initial status, measurements
        self.cbs['status']({"id": self.serial_number, "status": self.status})
        rpc_target.register(self.absolute_move, "{}.thorlabs.{}.absolute_move".format(rpc_target.namespace, self.serial_number))
        rpc_target.register(self.relative_move, "{}.thorlabs.{}.relative_move".format(rpc_target.namespace, self.serial_number))
        rpc_target.register(self.home, "{}.thorlabs.{}.home".format(rpc_target.namespace, self.serial_number))

    def absolute_move(self, abs_pos_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(float(abs_pos_mm), channel=1, wait=True)
        self.status = status

    def relative_move(self, dist_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(self.status['position'] + float(dist_mm), channel=1, wait=True)
        self.status = status

    def home(self, velocity=2):
        status = super(MotorController, self).home(velocity=velocity)
        print(status)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = self.status_transform(status)
        self.cbs['status']({"id": self.serial_number, "status": self._status})
