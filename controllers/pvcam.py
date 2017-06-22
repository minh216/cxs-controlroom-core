from .controller import Controller, DetectorController, locks
from ctypes import *
CDLL('libraw1394.so', mode=RTLD_GLOBAL)
CDLL('libpvcam.so', mode=RLTD_GLOBAL)

class Controller(Controller):

    def __init__(self, conf, cbs=None, rpc_target=None):
        super(Controller, self).__init__()
        self.cbs = cbs
        self.config = conf
        self.rpc_target = rpc_target
        self.driver = LoadLibrary('libpvcam.so')
        self.driver.pl_pvcam_init()

    def _setup(self):
        self.driver.pl_exp_init_seq()

        self.driver.pl_exp_setup_seq( hCam, 1, 1, &region, TIMED_MODE, 100, &size )

    def _acquire_single(self):
        self.driver.pl_exp_start_seq(hCam, frame)

    def _teardown(self):
        self.driver.pl_exp_finish_seq( hCam, frame, 0)
        self.driver.pl_exp_uninit_seq()

    def scan(self, axis_uris=[]):
        pass

    """
       Acquire a series of frames.
    """
    def _acquire(self):

        while( numberframes ) {
            self.driver.pl_exp_start_seq(hCam, frame )
            # wait for data or error
            while( self.driver.pl_exp_check_status( hCam, &status, &not_needed ) and
            (status != READOUT_COMPLETE && status != READOUT_FAILED) )
            # Check Error Codes 
            if( status == READOUT_FAILED ) {
            printf( "Data collection error: %i\n", pl_error_code() )
            break
            }
            # frame now contains valid data
            printf( "Center Three Points: %i, %i, %i\n",
            frame[size/sizeof(uns16)/2 - 1],
            frame[size/sizeof(uns16)/2],
            frame[size/sizeof(uns16)/2 + 1] )
            numberframes--;
            printf( "Remaining Frames %i\n", numberframes );
        }# End while


    def acquire(self):
        self.init()
        self._acquire()
        self.uninit()

    """
       As far as we're aware, PVCAM doesn't like long, idle connections.
    """
    def init(self):
        self.driver.pl_pvcam_init()
        self.driver.pl_cam_get_name( 0, cam_name )
        self.driver.pl_cam_open(cam_name, &hCam, OPEN_EXCLUSIVE )

    def uninit(self):
        self.driver.pl_cam_close( hCam )
        self.driver.pl_pvcam_uninit()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        pass