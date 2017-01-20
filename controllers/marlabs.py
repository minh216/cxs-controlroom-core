from .controller import Controller, DetectorController, MotorController
import os
from time import sleep
import asyncio
import time
import functools

class Controller(Controller):

    motors = [
        "PHI",
        "DISTANCE",
        "CHI"
    ]

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
            self.status = status
            asyncio.sleep(self.status_poll)
        writer.close()

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.ip = conf['ip']
        self.serial_number = conf['serial_number']
        self.port = conf['port']
        self.status_poll = conf['status_poll']
        self._status = None
        self.status = ""

        if rpc_target != None:
            for sub in self.motors:
                rpc_target.register(self.move,
                    "{}.{}.{}.absolute_move".format(rpc_target.namespace, "marlabs", sub))
                rpc_target.register(self.init,
                    "{}.{}.{}.init".format(rpc_target.namespace, "marlabs", sub))
            rpc_target.register(self.scan,
                "{}.{}.scan".format(rpc_target.namespace, "marlabs"))
            rpc_target.register(self.erase,
                "{}.{}.erase".format(rpc_target.namespace, "marlabs"))
            rpc_target.register(self.init,
                "{}.{}.init".format(rpc_target.namespace, "marlabs"))
            rpc_target.register(self.open_shutter,
                "{}.{}.shutter.open".format(rpc_target.namespace, "marlabs"))
            rpc_target.register(self.close_shutter,
                "{}.{}.shutter.close".format(rpc_target.namespace, "marlabs"))

    """
        Constructs the command string, encodes to a byte sequence, and writes it
        to the command socket
    """
    def send_command(self, command):
        self.writer.write("COMMAND {}".format(command).encode())

    def scan(self, file_name, resolution=''):
        now = int(time.time())
        self.send_command("SCAN {}_{}.mar2300 {}".format(file_name, now, resolution))

    def erase(self, params):
        self.send_command("ERASE {}".format(" ".join(params)))

    def move(self, axis, value):
        self.send_command("MOVE {} {}".format(axis, value))

    def init(self, axis, end):
        if not end.upper() in ["MIN", "MAX", "REF"]:
            return False
        self.send_command("INIT {} {}".format(axis, end.upper()))

    def open_shutter(self):
        self.send_command("SHUTTER OPEN")

    def close_shutter(self):
        self.send_command("SHUTTER CLOSE")

    def status_transform(self, status):
        return status

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = self.status_transform(status)
        self.cbs['status']({"id": self.serial_number, "status": self._status})
