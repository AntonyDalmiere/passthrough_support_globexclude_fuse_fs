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
        
    # Filesystem methods
    def access(self, path, mode):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            if not os.access(full_path, mode):
                raise FuseOSError(errno.EACCES)
        elif os.path.exists(cache_path):
            if not os.access(cache_path, mode):
                raise FuseOSError(errno.EACCES)
        else:
            raise FuseOSError(errno.ENOENT)
        return 0

    def getattr(self, path, fh=None):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            st = os.lstat(full_path)
        elif os.path.exists(cache_path):
            st = os.lstat(cache_path)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        #Edit st to make user RWX perm
        st_dict = dict((key, getattr(st, key)) for key in (
            'st_atime', 'st_ctime', 'st_gid', 'st_mtime',
            'st_nlink', 'st_size', 'st_uid','st_mode'))
        st_dict['st_mode'] = st_dict['st_mode'] | 0o777 # type: ignore
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
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            fh: FileHandle = FileHandle(full_path,os.open(full_path,flags))
        elif os.path.exists(cache_path):
            fh: FileHandle = FileHandle(cache_path,os.open(cache_path,flags))
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        #Append fh to file_handles
        exposed_fh = max(self.file_handles.keys()) + 1 if self.file_handles else 0
        self.file_handles[exposed_fh] = fh
        print({key: str(value) for key, value in self.file_handles.items()}, flush=True)
        return exposed_fh
    
    def read(self, path, length, offset, fh):
        print({key: str(value) for key, value in self.file_handles.items()}, flush=True)

        if(self.access(path, os.R_OK) != 0):
            raise FuseOSError(errno.EACCES)
        
        target_path = self.get_full_path(path) if os.path.exists(self.get_full_path(path)) else self.get_cache_path(path)

        if os.path.exists(target_path):
            with open(target_path, 'rb') as f:  # Use 'with open' for both cases
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
        print(f"Write operation: path={path}, offset={offset}, fh={fh}", flush=True)
        print({key: str(value) for key, value in self.file_handles.items()}, flush=True)

        if fh not in self.file_handles:
            raise KeyError(f"File handle {fh} not found")

        target_path = self.get_full_path(path) if not self.is_excluded(path) else self.get_cache_path(path)

        if not os.path.exists(target_path):
            raise FuseOSError(errno.ENOENT)  # Or raise an appropriate exception

        with open(target_path, 'r+b' if os.path.exists(target_path) else 'wb') as f:
            f.seek(offset)
            total_written = 0
            while total_written < len(buf):
                written = f.write(buf[total_written:])
                if written == 0:  # Write error or end of file reached unexpectedly
                    raise IOError("Failed to write entire buffer") 
                total_written += written

        print(f"Syncing file handle {fh} with real_fh {self.file_handles[fh].real_fh}", flush=True)
        os.fsync(self.file_handles[fh].real_fh)
        return total_written
    
    def chmod(self, path, mode):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            return os.chmod(full_path, mode)
        elif os.path.exists(cache_path):
            return os.chmod(cache_path, mode)
        else:
            raise FuseOSError(errno.ENOENT)

    def chown(self, path, uid, gid):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            return os.chown(full_path, uid, gid)
        elif os.path.exists(cache_path):
            return os.chown(cache_path, uid, gid)
        else:
            raise FuseOSError(errno.ENOENT)

    def readlink(self, path):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            pathname = os.readlink(full_path)
        elif os.path.exists(cache_path):
            pathname = os.readlink(cache_path)
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
            if os.path.exists(full_path):
                #remove readonly attrib 
                os.chmod(full_path, stat.S_IWRITE)
                return os.rmdir(full_path)
            if os.path.exists(cache_path):
                os.chmod(cache_path, stat.S_IWRITE)
                return os.rmdir(cache_path)
        except OSError as e:
            raise FuseOSError(e.errno)
        raise FuseOSError(errno.ENOENT)

    def mkdir(self, path, mode) -> None:
        full_path = self.get_full_path(path)
        if self.is_excluded(path):
            cache_path = self.get_cache_path(path)
            return os.mkdir(cache_path, mode)
        else:
            return os.mkdir(full_path, mode)

    def statfs(self, path):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            stv = psutil.disk_usage(full_path)
        elif os.path.exists(cache_path):
            stv = psutil.disk_usage(cache_path)
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
            'f_namemax': 1024,  # maximum filename length,
            'f_fsid': 123456789,  # Filesystem ID: Some unique identifier
        }

    def unlink(self, path):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        corresponded_file_handles = [fh for fh in self.file_handles if self.file_handles[fh].path == full_path or self.file_handles[fh].path == cache_path]

        for fh in corresponded_file_handles:
            print(f"Unlinking file handle {fh}", flush=True)
            self.release(path, fh)

        if os.path.exists(full_path):
            return os.unlink(full_path)
        if os.path.exists(cache_path):
            return os.unlink(cache_path)
        raise FuseOSError(errno.ENOENT)

    def symlink(self, name, target):
        full_path_name = self.get_full_path(name)
        full_path_target = self.get_full_path(target)
        if self.is_excluded(name):
            cache_path_name = self.get_cache_path(name)
            return os.symlink(full_path_target, cache_path_name)
        else:
            return os.symlink(full_path_target, full_path_name)

    def rename(self, old, new):
        full_path_old = self.get_full_path(old)
        full_path_new = self.get_full_path(new)
        cache_path_old = self.get_cache_path(old)
        cache_path_new = self.get_cache_path(new)

        print(psutil.Process().open_files(), flush=True)

        corresponded_file_handles = [fh for fh in self.file_handles if self.file_handles[fh].path == full_path_old or self.file_handles[fh].path == cache_path_old]

        for fh in corresponded_file_handles:
            print(f"Releasing file handle {fh} before renaming", flush=True)
            self.release(old, fh)
            print(f"Renaming file handle {fh}", flush=True)
            print(psutil.Process().open_files(), flush=True)

        if os.path.exists(full_path_old):
            if self.is_excluded(new):
                shutil.move(full_path_old, cache_path_new)
                for fh in corresponded_file_handles:
                    self.file_handles[fh] = FileHandle(cache_path_new, os.open(cache_path_new, os.O_RDWR))
            else:
                shutil.move(full_path_old, full_path_new)
                for fh in corresponded_file_handles:
                    self.file_handles[fh] = FileHandle(full_path_new, os.open(full_path_new, os.O_RDWR))
        elif os.path.exists(cache_path_old):
            if self.is_excluded(new):
                shutil.move(cache_path_old, cache_path_new)
                for fh in corresponded_file_handles:
                    self.file_handles[fh] = FileHandle(cache_path_new, os.open(cache_path_new, os.O_RDWR))
            else:
                shutil.move(cache_path_old, full_path_new)
                for fh in corresponded_file_handles:
                    self.file_handles[fh] = FileHandle(full_path_new, os.open(full_path_new, os.O_RDWR))
        else:
            raise FuseOSError(errno.ENOENT)
        return 0


    def utimens(self, path, times=None):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            return os.utime(full_path, times)
        elif os.path.exists(cache_path):
            return os.utime(cache_path, times)
        else:
            raise FuseOSError(errno.ENOENT)

    def create(self, path, mode):
        if self.is_excluded(path):
            cache_path = self.get_cache_path(path)
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)     
            fd = os.open(cache_path, os.O_WRONLY | os.O_CREAT, mode)
            new_fd_id = max(self.file_handles.keys()) + 1 if self.file_handles else 0
            self.file_handles[new_fd_id] = FileHandle(cache_path,fd)
        else:
            full_path = self.get_full_path(path)
            fd = os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)
            new_fd_id = max(self.file_handles.keys()) + 1 if self.file_handles else 0
            self.file_handles[new_fd_id] = FileHandle(full_path,fd)
        return new_fd_id
    
    def truncate(self, path, length, fh=None):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        if os.path.exists(full_path):
            with open(full_path, "r+") as f:
                f.truncate(length)
        elif os.path.exists(cache_path):
            with open(cache_path, "r+") as f:
                f.truncate(length)
        else:
            raise FuseOSError(errno.ENOENT)

    def release(self, path, fh):
        if fh in self.file_handles:
            try:
                print(f"Releasing file handle {fh} with path {self.file_handles[fh].path} and real_fh {self.file_handles[fh].real_fh}", flush=True)
                os.close(self.file_handles[fh].real_fh)
            except OSError as e:
                if e.errno != errno.EBADF:
                    raise
            print(f"Deleting file handle {fh} from file_handles", flush=True)
            del self.file_handles[fh]
        else:
            print(f"File handle {fh} not found in file_handles", flush=True)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)

    def flush(self, path, fh):
        # return os.fsync(fh)
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
        print("Check file {} and result is {}".format(path,glob_match(path, self.patterns)))
        return glob_match(path, self.patterns)

    


def start_passthrough_fs(mountpoint, root, patterns=None, cache_dir=None):
    if patterns:
        print("Excluded patterns: ", patterns)
    
    if not cache_dir:
        cache_dir = os.path.join(user_cache_dir("PassthroughFS"), base64.b64encode(root.encode()).decode())
    
    os.makedirs(name=cache_dir, exist_ok=True)
    print("Using cache directory:", cache_dir)
    fuse = FUSE(PassthroughFS(root, patterns, cache_dir), mountpoint, foreground=True, allow_other=True, uid=-1, nothreads=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PassthroughFS")
    parser.add_argument("mountpoint", help="Mount point for the filesystem")
    parser.add_argument("root", help="Root directory for the filesystem")
    parser.add_argument("--patterns", nargs="*", help="Exclude patterns")
    parser.add_argument("--cache-dir", help="Cache directory")
    args = parser.parse_args()
    start_passthrough_fs(args.mountpoint, args.root, args.patterns, args.cache_dir)