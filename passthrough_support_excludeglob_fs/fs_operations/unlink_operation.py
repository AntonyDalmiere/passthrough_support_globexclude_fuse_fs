import os
import errno
from refuse.high import FuseOSError

def unlink_operation(self, path):
    right_path = self.get_right_path(path)
    corresponded_file_handles = [fh for fh in self.file_handles if self.file_handles[fh].path == right_path]

    for fh in corresponded_file_handles:
        self.release(path, fh)

    if os.path.lexists(right_path):
        return os.unlink(right_path)
    raise FuseOSError(errno.ENOENT)
