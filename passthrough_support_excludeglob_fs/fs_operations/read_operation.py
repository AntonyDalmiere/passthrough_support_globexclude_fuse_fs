import os
import errno
from refuse.high import FuseOSError
from .access_operation import _access

def read_operation(self, path, length, offset, fh):
    if not _access(self, path, os.R_OK):
        raise FuseOSError(errno.EACCES)
    
    right_path = self.get_right_path(path)

    if os.path.lexists(right_path):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)
    else:
        raise FuseOSError(errno.ENOENT)
