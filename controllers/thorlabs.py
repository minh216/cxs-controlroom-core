from .controller import MotorController,Controller
import pyAPT
import pylibftdi

class Controller(Controller):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.controllers = {}

        if True:
            # Get info of all axes, create a controller for each
            drv = pylibftdi.Driver()
            controllers = drv.list_devices()
            for controller in controllers:
                id = controller[2].decode('latin-1')
                self.controllers[id] = MotorController({"serial_number": id, "label": None}, cbs=self.cbs, rpc_target=rpc_target)

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
        self.cbs['status']({"id": self.serial_number, "status": self.status})

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

    def absolute_move(self, abs_pos_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(abs_pos_mm, channel=1, wait=True)
        self.status = status

    def relative_move(self, dist_mm, channel=1, wait=True):
        status = super(MotorController, self).goto(self.telemetry.position + dist_mm, channel=1, wait=True)
        self.status = status

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = self.status_transform(status)
        self.cbs['status']({"id": self.serial_number, "status": self._status})
