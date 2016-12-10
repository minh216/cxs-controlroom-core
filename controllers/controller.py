class Controller(object):

    """
        Standard procedure:
        1. connect, assign callbacks
        2. discover groups/subcontrollers, assign callback (refs to parent cb)
        3. children auto-trigger publish cb, reflect initial to properties
    """
    def __init__(self):
        self.controllers = {}
        self.cbs = {}

class DetectorController(Controller):

    def __init__(self, conf, cbs=None):
        super(DetectorController, self).__init__()
        self.cbs = cbs

class MotorController(Controller):

    def __init__(self, conf, cbs=None):
        super(MotorController, self).__init__()
        self.cbs = cbs

    @property
    def velocity(self):
        return self._velocity

    @velocity.setter
    def velocity(self, velocity):
        self._velocity = velocity

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
