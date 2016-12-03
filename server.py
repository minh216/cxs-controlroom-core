from os import environ

import asyncio

import functools

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

import importlib, controllers

controller_mods = {}
for submodule in controllers.__all__:
    controller_mods[submodule] = importlib.import_module("controllers.{}".format(submodule))

import json

class ControlroomAPI(ApplicationSession):
    """
        An application component that publishes motor state, configuration
        changes, as well as global configuration changes
    """

    def publish_measurements(self, args):
        print("Hola")
        print(args)
        print(self)
        self.publish('com.controlroom.measurements', args)


    def __init__(self, conf):
        super(ControlroomAPI, self).__init__(conf)
        self._config = {}
        self.controllers = {}


    """
        gather all data from all controllers controlled by this node.
        Should be used sparingly, please rely on publish events
    """
    def get_telemetry():
        pass

    def set_param(id, params):
        pass

    async def describe(self):
        return self._config

    def echo():
        return self.session

    async def onJoin(self, details):
        with open("controllers.json", "r") as f:
            controllers =  json.load(f)
            for controller in controllers:
                print(controller)
                print(controller_mods[controller])
                self.controllers[controller] = controller_mods[controller].Controller(controllers[controller], cbs={"measurements": self.publish_measurements})
                # Controller has executed connection, login, self-description
        self.register(self.describe, 'com.controlroom.{}.describe'.format(details.session))
        self.register(self.get_telemetry, 'com.controlroom.{}.get_telemetry'.format(details.session))
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("AUTOBAHN_ROUTER", u"ws://localhost:8080/ws"),
        u"controlroom"
    )
    runner.run(ControlroomAPI)
