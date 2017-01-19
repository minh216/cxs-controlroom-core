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
    async def start_status_loop(self):
        loop = asyncio.get_event_loop()
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port, loop=loop)
        print("connection opened")
        while True:
            status = (await self.reader.read(4096)).decode()
            print(status)
            self.process_status(status)
            print("Helloooo")
            asyncio.sleep(self.status_poll)
        writer.close()

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.ip = conf['ip']
        self.port = conf['port']
        self.status_poll = conf['status_poll']
        if rpc_target != None:
            for sub in self.motors:
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
        self.send_command("SCAN {}".format(" ".join(params)))

    def erase(self, params):
        self.send_command("ERASE {}".format(" ".join(params)))

    def move(self, params):
        self.send_command("MOVE {}".format(" ".join(params)))
