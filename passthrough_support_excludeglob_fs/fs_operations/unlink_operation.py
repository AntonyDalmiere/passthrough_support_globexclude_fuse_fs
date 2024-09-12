import os
import errno
from refuse.high import FuseOSError
if os.name == 'nt':
    from ctypes import windll
def unlink_operation(self, path):
    right_path = self.get_right_path(path)

    if os.path.lexists(right_path):
        if os.name == 'nt':
            return windll.kernel32.DeleteFileW(right_path)
        else:
            return os.unlink(right_path)
    raise FuseOSError(errno.ENOENT)
