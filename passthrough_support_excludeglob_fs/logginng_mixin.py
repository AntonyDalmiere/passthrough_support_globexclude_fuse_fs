import ctypes
import logging
import os
from typing import Any
from syslog2 import SysLogHandler


def is_admin():
    try:
        # Unix-based systems
        return os.getuid() == 0
    except AttributeError:
        # Windows
        return ctypes.windll.shell32.IsUserAnAdmin() != 0 # type: ignore
    
class LoggingMixIn:
    """Mixin for logging operations."""

    def __init__(self, enable: bool, log_in_file: str | None,log_in_console: bool, log_in_syslog: bool) -> None:

        self.log: logging.Logger = logging.getLogger('passthrough_support_excludeglob_fs')
        self.log.setLevel(logging.DEBUG)  # Set the logging level to DEBUG
        if not enable:
            #Create a dummy logger
            self.log.addHandler(logging.NullHandler())
            return
        log_format = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')


        if log_in_syslog:
            #If  user is not windows admin, we need to warn him
            if not is_admin() and os.name == 'nt':
                log_in_syslog = False
                log_in_console = True
                self.log.error("You are not an administrator, syslog in windows event log will not work")
            else:
                syslog_handler = SysLogHandler(program=self.log.name)
                syslog_handler.setFormatter(log_format)
                self.log.addHandler(syslog_handler)

        if log_in_file:
            file_handler = logging.FileHandler(log_in_file)
            file_handler.setFormatter(log_format)
            self.log.addHandler(file_handler)

        if log_in_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_format)
            self.log.addHandler(console_handler)


    def __call__( self, op: str, path: str, *args: Any, ) -> Any:
        """
        Call the given operation with logging.

        Args:
            op (str): Operation name.
            path (str): Path to the file/directory.
            *args: Additional arguments.

        Returns:
            Any: Operation result.

        Raises:
            OSError: If an OSError occurred.
        """
        ret = '[Unhandled Exception]'
        try:
            ret = getattr(self, op)(path, *args)
            return ret
        except OSError as e:
            ret = str(e)
            raise
        finally:
            self.log.debug( '%s(p=%s, %s) => %s', op, path, repr(args), ret)