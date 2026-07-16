# Mock resource module to allow running pytest under Windows
RLIMIT_NOFILE = 0

def getrlimit(resource):
    return (1024, 1024)

def setrlimit(resource, limits):
    pass
