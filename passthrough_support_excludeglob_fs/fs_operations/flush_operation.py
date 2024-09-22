import os


def flush_operation(self, path, fh):
    os.fsync(fh)
