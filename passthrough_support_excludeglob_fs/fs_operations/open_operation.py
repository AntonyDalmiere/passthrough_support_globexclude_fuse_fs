import os
from typing import Dict
from ..main import FileHandle, FuseOSError

def open_operation(self, path, flags) -> int:
    if os.name == 'nt':
        flags = os.O_RDWR | os.O_BINARY
    right_path = self.get_right_path(path)
    st_mode = os.lstat(right_path).st_mode
    if stat.S_ISLNK(st_mode):
        return self.open(self.readlink(path), flags)
    if os.path.lexists(right_path):
        fh: FileHandle = FileHandle(right_path, os.open(right_path, flags))
    else:
        if flags & os.O_CREAT:
            return self.create(path, 0o777)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    exposed_fh = max(self.file_handles.keys()) + 1 if self.file_handles else 0
    self.file_handles[exposed_fh] = fh
    return exposed_fh
