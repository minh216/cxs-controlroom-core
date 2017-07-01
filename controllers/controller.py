from functools import wraps

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

def locks(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print('Calling decorated function')
        obj = args[0] if len(args) > 0 else None
        if obj and hasattr(obj, "lock"):
            obj.acquire()
        res = f(*args, **kwargs)
        if obj and hasattr(obj, "lock"):
            obj.lock.release()
    return wrapper

class DetectorController(Controller):

    def __init__(self, conf, cbs=None):
        super(DetectorController, self).__init__()
        self.cbs = cbs

class TriggerController(Controller):

    def __init__(self, conf, cbs=None):
        super(TriggerController, self).__init__()
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
