import os
import errno
from refuse.high import FuseOSError

def chmod_operation(self, path, mode):
    right_path = self.get_right_path(path)
    if os.path.lexists(right_path):
        return os.chmod(right_path, mode)
    else:
        raise FuseOSError(errno.ENOENT)
