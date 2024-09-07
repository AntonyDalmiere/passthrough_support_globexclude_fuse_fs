import os
import errno

def release_operation(self, path, fh):
    try:
        os.fsync(fh)
        os.close(fh)
    except OSError as e:
        if e.errno != errno.EBADF:
            raise
