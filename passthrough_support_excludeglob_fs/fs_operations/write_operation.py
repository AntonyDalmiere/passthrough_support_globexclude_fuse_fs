import os
from fuse import FuseOSError
import errno

def write_operation(self, path, buf, offset, fh):
    if fh not in self.file_handles:
        raise FuseOSError(errno.EBADF)
    right_path = self.get_right_path(path)

    if not os.path.lexists(right_path):
        raise FuseOSError(errno.ENOENT)

    os.lseek(self.file_handles[fh].real_fh, offset, os.SEEK_SET)
    total_written = os.write(self.file_handles[fh].real_fh, buf)
    os.fsync(self.file_handles[fh].real_fh)  
    return total_written
