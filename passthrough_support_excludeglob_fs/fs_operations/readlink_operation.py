import os
import errno
from refuse.high import FuseOSError
import pylnk3

def readlink_operation(self, path):
    if path == '/':
        return errno.ENOSYS
    #Support symlink backed by lnk file
    if self.symlink_creation_windows == 'create_lnkfile' and os.name == 'nt':
        stored_path: str = pylnk3.parse(self.get_right_path(path + '.lnk')).path
        #On FS sored_path look like : Q:\symlink_test.txt
        #However , supported on FS path should be : /symlink_test.txt
        #If sorted_path don't start with current mountpoint, the symlink point to external FS
        if not stored_path.startswith(self.mountpoint):
            return stored_path
        else:
            #Remove the mountpoint from the path
            stored_path = stored_path.replace(self.mountpoint + "\\", "/")
            return stored_path
    right_path = self.get_right_path(path)
    if os.path.lexists(right_path):
        pathname = os.readlink(right_path)
    else:
        raise FuseOSError(errno.ENOENT)
    return pathname
