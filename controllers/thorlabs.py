from .controller import MotorController,Controller
import pyAPT
import pylibftdi

class Controller(Controller):

    def __init__(self, conf, cbs=None):
        try:
            self.controllers = {}
            super(Motor, self).__init__()
        except Exception as e:
            pass


        if False:
            # Get info of all axes, create a controller for each
            drv = pylibftdi.Driver()
            controllers = drv.list_devices()
            for controller in controllers:
                id = controller[2].decode('latin-1')
                self.controllers[id] = MotorController({"serial_number": id, "label": None})

    def __del__(self):
        pass

class MotorController(pyAPT.controller.Controller):

    def __init__(self, conf):
        super(MotoController, self).__init__(conf.serial_number, conf.label)

    def goto(self, abs_pos_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(abs_pos_mm, channel=1, wait=True)
        self.cbs['measurements'](status)
