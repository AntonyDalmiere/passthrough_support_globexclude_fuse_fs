import os
import stat
import errno
import shutil
import traceback
from refuse.high import FuseOSError
from .access_operation import _access
from .mkdir_operation import makedirs

def rename_operation(self, old, new):
    if old in self.renameExcludedSourceFiles:
        self.renameExcludedSourceFiles.remove(old)
        self.unlink(new)
        return 0

    if old in self.renameAppendLnkToFilenameFiles:
        try:
            self.unlink(new)
        except Exception:
            pass
        self.renameAppendLnkToFilenameFiles.remove(old)
        new = new + '.lnk'

    try:
        if not _access(self, old, os.R_OK):
            raise FuseOSError(errno.ENOENT)

        try:
            if _access(self, new, os.R_OK):
                if not self.overwrite_rename_dest and 'fuse_hidden' not in old:
                    raise FuseOSError(errno.EEXIST)
        except FuseOSError as e:
            if e.errno == errno.EEXIST:
                raise
            else:
                pass

        def recursive_copy(old_path, new_path):
            print(f'Moving {old_path} to {new_path}')
            right_old_path = self.get_right_path(old_path)
            right_new_path = self.get_right_path(new_path)
            if stat.S_ISDIR(self.getattr(old_path)['st_mode']):  # Directory
                self.mkdir(new_path, self.getattr(old_path)['st_mode'])
                for item in self.readdir(old_path, None):
                    if item not in ['.', '..']:
                        recursive_copy(os.path.join(old_path, item), os.path.join(new_path, item))
                self.rmdir(old_path)
            elif stat.S_ISLNK(self.getattr(old_path)['st_mode']):  # Symlink
                source_path = self.get_right_path(old_path)
                destination_path = self.get_right_path(new_path)
                if os.path.lexists(destination_path):
                    os.unlink(destination_path)
                shutil.copy2(source_path, destination_path, follow_symlinks=False)
            else:  # File
                #Call makedirs to create the parent directory if it doesn't exist (when parent is excluded but child is not or vice versa)
                makedirs(self,os.path.dirname(right_new_path), exist_ok=True)
                if os.name == 'nt':
                    #Use native Ctype Win32 API to rename file
                    from ctypes import windll
                    windll.kernel32.MoveFileExW(right_old_path, right_new_path, 0)
                else:
                    os.rename(right_old_path, right_new_path)

        recursive_copy(old, new)

    except Exception:
        traceback.print_exc()
        raise
    return 0
