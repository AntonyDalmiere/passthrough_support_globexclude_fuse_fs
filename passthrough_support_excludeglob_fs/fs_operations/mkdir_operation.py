import os
import errno
from typing import Literal
from refuse.high import FuseOSError
from .access_operation import _access

def mkdir_operation(self, path, mode) -> None:
    right_path = self.get_right_path(path)
    #Retrieving the parent directory (path is already a dir)
    parent_dir = os.path.dirname(path)
    parent_dir_right_path = os.path.dirname(right_path)
    #If access to parent directory is not allowed, raise an error
    #We intentionallty check against os.R_OK instead of os.W_OK because we want to create the directory even if the parent directory is not writable to prevent bug in the translation of Unix permissions to Windows permissions
    if not _access(self,parent_dir, os.R_OK):
        raise FuseOSError(errno.ENOENT)
    makedirs(self,parent_dir_right_path, exist_ok=True)
    os.mkdir(right_path, mode)

def makedirs(self, path:str, exist_ok=False):
    """
    Recursively create directories at the specified path.

    Args:
        path (str): The path of the directory to be created.
        exist_ok (bool, optional): If True, no exception will be raised if the directory already exists. Defaults to False.

    Warning:
        The `path` argument must be already passed through the `get_right_path` method.
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