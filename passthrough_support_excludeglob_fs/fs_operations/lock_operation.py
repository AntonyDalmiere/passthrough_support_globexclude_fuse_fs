import errno

def lock_operation(self, path, fh, cmd, lock):
    return -errno.ENOTSUP
