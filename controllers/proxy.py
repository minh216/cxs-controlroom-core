from .controller import Controller, MotorController

class Controller(Controller):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.config = conf
        self.rpc_target = rpc_target

    def http_call(self, command, data):
        self.rpc_target.call(base_uri, method='POST', url=command, params=data)
