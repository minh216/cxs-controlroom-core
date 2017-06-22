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
        self.namespace = "com.controlroom"
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
        return list(self.controllers.keys())

    def echo():
        return self.session

    def http_register(self, data):
        deserialized = json.loads(data)
        if deserialized['name'] in self.controllers.keys():
            pass
        else:
            self.controllers[deserialized['name']] = controller_mods['proxy'].Controller(deserialized)

    async def onJoin(self, details):
        callback_collection = {
            "measurements": (lambda msg: self.publish(self.namespace+'.measurements', msg)),
            "status": (lambda msg: self.publish(self.namespace+'.status', msg)),
            "configuration": (lambda msg: self.publish(self.namespace+'.configuration', msg))
        }
        with open("controllers.json", "r") as f:
            controllers =  json.load(f)
            for controller in controllers:
                self.controllers[controller] = controller_mods[controller].Controller(controllers[controller], cbs=callback_collection, rpc_target=self)

        self.register(self.describe, '{}.describe'.format(self.namespace))
        self.register(self.get_telemetry, '{}.get_telemetry'.format(self.namespace))
        self.subscribe(self.http_register, self.namespace+'.describe')
        print(self.controllers)
        executor = ThreadPoolExecutor(len([self.controllers.values()]))
        loop = asyncio.get_event_loop()

        for controller in self.controllers.values():
            print(controller)
            boo = asyncio.ensure_future(controller.start_status_loop(), loop=loop)
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
