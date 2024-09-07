import os
import errno
from refuse.high import FuseOSError

def unlink_operation(self, path):
    right_path = self.get_right_path(path)

    if os.path.lexists(right_path):
        if os.name == 'nt':
            #Use native Ctype Win32 API to delete file
            from ctypes import windll
            windll.kernel32.DeleteFileW(right_path)
        else:
            return os.unlink(right_path)
    raise FuseOSError(errno.ENOENT)
