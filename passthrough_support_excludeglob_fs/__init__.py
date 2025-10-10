from .main import start_passthrough_fs, cli

try:
    from .gui import launch_gui
    __all__ = ['start_passthrough_fs', 'cli', 'launch_gui']
except ImportError:
    # GUI not available (e.g., tkinter not installed)
    __all__ = ['start_passthrough_fs', 'cli']
