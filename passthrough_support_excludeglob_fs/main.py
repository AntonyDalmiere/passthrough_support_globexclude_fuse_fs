#!/usr/bin/env python3

import os
import re
import stat
import sys
from typing import Any, Dict, List, Literal
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
import warnings
with warnings.catch_warnings(action="ignore"):
    from str2type import str2type

class FileHandle:
    def __init__(self, path, real_fh):
        self.path = path
        self.real_fh = real_fh
    def __str__(self):
        return f"FileHandle(path={self.path}, real_fh={self.real_fh})"

class PassthroughFS(LoggingMixIn,Operations):
    def __init__(self, root, patterns, cache_dir,overwrite_rename_dest):
        self.root:str = root
        self.patterns: list[str] = patterns
        self.cache_dir:str = cache_dir
        self.file_handles: Dict[int, FileHandle] = {} 
        self.overwrite_rename_dest:bool = overwrite_rename_dest
        # self.use_ns = True

    def get_right_path(self, path) -> str:
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        is_excluded = self.is_excluded(path)

        full_exists = os.path.lexists(full_path)
        cache_exists = os.path.lexists(cache_path)

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
    def _access(self, path, mode):
        right_path = self.get_right_path(path)
        if not os.path.lexists(right_path):
            raise FuseOSError(errno.ENOENT)
        if os.name == 'nt':
            return os.access(right_path, mode)
        else:
            return os.access(right_path, mode,follow_symlinks=False)
        return result

    def access(self, path, amode):
        if self._access(path, amode):
            return 0
        else:
            raise FuseOSError(errno.EACCES)
    def getattr(self, path, fh=None):
        right_path = self.get_right_path(path)
        if not os.path.lexists(right_path):
            raise FuseOSError(errno.ENOENT)
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

    def open(self, path, flags) -> int:
        if os.name == 'nt':
            flags = os.O_RDWR | os.O_BINARY
        right_path = self.get_right_path(path)
        if os.path.lexists(right_path):
            fh: FileHandle = FileHandle(right_path, os.open(right_path, flags))
        else:
            if flags & os.O_CREAT:
                return self.create(path, 0o777)
            else:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        #Append fh to file_handles
        exposed_fh = max(self.file_handles.keys()) + 1 if self.file_handles else 0
        self.file_handles[exposed_fh] = fh
        return exposed_fh
    
    def read(self, path, length, offset, fh):
        if(not self._access(path, os.R_OK)):
            raise FuseOSError(errno.EACCES)
        
        right_path = self.get_right_path(path)

        if os.path.lexists(right_path):
            os.lseek(self.file_handles[fh].real_fh, offset, os.SEEK_SET)
            return os.read(self.file_handles[fh].real_fh, length)
        else:
            raise FuseOSError(errno.ENOENT)

    def write(self, path, buf, offset, fh):
        if fh not in self.file_handles:
            raise FuseOSError(errno.EBADF)
        right_path = self.get_right_path(path)

        if not os.path.lexists(right_path):
            raise FuseOSError(errno.ENOENT)

        os.lseek(self.file_handles[fh].real_fh, offset, os.SEEK_SET)
        total_written = os.write(self.file_handles[fh].real_fh, buf)
        os.fsync(self.file_handles[fh].real_fh)  
        return total_written
    
    def chmod(self, path, mode):
        right_path = self.get_right_path(path)
        if os.path.lexists(right_path):
            return os.chmod(right_path, mode)
        else:
            raise FuseOSError(errno.ENOENT)

    def chown(self, path, uid, gid):
        if os.name == 'nt':
            raise FuseOSError(errno.ENOTSUP)
        right_path = self.get_right_path(path)
        if os.path.lexists(right_path):
            return os.chown(right_path, uid, gid)
        else:
            raise FuseOSError(errno.ENOENT)

    def readlink(self, path):
        right_path = self.get_right_path(path)
        if os.path.lexists(right_path):
            pathname = os.readlink(right_path)
        else:
            raise FuseOSError(errno.ENOENT)
        return pathname

    def rmdir(self, path):
        full_path = self.get_full_path(path)
        cache_path = self.get_cache_path(path)
        try:
            if not os.path.lexists(full_path) and not os.path.lexists(cache_path):
                raise FuseOSError(errno.ENOENT)
            if os.path.lexists(full_path):
                #remove readonly attrib 
                os.chmod(full_path, stat.S_IWRITE)
                os.rmdir(full_path)
            if os.path.lexists(cache_path):
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

    def unlink(self, path):
        right_path = self.get_right_path(path)
        corresponded_file_handles = [fh for fh in self.file_handles if self.file_handles[fh].path == right_path]

        for fh in corresponded_file_handles:
            self.release(path, fh)

        if os.path.lexists(right_path):
            return os.unlink(right_path)
        raise FuseOSError(errno.ENOENT)

    def symlink(self, link_location, name):
        if os.name == 'nt':
            raise FuseOSError(errno.ENOTSUP)
        link_location_path = self.get_right_path(link_location)
        #write a file named a.txt in fulldir
        with open(self.get_right_path("dfsdfs"), 'w') as f:
            f.write('This is a test file')
        #CHeck if link_location is either an absolute path relative to the mountpoint or a true absolute path


        os.symlink(name, link_location_path)

    def rename(self, old, new):
        try:
            if(not self._access(old, os.R_OK)):
                raise FuseOSError(errno.ENOENT)

            try:
                if self._access(new, os.R_OK):
                    if not self.overwrite_rename_dest:
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
                    
                    new_real_fh = os.open(new_path_of_handle, os.O_RDWR)
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
                    os.rename(source_path, destination_path)
                else:  # File
                    #copy metadata to opened_file_atime_ctime
                    opened_file_atime_ctime[new_path] = (self.getattr(old_path)['st_atime'], self.getattr(old_path)['st_ctime'])

                    #copy
                    dest_fh = self.create(new_path, self.getattr(old_path)['st_mode'])
                    source_fh = self.open(old_path, os.O_RDONLY)
                    buffer_size = 4096
                    offset = 0
                    while True:
                        data = self.read(old_path, buffer_size, offset, source_fh)
                        if not data:
                            break
                        self.write(new_path, data, offset, dest_fh)
                        offset += len(data)
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
        if os.path.lexists(right_path):
            return os.utime(right_path, times)
        else:
            raise FuseOSError(errno.ENOENT)

    #path is already passed trhough get_right_path
    def makedirs(self, path:str, exist_ok=False):
        """
        Recursively create directories at the specified path.

        Args:
            path (str): The path of the directory to be created.
            exist_ok (bool, optional): If True, no exception will be raised if the directory already exists. Defaults to False.
        """
        # Check if path is cache or full
        current_location: Literal['cache', 'full'] = 'cache' if path.startswith(self.cache_dir) else 'full'
        
        # Get the path at the same level in the other location
        relative_path = path.replace(self.cache_dir, "") if current_location == 'cache' else path.replace(self.root, "")
        
        # Split the path into its components
        parts = relative_path.split(sep=os.sep)
        current_path = ""
        
        for part in parts:
            if part:  # Skip empty parts
                # Append part to the current path
                current_path = os.path.join(current_path, part)
                
                # Get the full path if we are in the cache location and vice versa
                if current_location == 'cache':
                    os.makedirs(os.path.join(self.cache_dir, current_path), exist_ok=exist_ok)
                    
                    # If directory also exists in the full path, copy metadata (chmod and owner)
                    full_path = os.path.join(self.root, current_path)
                    if os.path.lexists(full_path):
                        os.chmod(os.path.join(self.cache_dir, current_path), os.stat(full_path).st_mode)
                        if hasattr(os, 'chown'):
                            os.chown(os.path.join(self.cache_dir, current_path), os.stat(full_path).st_uid, os.stat(full_path).st_gid)
                        # Also copy atime and ctime
                        os.utime(os.path.join(self.cache_dir, current_path), (os.stat(full_path).st_atime, os.stat(full_path).st_ctime)) 
                else:  # current_location == 'full'
                    os.makedirs(os.path.join(self.root, current_path), exist_ok=exist_ok)
                    
                    # If directory also exists in the cache path, copy metadata (chmod and owner)
                    cache_path = os.path.join(self.cache_dir, current_path)
                    if os.path.lexists(cache_path):
                        os.chmod(os.path.join(self.root, current_path), os.stat(cache_path).st_mode)
                        if hasattr(os, 'chown'):
                            os.chown(os.path.join(self.root, current_path), os.stat(cache_path).st_uid, os.stat(cache_path).st_gid)
                        # Also copy atime and ctime
                        os.utime(os.path.join(self.root, current_path), (os.stat(cache_path).st_atime, os.stat(cache_path).st_ctime))


    def create(self, path, mode):
        right_path = self.get_right_path(path)
        self.makedirs(os.path.dirname(right_path), exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if os.name == 'nt':
            flags |= os.O_BINARY
        fd = os.open(right_path, flags, mode)
        new_fd_id = max(self.file_handles.keys()) + 1 if self.file_handles else 0
        self.file_handles[new_fd_id] = FileHandle(right_path, fd)
        return new_fd_id
    
    def truncate(self, path, length, fh=None):
        right_path = self.get_right_path(path)
        if os.path.lexists(right_path):
            with open(right_path, "r+") as f:
                f.truncate(length)
        else:
            raise FuseOSError(errno.ENOENT)

    def release(self, path, fh):
        if fh in self.file_handles:
            try:
                os.fsync(self.file_handles[fh].real_fh)
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

    def lock(self, path, fh, cmd, lock):
        return -errno.ENOTSUP


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


def default_uid_and_gid():
    """
    Returns the default UID and GID based on the operating system.

    On Windows, it returns -1 for both UID and GID.
    On Unix-like systems, it returns the current UID and GID.

    Returns:
        tuple: A tuple containing the default UID and GID.
    """
    if os.name == 'nt':
        return -1, -1
    return os.getuid(), os.getgid()

def default_overwrite_rename_dest() -> bool:
    """
    Returns the default value for the `overwrite_rename_dest` parameter.

    This function checks the operating system and returns `False` if it is Windows,
    and `True` otherwise. The purpose of this function is to provide a default value
    for the `overwrite_rename_dest` parameter in the `start_passthrough_fs` function.

    Returns:
        bool: The default value for `overwrite_rename_dest`.
    """
    if os.name == 'nt':
        return False
    else:
        return True
    
def start_passthrough_fs(mountpoint:str, root:str, patterns:None|list[str]=None, cache_dir:str|None=None,uid:int=default_uid_and_gid()[0],gid:int=default_uid_and_gid()[1],foreground:bool=True,nothreads:bool=True,debug:bool=False, overwrite_rename_dest:bool=default_overwrite_rename_dest()):
    if not root:
        raise ValueError("Root directory must be specified")
    if patterns:
        print("Excluded patterns: ", patterns)
    
    if debug:
        print("Verbose mode enabled")
        
    if not cache_dir:
        cache_dir = os.path.join(user_cache_dir("PassthroughFS"), base64.b64encode(root.encode()).decode())
        print("Using default cache directory:", cache_dir)
    os.makedirs(name=cache_dir, exist_ok=True)

    fuse = FUSE(PassthroughFS(root, patterns, cache_dir,overwrite_rename_dest=overwrite_rename_dest), mountpoint,foreground=foreground,nothreads=nothreads,debug=debug,uid=uid,gid=gid)

def parse_options(options: str) -> Dict[str, str]:
    """Parse options string with escaping"""
    options_dict: Dict[str, str] = {}
    for opt in re.split(r'(?<!\\),', options):
        key, value = re.split(r'(?<!\\)=', opt, maxsplit=1)
        options_dict[key] = value.replace('\\,', ',').replace('\\=', '=').replace('\\ ', ' ')
    return options_dict

def split_escaped(separator: str, value: str) -> List[str]:
    """Split a string on a separator, handling escaping"""
    return re.split(rf'(?<!\\){separator}', value)

def cli() -> None:
    parser = argparse.ArgumentParser(description="PassthroughFS")
    parser.add_argument("mountpoint", help="Mount point for the filesystem")
    parser.add_argument("-o", "--options", help="Mount options")
    args = parser.parse_args()

    if args.options is None:
        raise ValueError("At least -o root must be specified.")
    
    options: Dict[str, Any] = parse_options(args.options)
    # Pass each options value to the right type using str2type () except for patterns
    for key in options:
        if key != 'patterns':
            options[key] = str2type(options[key].replace('\\:', ':').replace('\\,', ',').replace('\\=', '=').replace('\\ ', ' '), decode_escape=False)

    if 'patterns' in options:
        # Split patterns to list[str] based on the separator ':' but support escaping the separator
        options['patterns'] = split_escaped(':', options['patterns'].replace('\\ ', ' '))

    try:
        start_passthrough_fs(args.mountpoint, **options)
    except (TypeError, ValueError) as e:
        parser.error(str(e))

if __name__ == "__main__":
    cli()
