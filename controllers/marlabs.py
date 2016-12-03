from .controller import Controller, DetectorController, MotorController
import os
from time import sleep

class Controller(Controller):

    def __init__(self, conf, cbs=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        # look for available resources

        self.cbs['measurements']({"hello": "world"})

class Detector(DetectorController):

    def __init__(self):
        super(MarlabsDetector, self).__init__()

class Motor(MotorController):

    def __init__(self):
        super(MarlabsMotor, self).__init__()
