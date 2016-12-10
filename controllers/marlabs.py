from .controller import Controller, DetectorController, MotorController
import os
from time import sleep
import asyncio
import functools

class Controller(Controller):

    motors = [
        "PHI",
        "DISTANCE",
        "CHI"
    ]

    def process_status(self, status):
        # strip status message
        pass

    """
        Open up a reader, writer pair to ip:port, awaits data with a minimum
        waiting period if self.status_poll
    """
    async def status_loop(self, ip, port):
        loop = asyncio.get_event_loop()
        self.reader, self.writer = await asyncio.open_connection(ip, port, loop=loop)
        while True:
            status = (await reader.read(4096)).decode()
            self.process_status(status)
            asyncio.sleep(self.status_poll)
        writer.close()


    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.ip = conf.ip
        self.port = conf.port
        self.status_poll = conf.status_poll
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self,status_loop(self.ip, self.port))
        if rpc_target != None:
            for sub in self.motor_controllers:
                rpc_target.register(self.move,
                    "{}.{}.{}.absolute_move".format(rpc_target.namespace, "marlabs", sub))
            rpc_target.register(self.scan,
                "{}.{}.scan".format(rpc_target.namespace, "marlabs"))
            rpc_target.register(self.erase,
                "{}.{}.erase".format(rpc_target.namespace, "marlabs"))

    """
        Constructs the command string, encodes to a byte sequence, and writes it
        to the command socket
    """
    def send_command(self, command):
        self.writer.write("COMMAND {}".format(command).encode())

    def scan(self, params):
        self.send_command("SCAN {}".format(params.join(" ")))

    def erase(self, params):
        self.send_command("ERASE {}".format(params.join(" ")))
