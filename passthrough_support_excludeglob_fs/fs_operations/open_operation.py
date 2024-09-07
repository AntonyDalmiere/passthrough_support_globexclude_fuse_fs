import os
import stat
import errno

def open_operation(self, path, flags) -> int:
    if os.name == 'nt':
        flags = os.O_RDWR | os.O_BINARY
    right_path = self.get_right_path(path)
    st_mode = os.lstat(right_path).st_mode
    if stat.S_ISLNK(st_mode):
        return self.open(self.readlink(path), flags)
    if os.path.lexists(right_path):
        fh = os.open(right_path, flags)
    else:
        if flags & os.O_CREAT:
            return self.create(path, 0o777)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    return fh
