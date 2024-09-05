import os
import errno
from refuse.high import FuseOSError

def getattr_operation(self, path, fh=None):
    right_path = self.get_right_path(path)
    if not os.path.lexists(right_path):
        #Support symlink backed by lnk file
        if self.symlink_creation_windows == 'create_lnkfile' and os.name == 'nt':
            if not path.endswith('.lnk'):
                return getattr_operation(self, path + '.lnk', fh)
        raise FuseOSError(errno.ENOENT)
    st = os.lstat(right_path)
   
    #Edit st to make user RWX perm
    st_dict = dict((key, getattr(st, key,0)) for key in (
        'st_atime', 'st_ctime', 'st_gid', 'st_mtime',
        'st_nlink', 'st_size', 'st_uid','st_mode','st_birthtime','st_ino','st_dev'))
    #add st_birthtime to st_dict
    if os.name == 'nt':
        st_dict['st_mode'] = st_dict['st_mode'] | 0o777
        #Support symlink backed by lnk file
        if self.symlink_creation_windows == 'create_lnkfile' and path.endswith('.lnk'):
            st_dict['st_mode'] = st_dict['st_mode'] | 0o120000
    return st_dict
