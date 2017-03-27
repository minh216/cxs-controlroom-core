from os import environ, path

import asyncio

import functools

import time
import inspect

from concurrent.futures import ThreadPoolExecutor
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

import importlib, controllers
from socket import socketpair
import json

class ControlroomAgent(ApplicationSession):
    """
        An application component that takes command sequences, locks the 
        appropriate entities and executes them in series (with minor parallel 
        bubbles due to asynchronous invocation).
    """

    def __init__(self, conf):
        pass
    def echo():
        return self.session

    """
       Takes a json payload of command/parameter pairs.
       Inspect data/example_command.json for details
    """
    async def execute_commands(self, command_payload):
        pass

    async def onJoin(self, details):
        self.register(self.execute_commands, "{}.scan".format(self.namespace))
        self.subscribe(self.namespace+'.describe', self.http_register)
        while True:
            # for controller in self.controllers.values():
            #     for sub in controller.controllers.values():
            #         sub.notifyStatus()
                # all(map(lambda x: x.notifyStatus(), controller.controllers.values()))
            await asyncio.sleep(1)

if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("AUTOBAHN_ROUTER", u"ws://localhost:8080/ws"),
        u"controlroom"
    )
    runner.run(ControlroomAPI)
