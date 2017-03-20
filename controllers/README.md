# Controller specific documentation

## Marlabs
Ensure the mar345dtb software is running before you start server.py; the IP
is static due to limitations of the mar345 hardware, but the port can be 
configured - make sure this matches the one in your controllers.json file.

## Princeton PVCAM
PVCAM is only supported on 32-bit kernels. The Windows on Windows subsystem (WOW64) can be used to host a surrogate process wrapping the 32-bit PVCAM dll (i.e. a set of API endpoints redirecting to the DLL endpoints), which can then be called via interprocess communication channels (out of process COM ports for the most part). A less work-intensive alternative on a Windows host is to simply run a lightweight 32-bit virtual machine, to which one simply provides access to the host USB hardware and on which one installs the pvcam CDLL and whatever application that wraps said CDLL.

On a Linux host, cross-architecture libraries can be installed (e.g. libc6:i386 alongside lbc6:amd64). If your application includes a 32-bit CDLL via the usual method (ctypes in python, for example), it must also be built for the same architecture (more specifically, it must reference the same ld interpreter - e.g ld-linux-amd64.so.3 for 64 bit, ld-linux-x86.so.3 for x86). If the bulk of your application depends on 64 bit libraries (not inconceivable if it uses a lot of RAM or involves a lot of operations sensitive to the instruction set improvements made between x86 and amd64), it is best to write a small wrapper program that communicates via IPC (the loopback interface works well for this purpose). If your program happens to be written in python, as this one is, simply use MSL-Loadlib, a thin wrapper around ctypes (still requires a small amount of wrapper code)