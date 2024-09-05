import os
import stat
import errno
from refuse.high import FuseOSError

def rmdir_operation(self, path):
    full_path = self.get_full_path(path)
    cache_path = self.get_cache_path(path)
    try:
        if not os.path.lexists(full_path) and not os.path.lexists(cache_path):
            raise FuseOSError(errno.ENOENT)
        if os.path.lexists(full_path):
            #remove readonly attrib 
            os.chmod(full_path, stat.S_IWRITE)
            os.rmdir(full_path)
        if os.path.lexists(cache_path):
            os.chmod(cache_path, stat.S_IWRITE)
            os.rmdir(cache_path)
    except OSError as e:
        raise FuseOSError(e.errno)
    return 0
