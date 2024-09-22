import os
import stat
import errno
if os.name == 'nt':
    from ctypes import windll, wintypes, c_void_p
    import msvcrt
    # Define INVALID_HANDLE_VALUE
    INVALID_HANDLE_VALUE = c_void_p(-1).value

def open_operation(self, path, flags) -> int:
    right_path = self.get_right_path(path)
    
    # Check if it's a symbolic link
    if stat.S_ISLNK(os.lstat(right_path).st_mode):
        return self.open(self.readlink(path), flags)
    
    # Handle file existence and opening
    if os.path.lexists(right_path):
        # flags |= os.O_DIRECT
        return _open_windows(right_path, flags) if os.name == 'nt' else os.open(right_path, flags)
    
    # Handle file creation if it does not exist
    if flags & os.O_CREAT:
        return os.open(right_path, flags, mode=0o777)
    
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

def _open_windows(path, flags):
    FILE_ATTRIBUTE_NORMAL = 0x80 | 0x20  # Normal filew with backup semantics
    GENERIC_READ_WRITE = 0x80000000 | 0x40000000  # Read and write access
    FILE_SHARE_ALL = 0x1 | 0x2 | 0x4  # Share read, write, and delete access
    CREATE_ALWAYS = 2
    OPEN_EXISTING = 3

    creation_disposition = OPEN_EXISTING if os.path.exists(path) else CREATE_ALWAYS

    handle = windll.kernel32.CreateFileW(
        path,
        GENERIC_READ_WRITE,
        FILE_SHARE_ALL,
        None,
        creation_disposition,
        FILE_ATTRIBUTE_NORMAL,
        None
    )

    if handle == INVALID_HANDLE_VALUE:
        raise OSError(windll.kernel32.GetLastError())
    #Convert the handle to a python compatible  file descriptor
    return msvcrt.open_osfhandle(handle, 0)