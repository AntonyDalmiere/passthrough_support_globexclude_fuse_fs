# PassthroughSupportExcludeGlobFS: A Union Filesystem with Glob Pattern Exclusion

![Pepy Total Downlods](https://img.shields.io/pepy/dt/passthrough-support-excludeglob-fs)
![PyPI - Version](https://img.shields.io/pypi/v/passthrough-support-excludeglob-fs)
[![CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](http://creativecommons.org/licenses/by-nc-nd/4.0/)

PassthroughSupportExcludeGlobFS is a user-space filesystem (FUSE) written in Python that provides a union mount functionality with the added power of glob pattern exclusion. It allows you to seamlessly merge the contents of two directories, while selectively excluding files or folders based on flexible glob patterns.

## Key Features

- **Union Mount:** Combine the contents of two directories into a single, unified view.
- **Glob Pattern Exclusion:** Fine-grained control over which files and directories are included or excluded from two directories.
- **Cross-Platform:** Works seamlessly on Linux, macOS (in theory but untested), and Windows.
- **Easy to Use:** Simple CLI interface and Python API for integration into your projects.

## Use Cases

- **Configuration Management:** Overlay custom configurations on top of default settings.
- **Data Versioning:** Track changes to files and directories by maintaining a separate "cache" directory.
- **Selective Syncing:** Synchronize only specific files or folders between two locations.
- **Sandboxing:** Isolate applications or processes by redirecting specific files or directories to a controlled environment.
- **Development Workflows:** Manage different versions of code or assets by merging and excluding specific files.

## Installation

### Prerequisites

- **Python 3.6 or higher**
- **FUSE library:**
    - **Linux:** Install the `fuse` package using your distribution's package manager (e.g., `apt-get install fuse` on Debian/Ubuntu).
    - **macOS:** Install [OSXFUSE](https://osxfuse.github.io/).
    - **Windows:** Install [WinFsp](https://winfsp.dev/).

### Installing PassthroughSupportExcludeGlobFS

```bash
pip install passthrough-support-excludeglob-fs
```

## Usage

### Command-Line Interface

```
passthrough_support_excludeglob_fs <mountpoint> -o root=<root_directory>,[options]
```

**Options:**

- `root=<root_directory>`: The path to the lower directory (required). Use `\` to escape `,` and `=`.
- `patterns=<pattern1:pattern2:patternN>`: A colon-separated list of glob patterns to exclude from root. All files and directories matching these patterns will be stored in the cache directory (default none). Use `\` to escape `:`.
- `cache_dir=<cache_directory>`: The path to the upper directory (defaults to a cache directory within the user's cache folder). Use `\` to escape `,` and `=`.
- `uid=<user_id>`: The user ID to own the mounted filesystem (defaults to the current user).
- `gid=<group_id>`: The group ID to own the mounted filesystem (defaults to the current group).
- `foreground=<True|False>`: Run PassthroughSupportExcludeGlobFS in the foreground (default true).
- `nothreads=<True|False>`: Disable multi-threading (default true because untested).
- `overwrite_rename_dest=<True|False>`: When renaming, if `True`, overwrite the destination file if it already exists. If `False`, the rename operation will fail if the destination file already exists. The default behavior is `False` on Windows and `True` on Linux and macOS.
- `debug=<True|False>`: Enable logging. Default is `False`. It must be enabled to use the `log_in_file`, `log_in_console` and `log_in_syslog` options. It is independent of `fusedebug` option. Be careful, it can generate a lot of logs.
  - `log_in_syslog=<True|False>`: Log to the system log. Default is `False`. To use this option on Windows and so that the log is visible in the Windows Event Viewer, you must run the program as an administrator. However, it is not recommended to use this option on Windows because it can saturate the WIndows system log.
  - `log_in_file=<log_file_path|None>`: Log to a file instead of the console. Default is `None` which means no log file.
  - `log_in_console=<True|False>`: Log to the console. Default is `True`.
- `fusedebug=<True|False>`: Enable native FUSE debugging. Default is `False`. It is independent of `debug`, `log_in_file`, `log_in_console` and `log_in_syslog` options and always prints to the console. Be careful, it can also generate a lot of logs.
- `symlink_creation_windows=<skip|error|copy|create_lnkfile|real_symlink>`: Define how to handle symlinks created on Windows. Default is `real_symlink` with fallback to `error` if there is insufficient privileges. The possible values are:
  - `skip`: Skip the symlink creation. Fail silently.
  - `error`: Raise an error at the time of symlink creation.
  - `copy`: Copy the target file to the symlink location.
  - `create_lnkfile`: Create a new lnk file in the symlink location. Also resolve .lnk files as symlinks.
  - `real_symlink`: Real Windows symlink. Backed by NTFS ReparsePoint. Requires administrator privileges.
- `rellinks=<True|False>`: Convert POSIX absolute symlinks to drive-relative symlinks. Default is `True` on Windows (mandatory for symlinks to work) and `False` on Linux and macOS.



**Example 1:**

```bash
passthrough_support_excludeglob_fs /mnt/union -o root=/path/to/lower,patterns='**/*.log/*:**/*.tmp/*'
```

This command will mount a union filesystem at `/mnt/union`, merging the contents of `/path/to/lower` with a cache directory. All files matching the patterns `**/*.log/*` and `**/*.tmp/*` will be excluded from the root directory and stored somewhere in the cache directory.

**Example 2:**


```bash
passthrough_support_excludeglob_fs /mnt/union -o root=/path/to/lower,patterns='**/*.log/*:**/*.tmp/*',cache_dir=/path/to/cache
```

This command will mount a union filesystem at `/mnt/union`, merging the contents of `/path/to/lower` with a cache directory. All files matching the patterns `**/*.log/*` and `**/*.tmp/*` will be excluded from the root directory and stored in the cache directory `/path/to/cache`.

**Example 3:**

```bash
passthrough_support_excludeglob_fs /mnt/union -o root=/path/to/lower,patterns='**/*.log/*:**/*.tmp/*',cache_dir=/path/to/cache,overwrite_rename_dest=True
```

Same as above but can resolve issues with renaming files.

**Example 4:**

```bash
passthrough_support_excludeglob_fs /mnt/union -o root=/path/to/lower,patterns='**/*.log/*:**/*.tmp/*',cache_dir=/path/to/cache,overwrite_rename_dest=True,debug=True
```

Same as above but with debug enabled.

### Python API

```python
from passthrough_support_excludeglob_fs import start_passthrough_fs

# Start the filesystem
start_passthrough_fs(mountpoint='/mnt/union', root='/path/to/lower', patterns=['**/*.log/*', '**/*.tmp/*'], cache_dir='/path/to/cache' )
```
Like in the CLI, it will mount a union filesystem at `/mnt/union`, merging the contents of `/path/to/lower` with a cache directory. All files matching the patterns `**/*.log/*` and `**/*.tmp/*` will be excluded from the root directory and stored somewhere in the cache directory. The function is blocking and return only if a fatal error in the filesystem occurs. Note the function provide type hints.


## Glob Pattern Syntax

PassthroughSupportExcludeGlobFS uses the [globmatch](https://pypi.org/project/globmatch/2.0.0/) library for glob pattern matching. The following wildcards are supported:

- `*`: Matches any number of characters (including zero).
- `?`: Matches any single character.
- `[abc]`: Matches any character within the brackets.
- `[a-z]`: Matches any character within the range.
- `{a,b,c}`: Matches any of the patterns within the braces.
- `**`: Matches any number of directories recursively.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

## License

PassthroughSupportExcludeGlobFS is licensed under the CC-BY-NC-ND License. See the [LICENCE](LICENCE) file for details.



## FAQ

**Q: What sets `passthrough_support_excludeglob_fs` apart from other union filesystems like UnionFS, OverlayFS, and mergerfs?**

**A:** `passthrough_support_excludeglob_fs` offers a unique combination of union mount capabilities with glob pattern exclusion. This allows you to merge directories while precisely controlling which files and folders are included or excluded. It's particularly useful for selective syncing and providing flexibility that other union filesystems might not offer allowing you to do *selective mouting*.

**Q: How do I unmount the filesystem?**

**A:** On Linux and macOS, you can use the `fusermount -u <mountpoint>` command. On Windows, you can use the "Unmount" option in the WinFsp context menu for the mountpoint.

**Q: Can I use multiple glob patterns for exclusion?**

**A:** Yes, you can specify multiple glob patterns separated by colons (`:`) in the `patterns` option.

**Q: What happens if a file exists in both the root and cache directories?**

**A:** The most recent file take precedence.

**Q: What happen if an excluded file already exist on root directory?**

**A:** The file will be moved automatically to the cache directory at the first access. 

**Q: Can I exclude entire directories?**

**A:** Yes, you can use glob patterns that match directory names, such as `**/logs` to exclude the entire `logs` directory and its contents.

**Q: Is PassthroughSupportExcludeGlobFS compatible with symbolic links?**

**A:** Yes, PassthroughSupportExcludeGlobFS supports symbolic links. However some behavior may be unexpected with relative target links. Note `mklink` is untested on Windows.


**Q: Can I use PassthroughSupportExcludeGlobFS in a production environment?**

**A:** PassthroughSupportExcludeGlobFS is intended for testing and development purposes. While it is stable, it may not be suitable for production use.

**Q: Why the CLI options are weird?**

**A:** The CLI options are designed to be consistent with the mount options. This allows you to use PassthroughSupportExcludeGlobFS with existing FUSE tools and libraries.

**Q: Why it is slow to access files?**

**A:** The first access to a misplaced file will trigger a move operation to the right directory. This operation can be slow for large files or directories. However it should be fast for subsequent accesses.

**Q: What is the default cache directory?**

**A:** The default cache directory is a subdirectory within the user's cache folder. On Linux and macOS, this is typically `~/.cache/passthrough-support-excludeglob-fs`. On Windows, it is `%LOCALAPPDATA%\passthrough-support-excludeglob-fs`. The name of the subdirectory is then the base64 encoded root directory path.

For example, if the root directory is `/home/user/doc`, the cache directory will be `~/.cache/passthrough-support-excludeglob-fs/L2hvbWUvdXNlci9kb2M=`.

**Q: What are common bugs?**

**A:** Common know bugs:
- Metadata time (`ctime`,`atime`,`mtime`) are sometime updated even if the file is not accessed or modified. It can happen during the first access of a misplaced file.
- The filesystem is not thread safe. It is recommended to keep the `nothreads` option to `True`.
- Instability with .lnk backed symlinks on Windows.
- Exclude glob patterns should never be relative to root directory. It is recommended to always prefix with `**/`.
- The rename operation can be slow because it is internally implemented with a copy-and-delete operation. This operation can be slow for large files or directories. It is implemented this way to mitigate the non-deterministic order of operations. For example, the kernel or FUSE may reorder the operations and block the rename operation.

**Q: How can I contribute to PassthroughSupportExcludeGlobFS?**

**A:** We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on reporting issues, submitting pull requests, and contributing to the project.

**Q: Where can I get help or ask questions?**

**A:** You can open an issue on the GitHub repository.