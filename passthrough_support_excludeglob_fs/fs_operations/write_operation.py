import os
from refuse.high import FuseOSError
import errno

def write_operation(self, path, buf, offset, fh):
    if not os.path.lexists(self.get_right_path(path)):
        raise FuseOSError(errno.ENOENT)

    os.lseek(fh, offset, os.SEEK_SET)
    total_written = os.write(fh, buf)
    os.fsync(fh)  
    return total_written
