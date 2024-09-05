import os
import errno
from refuse.high import FuseOSError

def utimens_operation(self, path, times=None):
    right_path = self.get_right_path(path)
    if os.path.lexists(right_path):
        return os.utime(right_path, times)
    else:
        raise FuseOSError(errno.ENOENT)
