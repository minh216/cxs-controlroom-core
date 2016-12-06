from newportXpsQ8.driver import XPS
from .controller import Controller, MotorController

class Motor(MotorController):

    def __init__(self):
        super(Motor, self).__init__()

class Controller(Controller, XPS):

    def __init__(self, conf, cbs=None):
        super(Controller, self).__init__()
        try:
            self.socketId = self.TCP_ConnectToServer(conf.ip, conf.port, conf.timeout)
            self.Login(self.socketId, conf.username, conf.password)
        except Exception as e:
            pass

    def __del__(self):
        super(Controller, self).__del__()
        try:
            self.TCP_CloseSocket(self.socketId)
        except Exception as e:
            pass
