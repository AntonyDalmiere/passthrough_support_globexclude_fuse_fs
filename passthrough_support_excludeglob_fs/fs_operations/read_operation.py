import os
import errno
from refuse import FuseOSError

def read_operation(self, path, length, offset, fh):
    if not self._access(path, os.R_OK):
        raise FuseOSError(errno.EACCES)
    
    right_path = self.get_right_path(path)

    if os.path.lexists(right_path):
        os.lseek(self.file_handles[fh].real_fh, offset, os.SEEK_SET)
        return os.read(self.file_handles[fh].real_fh, length)
    else:
        raise FuseOSError(errno.ENOENT)
