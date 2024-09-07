import os
from .mkdir_operation import makedirs

def create_operation(self, path, mode):
    right_path = self.get_right_path(path)
    makedirs(self, os.path.dirname(right_path), exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT
    if os.name == 'nt':
        flags |= os.O_BINARY
    fd = os.open(right_path, flags, mode)
    return fd
