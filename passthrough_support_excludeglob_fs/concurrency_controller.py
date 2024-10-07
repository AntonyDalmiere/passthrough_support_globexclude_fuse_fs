from multiprocessing.managers import SyncManager
from multiprocessing.managers import DictProxy
from threading import Lock
from typing import Any, Dict
from contextlib import nullcontext
class ConcurrencyControllerMixIn:
    """Mixin for controlling concurrency in file system operations."""

    def __init__(self) -> None:
        #Check if SyncManager is already running
        self.manager = SyncManager()
        self.manager.start()  # Start the manager's server
        print("Started new manager.", flush=True)
        self.dict_of_locks: DictProxy[str, Lock] = self.manager.dict()
    def get_filelock_for_path(self, path: str) -> Lock:
        #Check if path is already in dict
        #print content of dict
        if path in self.dict_of_locks:
            return self.dict_of_locks[path]
        #Create a lock for the path
        else:
            lock = self.manager.Lock()
            #Add lock to dict
            self.dict_of_locks[path] = lock
            return lock
    def __call__(self, op: str, path: str, *args: Any) -> Any:
        """
        Call the given operation with concurrency control.

        Args:
            op (str): Operation name.
            path (str): Path to the file/directory.
            *args: Additional arguments.
        """
        #Check if operation is a write operation
        if op in ['rename','write','truncate','utimens','read','getattr','unlink','fsync','open','create','access','chmod','chown','release','readlink','rmdir','mkdir']:
            #Create a lock for the file
            lock = self.get_filelock_for_path(path)
        else:
            #Create a dumy context manager
            lock = nullcontext()

        with lock:
            # Perform the operation here
            return getattr(self, op)(path, *args)