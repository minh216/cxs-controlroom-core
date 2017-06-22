from .controller import Controller, DetectorController, MotorController, locks
import os
from time import sleep
import asyncio
import time
from functools import *

class Controller(Controller):
    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.config = conf
        self.cbs = cbs
        self.status_poll = conf['status_poll']
        self.controllers = {}

    def describe(self):
        return self.config

    async def start_status_loop(self):
        while True:
            for controller in self.controllers.values():
                controller.check_status()
                pass
            await asyncio.sleep(self.status_poll)

    def __del__(self):
        pass

    async def move():
        pass
