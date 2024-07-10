import os
import stat
import sys
from typing import Dict
from refuse import _refactor
_refactor.sys = sys # type: ignore
from refuse.high import FUSE, FuseOSError, Operations,LoggingMixIn

import errno
from globmatch import glob_match
import argparse
from appdirs import user_cache_dir
import base64
import psutil
import logging
from pathlib import Path
import shutil
import traceback

class FileHandle:
    def __init__(self, path, real_fh):
        self.path = path
        self.real_fh = real_fh
    def __str__(self):
        return f"FileHandle(path={self.path}, real_fh={self.real_fh})"

class PassthroughFS(LoggingMixIn,Operations):
    def __init__(self, root, patterns, cache_dir):
        self.root = root
        self.patterns = patterns
        self.cache_dir = cache_dir
        self.file_handles: Dict[int, FileHandle] = {} 

    def get_right_path(self, path):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        is_excluded = self.is_excluded(path)

        full_exists = os.path.exists(full_path)
        cache_exists = os.path.exists(cache_path)

        if full_exists and cache_exists:
            # Both exist, return the most recent one
            full_mtime = os.path.getmtime(full_path)
            cache_mtime = os.path.getmtime(cache_path)
            return cache_path if cache_mtime > full_mtime else full_path
        elif full_exists:
            if is_excluded:
                # Move to cache if it should be excluded
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                shutil.move(full_path, cache_path)
                return cache_path
            else:
                return full_path
        elif cache_exists:
            if not is_excluded:
                # Move to full if it should not be excluded
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                shutil.move(cache_path, full_path)
                return full_path
            else:
                return cache_path
        else:
            # Neither exists, return the appropriate path based on exclusion
            return cache_path if is_excluded else full_path
        
    # Filesystem methods
    def access(self, path, mode):
        right_path = self.get_right_path(path)
        if not os.path.exists(right_path):
            raise FuseOSError(errno.ENOENT)
        if not os.access(right_path, mode):
            raise FuseOSError(errno.EACCES)
        return 0

    def getattr(self, path, fh=None):
        right_path = self.get_right_path(path)
        if not os.path.exists(right_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        st = os.lstat(right_path)
       
        #Edit st to make user RWX perm
        st_dict = dict((key, getattr(st, key,0)) for key in (
            'st_atime', 'st_ctime', 'st_gid', 'st_mtime',
            'st_nlink', 'st_size', 'st_uid','st_mode','st_birthtime'))
        #add st_birthtime to st_dict
        if os.name == 'nt':
            st_dict['st_mode'] = st_dict['st_mode'] | 0o777
        return st_dict

    def readdir(self, path, fh):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        dirents = [".", ".."]
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        if os.path.isdir(cache_path):
            dirents.extend(os.listdir(cache_path))
        return set(dirents)

    def open(self, path, flags):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
            fh: FileHandle = FileHandle(right_path, os.open(right_path, flags))
        else:
            if flags & os.O_CREAT:
                return self.create(path, 0o777)
            else:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        #Append fh to file_handles
        exposed_fh = max(self.file_handles.keys()) + 1 if self.file_handles else 0
        self.file_handles[exposed_fh] = fh
        print(f"Opened file handle for {right_path} with fd {exposed_fh}")

        return exposed_fh
    
    def read(self, path, length, offset, fh):
        if(self.access(path, os.R_OK) != 0):
            raise FuseOSError(errno.EACCES)
        
        right_path = self.get_right_path(path)

        if os.path.exists(right_path):
            with open(right_path, 'rb') as f:
                f.seek(offset)
                data = b""
                while len(data) < length:
                    chunk = f.read(length - len(data))
                    if not chunk:
                        break
                    data += chunk
                return data
        else:
            raise FuseOSError(errno.ENOENT)

    def write(self, path, buf, offset, fh):
        if fh not in self.file_handles:
            raise KeyError(f"File handle {fh} not found")

        right_path = self.get_right_path(path)

        if not os.path.exists(right_path):
            raise FuseOSError(errno.ENOENT)

        with open(right_path, 'r+b' if os.path.exists(right_path) else 'wb') as f:
            f.seek(offset)
            total_written = 0
            while total_written < len(buf):
                written = f.write(buf[total_written:])
                if written == 0:
                    raise IOError("Failed to write entire buffer") 
                total_written += written

        os.fsync(self.file_handles[fh].real_fh)
        return total_written
    
    def chmod(self, path, mode):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
            os.chmod(right_path, mode)
        else:
            raise FuseOSError(errno.ENOENT)

    def chown(self, path, uid, gid):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
            return os.chown(right_path, uid, gid)
        else:
            raise FuseOSError(errno.ENOENT)

    def readlink(self, path):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
            pathname = os.readlink(right_path)
        else:
            raise FuseOSError(errno.ENOENT)
        if pathname.startswith("/"):
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def rmdir(self, path):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        try:
            if not os.path.exists(full_path) and not os.path.exists(cache_path):
                raise FuseOSError(errno.ENOENT)
            if os.path.exists(full_path):
                #remove readonly attrib 
                os.chmod(full_path, stat.S_IWRITE)
                os.rmdir(full_path)
            if os.path.exists(cache_path):
                os.chmod(cache_path, stat.S_IWRITE)
                os.rmdir(cache_path)
        except OSError as e:
            raise FuseOSError(e.errno)
        return 0

    def mkdir(self, path, mode) -> None:
        right_path = self.get_right_path(path)
        return os.mkdir(right_path, mode)

    def statfs(self, path):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
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

    def unlink(self, path):
        right_path = self.get_right_path(path)
        corresponded_file_handles = [fh for fh in self.file_handles if self.file_handles[fh].path == right_path]

        for fh in corresponded_file_handles:
            self.release(path, fh)

        if os.path.exists(right_path):
            return os.unlink(right_path)
        raise FuseOSError(errno.ENOENT)

    def symlink(self, name, target):
        if os.name == 'nt':
            raise FuseOSError(errno.ENOTSUP)
        target_path = self.get_right_path(target)
        name_path = self.get_right_path(name)
        os.symlink(target_path, name_path)

    def rename(self, old, new):
        try:
            if(self.access(old, os.R_OK) != 0):
                raise FuseOSError(errno.ENOENT)

            try:
                if self.access(new, os.R_OK) == 0:
                    raise FuseOSError(errno.EEXIST)
            except FuseOSError:
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


            def reopen_file_handles(handles, old_path, new_path):
                for fh, old_path, real_fh in handles:
                    relative_path = os.path.relpath(old_path, self.get_right_path(old_path))
                    new_file_path = os.path.join(new_path, relative_path)
                    new_right_path = self.get_right_path(new_file_path)
                    new_real_fh = os.open(new_right_path, os.O_RDWR)
                    self.file_handles[fh] = FileHandle(new_right_path, new_real_fh)

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
                print(f"Copying {old_path} to {new_path}")
                if stat.S_ISDIR(self.getattr(old_path)['st_mode']):  # Directory
                    self.mkdir(new_path, self.getattr(old_path)['st_mode'])
                    for item in self.readdir(old_path,None):
                        if item not in ['.', '..']:
                            recursive_copy(os.path.join(old_path, item), os.path.join(new_path, item))
                elif stat.S_ISLNK(self.getattr(old_path)['st_mode']):  # Symlink
                    source_path = self.get_right_path(old_path)
                    destination_path = self.get_right_path(new_path)
                    os.rename(source_path, destination_path)
                else:  # File
                    #copy metadata to opened_file_atime_ctime
                    opened_file_atime_ctime[new_path] = (self.getattr(old_path)['st_atime'], self.getattr(old_path)['st_ctime'])

                    #copy
                    new_fh = self.create(new_path, self.getattr(old_path)['st_mode'])
                    old_fh = self.open(old_path, os.O_RDONLY)
                    buffer_size = 4096
                    offset = 0
                    while True:
                        data = self.read(old_path, buffer_size, offset, old_fh)
                        if not data:
                            break
                        self.write(new_path, data, offset, new_fh)
                        offset += len(data)
                    self.release(old_path, old_fh)
                    self.release(new_path, new_fh)
                    

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
                os.lseek(self.file_handles[fh].real_fh, pos, os.SEEK_SET)

            #set back the atime and ctime for each file
            for path, (atime, ctime) in opened_file_atime_ctime.items():
                os.utime(self.get_right_path(path), (atime, ctime))

        except Exception:
            traceback.print_exc()
            raise
        return 0

    def utimens(self, path, times=None):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
            return os.utime(right_path, times)
        else:
            raise FuseOSError(errno.ENOENT)

    def create(self, path, mode):
        right_path = self.get_right_path(path)
        os.makedirs(os.path.dirname(right_path), exist_ok=True)
        fd = os.open(right_path, os.O_RDWR | os.O_CREAT, mode)
        new_fd_id = max(self.file_handles.keys()) + 1 if self.file_handles else 0
        self.file_handles[new_fd_id] = FileHandle(right_path, fd)
        return new_fd_id
    
    def truncate(self, path, length, fh=None):
        right_path = self.get_right_path(path)
        if os.path.exists(right_path):
            with open(right_path, "r+") as f:
                f.truncate(length)
        else:
            raise FuseOSError(errno.ENOENT)

    def release(self, path, fh):
        if fh in self.file_handles:
            try:
                os.close(self.file_handles[fh].real_fh)
            except OSError as e:
                if e.errno != errno.EBADF:
                    raise
            del self.file_handles[fh]
        else:
            pass

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)

    def flush(self, path, fh):
        pass

    def get_full_path(self, path):
        p = Path(self.root) / Path(path.lstrip("/"))
        return str(p)

    def get_cache_path(self, path):
        p = Path(self.cache_dir) / Path(path.lstrip("/"))
        return str(p)

    def is_excluded(self, path):
        if not self.patterns:
            return False
        return glob_match(path, self.patterns)

def start_passthrough_fs(mountpoint, root, patterns=None, cache_dir=None):
    if patterns:
        print("Excluded patterns: ", patterns)
    
    if not cache_dir:
        cache_dir = os.path.join(user_cache_dir("PassthroughFS"), base64.b64encode(root.encode()).decode())
    
    os.makedirs(name=cache_dir, exist_ok=True)
    print("Using cache directory:", cache_dir)
    fuse = FUSE(PassthroughFS(root, patterns, cache_dir), mountpoint, foreground=True, allow_other=True, uid=-1,ouid=-1, umask=000,nothreads=True,debug=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PassthroughFS")
    parser.add_argument("mountpoint", help="Mount point for the filesystem")
    parser.add_argument("root", help="Root directory for the filesystem")
    parser.add_argument("--patterns", nargs="*", help="Exclude patterns")
    parser.add_argument("--cache-dir", help="Cache directory")
    args = parser.parse_args()
    start_passthrough_fs(args.mountpoint, args.root, args.patterns, args.cache_dir)