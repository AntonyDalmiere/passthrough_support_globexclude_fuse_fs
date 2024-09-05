import os
import errno
from refuse.high import FuseOSError

def truncate_operation(self, path, length, fh=None):
    right_path = self.get_right_path(path)
    if os.path.lexists(right_path):
        with open(right_path, "r+") as f:
            f.truncate(length)
    else:
        raise FuseOSError(errno.ENOENT)
