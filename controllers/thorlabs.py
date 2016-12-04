from .controller import MotorController,Controller
import pyAPT
import pylibftdi

class Controller(Controller):

    def __init__(self, conf, cbs=None):
        super(Controller, self).__init__()
        self.cbs = cbs

        if False:
            # Get info of all axes, create a controller for each
            drv = pylibftdi.Driver()
            controllers = drv.list_devices()
            for controller in controllers:
                id = controller[2].decode('latin-1')
                self.controllers[id] = MotorController({"serial_number": id, "label": None}, cbs=self.cbs)

    def __del__(self):
        pass

class MotorController(pyAPT.controller.Controller):

    def __init__(self, conf, cbs=None):
        super(MotoController, self).__init__(conf.serial_number, conf.label)
        self.cbs = cbs
        # Get initial status, measurements
        self.cbs['status']({"id": self.id, "status": self._status})

    def goto(self, abs_pos_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(abs_pos_mm, channel=1, wait=True)
        self.status = status

    @property
    def status(self):
        return self._status

    @property.setter
    def status(self, status):
        self._status = status
        self.cbs['status']({"id": self.id, "status": self._status})

    @property.getter
    def status(self):
        return self._status
