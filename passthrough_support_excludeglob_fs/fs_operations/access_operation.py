import os
import errno
from refuse.high import FuseOSError

def _access(self, path, mode):
    right_path = self.get_right_path(path)
    if not os.path.lexists(right_path):
        raise FuseOSError(errno.ENOENT)
    if os.name == 'nt':
        return os.access(right_path, mode)
    else:
        return os.access(right_path, mode, follow_symlinks=False)

def access_operation(self, path, amode):
    if _access(self, path, amode):
        return 0
    else:
        raise FuseOSError(errno.EACCES)

__all__ = ['_access', 'access_operation']
