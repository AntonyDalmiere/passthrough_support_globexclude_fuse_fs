# PassthroughSupportExcludeGlobFS: A Union Filesystem with Glob Pattern Exclusion

[![CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](http://creativecommons.org/licenses/by-nc-nd/4.0/)


PassthroughSupportExcludeGlobFS is a user-space filesystem (FUSE) written in Python that provides a union mount functionality with the added power of glob pattern exclusion. It allows you to seamlessly merge the contents of two directories, while selectively excluding files or folders based on flexible glob patterns.

## Key Features

- **Union Mount:** Combine the contents of two directories into a single, unified view.
- **Glob Pattern Exclusion:** Fine-grained control over which files and directories are included or excluded from the upper or lower directory.
- **Performance:** Designed for efficiency, minimizing overhead and maximizing throughput.
- **Cross-Platform:** Works seamlessly on Linux, macOS, and Windows.
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
pip install passthrough-support-excludeglob
```

## Usage

### Command-Line Interface

```
passthrough_support_excludeglob_fs <mountpoint> -o root=<root_directory>,[options]
```

**Options:**

- `root=<root_directory>`: The path to the lower directory (required).
- `patterns=<pattern1:pattern2:patternN>`: A colon-separated list of glob patterns to exclude from root. All files and directories matching these patterns will be stored in the cache directory (default none).
- `cache_dir=<cache_directory>`: The path to the upper directory (defaults to a cache directory within the user's cache folder).
- `uid=<user_id>`: The user ID to own the mounted filesystem (defaults to the current user).
- `gid=<group_id>`: The group ID to own the mounted filesystem (defaults to the current group).
- `foreground=<True|False>`: Run PassthroughSupportExcludeGlobFS in the foreground (default true).
- `nothreads=<True|False>`: Disable multi-threading (default true because untested).
- `debug=<True|False>`: Enable debug logging.

**Example:**

```bash
passthrough_support_excludeglob_fs /mnt/union -o root=/path/to/lower,patterns='**/*.log:**/*.tmp'
```

This command will mount a union filesystem at `/mnt/union`, merging the contents of `/path/to/lower` with a cache directory. All files matching the patterns `**/*.log` and `**/*.tmp` will be excluded from the lower directory and stored in the  user local directory.

### Python API

```python
from passthrough_support_excludeglob_fs import start_passthrough_fs

# Start the filesystem
start_passthrough_fs(mountpoint='/mnt/union', root='/path/to/lower', patterns=['**/*.log', '**/*.tmp'], cache_dir='/path/to/cache' )
```

## Glob Pattern Syntax

PassthroughSupportExcludeGlobFS uses the `globmatch` library for glob pattern matching. The following wildcards are supported:

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

**A:** Yes, PassthroughSupportExcludeGlobFS supports symbolic links. However, note that symbolic links to excluded files will be resolved within the cache directory. However some behavior may be unexpected with relative target links. Also note (`mklink`) it is untested on Windows.

**Q: How can I contribute to PassthroughSupportExcludeGlobFS?**

**A:** We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on reporting issues, submitting pull requests, and contributing to the project.

**Q: Where can I get help or ask questions?**

**A:** You can open an issue on our GitHub repository.