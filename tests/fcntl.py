# Mock fcntl module to allow running pytest under Windows
def fcntl(fd, op, arg=0):
    return 0

def ioctl(fd, op, arg=0, mutate_flag=False):
    return 0

def flock(fd, op):
    return 0

def lockf(fd, op, length=0, start=0, whence=0):
    return 0
