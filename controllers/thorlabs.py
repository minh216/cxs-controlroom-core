from .controller import MotorController,Controller
import pyAPT
import pylibftdi
import jsonpickle

class Controller(Controller):

    def __init__(self, conf, cbs=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.controllers = {}

        if True:
            # Get info of all axes, create a controller for each
            drv = pylibftdi.Driver()
            controllers = drv.list_devices()
            for controller in controllers:
                id = controller[2].decode('latin-1')
                self.controllers[id] = MotorController({"serial_number": id, "label": None}, cbs=self.cbs)

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

    def notifyStatus(self):
        # print(self.serial_number)
        self.cbs['status']({"id": self.serial_number, "status": self.status})

    def __init__(self, conf, cbs=None):
        super(MotorController, self).__init__(conf['serial_number'], conf['label'])
        self.cbs = cbs
        self._status = None
        self.status = super(MotorController, self).status()
        print(super(MotorController, self).status().shortstatus)
        # Get initial status, measurements
        self.cbs['status']({"id": self.serial_number, "status": self.status})

    def goto(self, abs_pos_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(abs_pos_mm, channel=1, wait=True)
        self.status = status

    def move(self, dist_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(abs_pos_mm, channel=1, wait=True)
        self.status = status

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = self.status_transform(status)
        self.cbs['status']({"id": self.serial_number, "status": self._status})
