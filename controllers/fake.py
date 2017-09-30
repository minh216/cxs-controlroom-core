from .controller import Controller, SourceController, CameraController, DetectorController, MotorController, locks
import os
import asyncio
import time
from functools import *
from math import copysign, floor
import numpy
from PIL import Image
import attr
from autobahn.wamp.exception import ApplicationError

class Controller(Controller):
    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.config = conf
        self.cbs = cbs
        self.status_poll = conf['status_poll']
        self.controllers = {}
        for controller in conf['controllers']:
            if controller['type'] == 'motor':
                self.controllers[controller['id']] = MotorController(controller, self.cbs)
                rpc_target.register(self.controllers[controller['id']].absolute_move,
                    f"{rpc_target.namespace}.fake.{controller['id']}.absolute_move")
                rpc_target.register(self.controllers[controller['id']].relative_move,
                    f"{rpc_target.namespace}.fake.{controller['id']}.relative_move")
                rpc_target.register(self.controllers[controller['id']].home,
                    f"{rpc_target.namespace}.fake.{controller['id']}.home")
                rpc_target.register(self.controllers[controller['id']].disable,
                    f"{rpc_target.namespace}.fake.{controller['id']}.disable")
                rpc_target.register(self.controllers[controller['id']].abort,
                    f"{rpc_target.namespace}.fake.{controller['id']}.abort")
            elif controller['type'] == 'source':
                self.controllers[controller['id']] = SourceController(controller, self.cbs)
                rpc_target.register(partial(self.controllers[controller['id']].set_xray_state, True),
                    f"{rpc_target.namespace}.fake.{controller['id']}.xray.on")
                rpc_target.register(partial(self.controllers[controller['id']].set_xray_state, False),
                    f"{rpc_target.namespace}.fake.{controller['id']}.xray.off")
            elif controller['type'] == 'camera':
                self.controllers[controller['id']] = CameraController(controller, self.cbs)
                rpc_target.register(self.controllers[controller['id']].capture,
                    f"{rpc_target.namespace}.fake.{controller['id']}.capture")
            else:
                continue
            rpc_target.register(self.controllers[controller['id']].describe,
                f"{rpc_target.namespace}.fake.{controller['id']}.describe")
        
        if rpc_target:
            rpc_target.register(self.describe, f"{rpc_target.namespace}.fake.describe")

    def describe(self):
        return self.config

    async def start_status_loop(self):
        while True:
            await asyncio.wait(map(lambda c: c.pub_status(), self.controllers.values()))
            await asyncio.sleep(self.status_poll)

class CameraController(CameraController):
    async def capture(self, exposure):
        if not type(exposure) in [int, float]:
            raise ApplicationError("com.controlroom.type.error", exposure)
        async with self.lock:
            self.status = "acquiring"
            await self.pub_status()
            # generate the file name
            path = f"fake-{time.time()}.png"
            await asyncio.sleep(exposure)
            a = numpy.random.rand(100,100,3) * 255
            out = Image.fromarray(a.astype('uint8')).convert('RGBA')
            out.save(path)
            self.acquisition_path = path
            self.status = "idle"
            await self.pub_status()
        return path
@attr.s
class SourceController(SourceController):
    xray = attr.ib(init=False)
    @xray.default
    def default_x(self):
        return {"state": False} #i.e. off
    async def set_xray_state(self, state):
        if type(state) != bool:
            raise TypeError("Incorrect type!")
        self.xray['state'] = state
    async def pub_status(self):
        self.cbs['status']({"id": self.config['id'], "telemetry": {
            "status": self.status, "xray": self.xray
        }})

class MotorController(MotorController):
    async def abort(self):
        # Our fake abort
        print("ABORT!")
        # set the disabled flag
        self.disabled = True
        # nuke the lock
        if self.lock.locked():
            self.lock.release()
        self.status = "aborted"
        await self.pub_status()

    async def disable(self):
        if self.disabled:
            self.disabled = False
            self.status = "idle"
        else:
            self.disabled = True
            self.status = "disabled"
        if self.lock.locked():
            self.lock.release()
        await self.pub_status()
        
    async def absolute_move(self, ordinate):
        if not self.config['min'] <= ordinate <= self.config['max']:
            raise ValueError("Not in bounds")
        # prevent concurrent moves
        async with self.lock:
            if self.disabled:
                raise Exception("Disabled!")
            self.status = "moving"
            incr = copysign(1, ordinate - self.position)
            for i in range(0, floor(abs(ordinate - self.position))):
                await self.pub_status()
                await asyncio.sleep(1)
                self.position += incr
                await asyncio.sleep(abs(ordinate - self.position))
            self.position = ordinate
            self.status = "idle"
        await self.pub_status()
        return self.position

    async def relative_move(self, offset):
        async with self.lock:
            incr = copysign(1, offset)
            new_pos = self.position + offset
            if not self.config['min'] <= new_pos <= self.config['max']:
                raise ValueError("Not in bounds")
            if self.disabled:
                raise Exception("Disabled!")
            self.status = "moving"
            for i in range(0, floor(abs(offset))):
                await self.pub_status()
                self.position += incr
                await asyncio.sleep(1)
            self.position = new_pos
            self.status = "idle"
        await self.pub_status()
        return self.position

    async def home(self):
        async with self.lock:
            if self.disabled:
                raise Exception("Disabled!")
            self.status = "homing"
            await self.pub_status()
            await asyncio.sleep(abs(self.position))
            self.position = 0
            self.status = "idle"
        await self.pub_status()
