import os
import errno
from refuse.high import FuseOSError

def chown_operation(self, path, uid, gid):
    if os.name == 'nt':
        raise FuseOSError(errno.ENOTSUP)
    right_path = self.get_right_path(path)
    if os.path.lexists(right_path):
        return os.chown(right_path, uid, gid)
    else:
        raise FuseOSError(errno.ENOENT)
