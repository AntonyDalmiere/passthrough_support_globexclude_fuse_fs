import os
import shutil
import errno
from refuse.high import FuseOSError
import pylnk3

from typing import Callable, Type
...
def create_for_path_generator(size: int, st_mode: int) -> Type[Callable[[str], pylnk3.PathSegmentEntry]]:
    """
    Generate a function that creates a PathSegmentEntry for a given path.

    Args:
        size (int): The size of the entry.
        st_mode (int): The mode of the entry.

    Returns:
        callable: A function that creates a PathSegmentEntry for a given path.
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

def symlink_operation(self, link_location: str, name: str) -> None:
    """
    Create a symbolic link to name at link_location.

    Args:
        link_location (str): The path of the symbolic link to be created.
        name (str): The path of the target of the symbolic link.

    Returns:
        None
    """
    link_location_path: str = self.get_right_path(link_location)
    if os.name != 'nt':
        os.symlink(name, link_location_path)
    else:
        if self.symlink_creation_windows == 'skip':
            #add the dest file to the list of dest file that must be ignored when they are the source of a rename
            self.renameExcludedSourceFiles.append(link_location)
            return
        if self.symlink_creation_windows == 'error':
            raise FuseOSError(errno.ENOTSUP)
        if self.symlink_creation_windows == 'copy':
            # Copy file
            self.log.debug("Copying symlink content from %s to %s", name, link_location_path)
            shutil.copy2(self.get_right_path(name), link_location_path)
            return
        if self.symlink_creation_windows == 'create_lnkfile':
            # get path of target and dest files
            self.log.debug("Creating lnk file from %s to %s", name, link_location_path)
            #Check if name is relatuve or absolute
            original_name = name
            if name.startswith('/'):
                name = self.mountpoint + os.path.sep + name[1:]
            self.renameAppendLnkToFilenameFiles.append(link_location)
            st_mode = self.getattr(original_name)['st_mode']
            st_size = self.getattr(original_name)['st_size']

            pylnk3.PathSegmentEntry.create_for_path = create_for_path_generator(st_size, st_mode)

            levels = list(pylnk3.path_levels(name))

            pylnk3.for_file(name, link_location_path)
        if self.symlink_creation_windows == 'real_symlink':
            # determine if target is a dir
            target_name_is_dir: bool = False
            try:
                target_name_is_dir = os.path.isdir(name)
            except Exception:
                self.log.warning("Could not determine if %s is a directory", name)
            # create real symlink
            os.symlink(name, link_location_path, target_is_directory=target_name_is_dir)
            return
