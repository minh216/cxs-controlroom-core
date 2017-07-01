import asyncio
from .controller import TriggerController, locks

class TriggerController(TriggerController):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()