from functools import wraps
import attr
import asyncio

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

@attr.s
class CameraController(Controller):
    config = attr.ib()
    cbs = attr.ib(default=None)
    rpc_target = attr.ib(default=None)
    status = attr.ib(default="idle")
    acquisition_path = attr.ib(default=attr.Factory(str))
    disabled = attr.ib(default=False)
    lock = attr.ib(init=False)
    @lock.default
    def gen_lock(self):
        return asyncio.Lock()
    async def describe(self):
        return self.config
    async def pub_status(self):
        self.cbs['status']({"id": self.config['id'], "telemetry": {
            "status": self.status, "acquisition": self.acquisition_path
        }})

@attr.s
class SourceController(Controller):
    config = attr.ib()
    cbs = attr.ib(default=None)
    rpc_target = attr.ib(default=None)
    status = attr.ib(default="inactive")
    disabled = attr.ib(default=False)
    lock = attr.ib(init=False)
    @lock.default
    def gen_lock(self):
        return asyncio.Lock()
    async def describe(self):
        return self.config
    # Override this in subclasses
    async def pub_status(self):
        self.cbs['status']({"id": self.config['id'], "telemetry": {
            "status": self.status
        }})


class TriggerController(Controller):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(TriggerController, self).__init__()
        self.cbs = cbs

@attr.s
class DetectorController(Controller):
    pass

@attr.s
class MotorController(Controller):
    config = attr.ib()
    cbs = attr.ib(default=None)
    rpc_target = attr.ib(default=None)
    position = attr.ib(init=False, default=attr.Factory(float))
    velocity = attr.ib(init=False, default=attr.Factory(float))
    status = attr.ib(default="idle")
    disabled = attr.ib(default=False)
    # lock required for everything except abort
    lock = attr.ib(init=False)
    @lock.default
    def gen_lock(self):
        return asyncio.Lock()

    async def pub_status(self):
        self.cbs['status']({"id": self.config['id'], "telemetry": {
            "status": self.status, "position": self.position, "velocity": self.velocity
        }})

    async def describe(self):
        return self.config

    def get_attrs(self):
        return attr.asdict(self)