import os
import stat
import errno
import shutil
import traceback
from refuse.high import FuseOSError
from .access_operation import _access
from ..main import FileHandle

def rename_operation(self, old, new):
    #Check if the dest file is ignored by rename
    if old in self.renameExcludedSourceFiles:
        #Remove the element from the list
        self.renameExcludedSourceFiles.remove(old)
        self.unlink(new)
        return 0
    #Check if the new filename should be suffixed with .lnk
    if old in self.renameAppendLnkToFilenameFiles:
        #Remove the element from the list
        try:
            self.unlink(new)
        except Exception:
            pass

        self.renameAppendLnkToFilenameFiles.remove(old)
        new = new + '.lnk'

    try:
        if(not _access(self, old, os.R_OK)):
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

        def get_all_file_handles(path) -> list[int]:
            handles = []
            for fh, handle in self.file_handles.items():
                if handle.path.startswith(self.get_right_path(path)):
                    handles.append((fh, handle.path, handle.real_fh))
            return handles

        def close_file_handles(handles):
            for fh, _, _ in handles:
                self.release(None, fh)

        #Reopen previous file handles which where moved to their new paths
        def reopen_file_handles(handles, original_old, original_new):
            for fh, real_old_path, real_fh in handles:
                # Get the new path of the file handle
                # Replace the old path with the new path
                new_path_of_handle = real_old_path.replace(self.get_right_path(original_old), self.get_right_path(original_new))
                
                open_flags = os.O_RDWR
                if os.name == 'nt':
                    open_flags |= os.O_BINARY
                new_real_fh = os.open(new_path_of_handle, open_flags)
                self.file_handles[fh] = FileHandle(new_path_of_handle, new_real_fh)

        # Get and close all open file handles in the hierarchy
        old_handles = get_all_file_handles(old)
        new_handles = get_all_file_handles(new)

        #get for each keys the pos of the seek
        pos_per_fh: dict[int, int] = {}
        for fh, handle in self.file_handles.items():
            pos_per_fh[fh] = os.lseek(handle.real_fh, 0, os.SEEK_CUR)
                

        close_file_handles(old_handles + new_handles)

        opened_file_atime_ctime : dict[str, tuple[float, float]] = {}

        def recursive_copy(old_path, new_path):
            if stat.S_ISDIR(self.getattr(old_path)['st_mode']):  # Directory
                self.mkdir(new_path, self.getattr(old_path)['st_mode'])
                for item in self.readdir(old_path,None):
                    if item not in ['.', '..']:
                        recursive_copy(os.path.join(old_path, item), os.path.join(new_path, item))
            elif stat.S_ISLNK(self.getattr(old_path)['st_mode']):  # Symlink
                source_path = self.get_right_path(old_path)
                destination_path = self.get_right_path(new_path)
                #Delete the target  then create the symlink
                if os.path.lexists(destination_path):
                    os.unlink(destination_path)
                shutil.copy2(source_path, destination_path, follow_symlinks=False)
            else:  # File
                #copy metadata to opened_file_atime_ctime
                opened_file_atime_ctime[new_path] = (self.getattr(old_path)['st_atime'], self.getattr(old_path)['st_ctime'])

                #copy
                dest_fh = self.create(new_path, self.getattr(old_path)['st_mode'])
                #truncate destination file
                self.truncate(new_path, 0, dest_fh)
                source_fh = self.open(old_path, os.O_RDONLY)
                buffer_size = 4096
                offset = 0
                while True:
                    data = self.read(old_path, buffer_size, offset, source_fh)
                    if not data:
                        break
                    offset += self.write(new_path, data, offset, dest_fh)
                self.release(old_path, source_fh)
                self.release(new_path, dest_fh)


        recursive_copy(old, new)

        def recursive_remove(path):
            if self.getattr(path)['st_mode'] & 0o40000:  # Directory
                for item in self.readdir(path,None):
                    if item not in ['.', '..']:
                        recursive_remove(os.path.join(path, item))
                self.rmdir(path)
            else:  # File
                self.unlink(path)

        recursive_remove(old)
        # Reopen file handles
        reopen_file_handles(old_handles, old, new)
        #reset the seek for each file handles
        for fh, pos in pos_per_fh.items():
            try:
                os.lseek(self.file_handles[fh].real_fh, pos, os.SEEK_SET)
            except:
                pass
        #set back the atime and ctime for each file
        for path, (atime, ctime) in opened_file_atime_ctime.items():
            os.utime(self.get_right_path(path), (atime, ctime))

    except Exception:
            traceback.print_exc()
            raise
    return 0
