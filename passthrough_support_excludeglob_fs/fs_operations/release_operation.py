import os
import errno

def release_operation(self, path, fh):
    if fh in self.file_handles:
        try:
            os.fsync(self.file_handles[fh].real_fh)
            os.close(self.file_handles[fh].real_fh)
        except OSError as e:
            if e.errno != errno.EBADF:
                raise
        del self.file_handles[fh]
    else:
        pass
