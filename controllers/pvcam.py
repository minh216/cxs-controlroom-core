from .controller import Controller, DetectorController
from ctypes import *
CDLL('pvcam.so')
class Controller(Controller):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.config = conf
        self.rpc_target = rpc_target
        self.driver = LoadLib('pvcam.so')
        self.driver.pl_pvcam_init()
        self.driver.

    def acquire(self):
        pass

        
    def acquire_wrapper(self):
        self.driver.pl_pvcam_init()
        self.driver.pl_cam_get_name( 0, cam_name )
        self.driver.pl_cam_open(cam_name, &hCam, OPEN_EXCLUSIVE )
        AcquireStandard( hCam )
        self.driver.pl_cam_close( hCam )
        self.driver.pl_pvcam_uninit()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        pass