from .controller import Controller, DetectorController, MotorController
import os
from time import sleep

class Controller(Controller):

    def __init__(self, conf, cbs=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        # look for available resources

class Detector(DetectorController):

    def __init__(self, conf, cbs=None):
        super(Detector, self).__init__(conf, cbs)
        # request values

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        self.cbs['status']({"id": self.id, "status": self._status})

    @status.getter
    def status(self):
        return self._status

class Motor(MotorController):

    def __init__(self, conf, cbs=None):
        super(Motor, self).__init__(conf, cbs)

    def notifyStatus(self):
        print("not yet implemented")
        #pyepics status monitoring goes here
        
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        self.cbs['status']({"id": self.id, "status": self._status})
    @status.getter
    def status(self):
        return self._status
