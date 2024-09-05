import os
import psutil
import errno
from refuse.high import FuseOSError

def statfs_operation(self, path):
    right_path = self.get_right_path(path)
    if os.path.lexists(right_path):
        stv = psutil.disk_usage(right_path)
    else:
        raise FuseOSError(errno.ENOENT)
    block_size = 4096  # Set the block size to a fixed value
    return {
        'f_bsize': block_size,  # file system block size
        'f_frsize': block_size,  # fragment size
        'f_blocks': stv.total // block_size,  # size of fs in f_frsize units
        'f_bfree': stv.free // block_size,  # number of free blocks
        'f_bavail': stv.free // block_size,  # number of free blocks for unprivileged users
        'f_files': stv.total // block_size,  # number of inodes
        'f_ffree': stv.total // block_size,  # number of free inodes
        'f_favail': stv.total // block_size,  # number of free inodes for unprivileged users
        'f_flag': 0,  # mount flags
        'f_namemax': 255,  # maximum filename length,
        'f_fsid': 123456789,  # Filesystem ID: Some unique identifier
    }
