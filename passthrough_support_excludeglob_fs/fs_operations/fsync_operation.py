def fsync_operation(self, path, fdatasync, fh):
    return self.flush(path, fh)
