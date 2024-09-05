import os

def readdir_operation(self, path, fh):
    full_path = self.get_full_path(path)
    cache_path = self.get_cache_path(path)
    dirents = [".", ".."]
    if os.path.isdir(full_path):
        dirents.extend(os.listdir(full_path))
    if os.path.isdir(cache_path):
        dirents.extend(os.listdir(cache_path))
    #Support symlink backed by lnk file
    if self.symlink_creation_windows == 'create_lnkfile' and os.name == 'nt':
        dirents = [entry[:-4] if entry.endswith('.lnk') else entry for entry in dirents]
    return set(dirents)
