from os import environ, path

import asyncio

import functools

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

import importlib, controllers

import json

controller_mods = {}

for submodule in controllers.__all__:
    controller_mods[submodule] = importlib.import_module("controllers.{}".format(submodule))

if path.isfile("module_imports.json"):
    with open("module_imports.json", "r") as f:
        for module in json.load(f):
            importlib.import_module(module)

class ControlroomAPI(ApplicationSession):
    """
        An application component that publishes motor state, configuration
        changes, as well as global configuration changes
    """

    def __init__(self, conf):
        super(ControlroomAPI, self).__init__(conf)
        self._config = {}
        self.controllers = {}



    """
        Trigger all controllers to publish their configurations
    """
    def get_configuration():
        all(map(lambda x: x.publish_configuration(), self.controllers.values()))
        return "subscribe to com.controlroom.configuration for config updates"

    """
        Trigger all controllers to publish their current telemetry
    """
    def get_telemetry():
        """
            Loop through controllers, trigger all publishes
        """
        all(map(lambda x: x.publish_telemetry(), self.controllers.values()))
        return "subscribe to com.controlroom.measurements for telemetry"


    def set_param(id, param_name, param_value):
        """
            Loop through controllers, check for presence of controller<id>.
            Set the parameter
        """

    async def describe(self):
        return self._config

    def echo():
        return self.session

    async def onJoin(self, details):
        prefix = "com.controlroom"

        callback_collection = {
            "measurements": (lambda msg: self.publish(prefix+'.measurements', msg)),
            "status": (lambda msg: self.publish(prefix+'.status', msg))
            "configuration": (lambda msg: self.publish(prefix+'.configuration', msg))
        }
        with open("controllers.json", "r") as f:
            controllers =  json.load(f)
            for controller in controllers:
                print(controller)
                print(controller_mods[controller])
                self.controllers[controller] = controller_mods[controller].Controller(controllers[controller], cbs=callback_collection)
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
