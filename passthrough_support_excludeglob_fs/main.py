#!/usr/bin/env python3

import os
import re
import stat
import sys
from typing import Any, Callable, Dict, List, Literal, get_args
from refuse import _refactor
_refactor.sys = sys # type: ignore
from refuse.high import FUSE, FuseOSError, Operations
from .logginng_mixin import LoggingMixIn
import errno
from globmatch import glob_match
import argparse
from appdirs import user_cache_dir
import base64
import psutil
from pathlib import Path
import shutil
import traceback
import warnings
with warnings.catch_warnings(action="ignore"):
    from str2type import str2type
import subprocess
import pylnk3
import tempfile
class FileHandle:
    def __init__(self, path, real_fh):
        self.path = path
        self.real_fh = real_fh
    def __str__(self):
        return f"FileHandle(path={self.path}, real_fh={self.real_fh})"

from .fs_operations import (
    open_operation,
    read_operation,
    write_operation,
    release_operation,
    access_operation,
    fsync_operation,
    flush_operation,
    lock_operation,
    truncate_operation,
    create_operation,
    utimens_operation,
    unlink_operation,
    statfs_operation,
    rmdir_operation,
    chown_operation,
    chmod_operation,
    getattr_operation,
    readdir_operation,
    readlink_operation,
    mkdir_operation,
    symlink_operation,
    rename_operation
)


def create_for_path_generator( size: int, st_mode: int
) -> Callable[[str], pylnk3.PathSegmentEntry]:
    """
    Generate a function that creates a PathSegmentEntry for a given path.

    Args:
        path (str): The path for which to create the entry.
        size (int): The size of the entry.
        st_mode (int): The mode of the entry.

    Returns:
        Callable[[str], pylnk3.PathSegmentEntry]: A function that creates a
        PathSegmentEntry for a given path.
    """
    def create_for_path(path: str) -> pylnk3.PathSegmentEntry:
        """
        Create a PathSegmentEntry for a given path.

        Args:
            path (str): The path for which to create the entry.

        Returns:
            pylnk3.PathSegmentEntry: The created PathSegmentEntry.
        """
        entry = pylnk3.PathSegmentEntry()
        entry.type = (
            pylnk3.TYPE_FOLDER if st_mode & 0o40000 else pylnk3.TYPE_FILE
        )
        entry.file_size = size
        entry.full_name = os.path.split(path)[1]
        entry.short_name = entry.full_name
        return entry
    return create_for_path

symlink_creation_windows_type = Literal['skip', 'error', 'copy', 'create_lnkfile', 'real_symlink']
class PassthroughFS(LoggingMixIn,Operations):
    def __init__(self, root, patterns, cache_dir,overwrite_rename_dest,debug,log_in_file,log_in_console,log_in_syslog,symlink_creation_windows:symlink_creation_windows_type,mountpoint):

        LoggingMixIn.__init__(self, enable=debug,log_in_file=log_in_file,log_in_console=log_in_console,log_in_syslog=log_in_syslog)
        self.root:str = root
        self.patterns: list[str] = patterns
        self.cache_dir:str = cache_dir
        self.file_handles: Dict[int, FileHandle] = {} 
        self.overwrite_rename_dest:bool = overwrite_rename_dest
        self.symlink_creation_windows:symlink_creation_windows_type = symlink_creation_windows
        # self.use_ns = True
        self.mountpoint:str = mountpoint

        #create a property to store list of dest file that must be ignored when they are the source of a rename
        self.renameExcludedSourceFiles: list[str] = []
        self.renameAppendLnkToFilenameFiles: list[str] = []

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
    def getattr(self, path, fh=None):
        return getattr_operation(self, path, fh)

    def readdir(self, path, fh):
        return readdir_operation(self, path, fh)

    def open(self, path, flags) -> int:
        return open_operation(self, path, flags)
    
    def read(self, path, length, offset, fh):
        return read_operation(self, path, length, offset, fh)

    def write(self, path, buf, offset, fh):
        return write_operation(self, path, buf, offset, fh)
    
    def chmod(self, path, mode):
        return chmod_operation(self, path, mode)

    def chown(self, path, uid, gid):
        return chown_operation(self, path, uid, gid)

    def release(self, path, fh):
        return release_operation(self, path, fh)
    def access(self, path, amode):
        return access_operation(self, path, amode)
    def fsync(self, path, fdatasync, fh):
        return fsync_operation(self, path, fdatasync, fh)
    def flush(self, path, fh):
        return flush_operation(self, path, fh)
    def lock(self, path, fh, cmd, lock):
        return lock_operation(self, path, fh, cmd, lock)
    def truncate(self, path, length, fh=None):
        return truncate_operation(self, path, length, fh)
    def utimens(self, path, times=None):
        return utimens_operation(self, path, times)
    def unlink(self, path):
        return unlink_operation(self, path)
    def statfs(self, path):
        return statfs_operation(self, path)
    
    def readlink(self, path):
        return readlink_operation(self, path)

    def rmdir(self, path):
        return rmdir_operation(self, path)

    def mkdir(self, path, mode) -> None:
        return mkdir_operation(self, path, mode)

    def symlink(self, link_location: str, name: str) -> None:
        return symlink_operation(self, link_location, name)

    def rename(self, old, new):
        return rename_operation(self, old, new)

    def create(self, path, mode):
        return create_operation(self, path, mode)
    



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
def default_symlink_creation_windows() -> symlink_creation_windows_type:
    if os.name != 'nt':
        return 'error'
    #Detect if symlink creation is allowed
    #Create a symlink to a file in temp dir
    temp_dest_path = os.path.join(tempfile.gettempdir(), 'test_symlink_creation_windows')
    #create destination file
    with open(temp_dest_path, 'w') as f:
        f.write('test')
    temp_source_path = os.path.join(tempfile.gettempdir(), 'test_symlink_creation_windows_source')
    #if symlink sucees set symlink_creation_windows to real_symlink else set it to error
    try:
        os.symlink(temp_dest_path, temp_source_path)
        return 'real_symlink'
    except OSError:
        return 'error'
    finally:
        os.remove(temp_dest_path)
        os.remove(temp_source_path)
     
def default_rellinks() -> bool:
    if os.name == 'nt':
        return True
    else:
        return False
    
def start_passthrough_fs(mountpoint:str, root:str, patterns:None|list[str]=None, cache_dir:str|None=None,uid:int=default_uid_and_gid()[0],gid:int=default_uid_and_gid()[1],foreground:bool=True,nothreads:bool=True,fusedebug:bool=False, overwrite_rename_dest:bool=default_overwrite_rename_dest(),debug:bool=False,log_in_file:str|None=None,log_in_console:bool=True,log_in_syslog:bool=False,symlink_creation_windows:symlink_creation_windows_type=default_symlink_creation_windows(),rellinks:bool=default_rellinks()):
    if not root:
        raise ValueError("Root directory must be specified")
    if patterns:
        print("Excluded patterns: ", patterns)
    
    if debug:
        print("Verbose mode enabled",flush=True)
        
    if not cache_dir:
        cache_dir = os.path.join(user_cache_dir("PassthroughFS"), base64.b64encode(root.encode()).decode())
        print("Using default cache directory:", cache_dir)
    os.makedirs(name=cache_dir, exist_ok=True)

    #Check symlink_creation_windows
    if symlink_creation_windows not in get_args(symlink_creation_windows_type):
        raise ValueError(f"symlink_creation_windows must be one of {get_args(symlink_creation_windows_type)}")
    
    fuse = FUSE(PassthroughFS(root, patterns, cache_dir,overwrite_rename_dest=overwrite_rename_dest,debug=debug,log_in_file=log_in_file,log_in_console=log_in_console,log_in_syslog=log_in_syslog,symlink_creation_windows=symlink_creation_windows,mountpoint=mountpoint), mountpoint,foreground=foreground,nothreads=nothreads,debug=fusedebug,uid=uid,gid=gid,rellinks=rellinks)

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
