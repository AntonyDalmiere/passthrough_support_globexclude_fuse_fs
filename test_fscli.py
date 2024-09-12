from pathlib import Path
import pytest
import os
import shutil
import subprocess
import tempfile
import time
import pytest
from test_fs import determine_mountdir_based_on_os

def clean_up(root_dir: str | None, mountpoint_dir: str | None, process: subprocess.Popen, cache_dir: str | None = None):
    try:
        process.kill()
        time.sleep(0.5)
    except Exception:
        pass

    if root_dir and os.path.exists(root_dir):
        try:
            shutil.rmtree(root_dir)
        except Exception:
            pass

    if mountpoint_dir and os.path.exists(mountpoint_dir):
        try:
            shutil.rmtree(mountpoint_dir)
        except Exception:
            pass

    if cache_dir and os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
        except Exception:
            pass
@pytest.fixture
def virtual_env(tmp_path) -> Path:
    """Create a virtual environment for testing."""
    venv_dir = tmp_path / "venv"
    if os.name == 'nt':
        subprocess.check_call(["python3.exe", "-m", "venv", str(venv_dir)])
        subprocess.check_call([str(venv_dir / "Scripts" / "pip"), "install", "."])
    else:
        subprocess.check_call(["python3", "-m", "venv", str(venv_dir)])
        subprocess.check_call([str(venv_dir / "bin" / "pip"), "install", "."])
    return venv_dir

@pytest.fixture
def command_location(virtual_env)-> Path:
    """Get the location of commands sych as passthrough_support_excludeglob_fs or pip or python."""
    if os.name == 'nt':
        return virtual_env / "Scripts"
    else:
        return virtual_env / "bin"
@pytest.mark.xdist_group(name="cli")
@pytest.mark.parametrize("complementary_option",['',',patterns=**/*.txt',',patterns=**/*.txt:**/exc/*'])
def test_cli(command_location: Path,complementary_option):
    """Test the CLI of the filesystem."""

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = determine_mountdir_based_on_os()

    # Run the CLI command in a separate process
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir}{complementary_option}",
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")


    time.sleep(5)

    #create file in the underlying filesystem
    with open(os.path.join(root_dir, 'test'), 'w') as f:
        f.write('test')

    # Verify the file is accessible in the mounted filesystem
    assert os.path.exists(os.path.join(mountpoint_dir, 'test'))

    # Verify the content of the file
    with open(os.path.join(mountpoint_dir, 'test'), 'r') as f:
        assert f.read() == 'test'

    #Test the exclude glob
    with open(os.path.join(mountpoint_dir, 'test.txt'), 'w') as f:
        f.write('test')

    #Check if the file is excluded
    assert os.path.exists(os.path.join(mountpoint_dir, 'test.txt'))
    #If we are in the paramtetrise '**/*.txt' case, the file should not be present in root_dir
    if '**/*.txt' in complementary_option:
        assert not os.path.exists(os.path.join(root_dir, 'test.txt'))

    # create dir exc and file in it
    os.mkdir(os.path.join(mountpoint_dir, 'exc'))
    with open(os.path.join(mountpoint_dir, 'exc', 'test'), 'w') as f:
        f.write('test')
    assert os.path.exists(os.path.join(mountpoint_dir, 'exc', 'test'))
    #If we are in the paramtetrise '**/exc/*' case, the file should not be present in root_dir
    if '**/exc/*' in complementary_option:
        assert not os.path.exists(os.path.join(root_dir, 'exc', 'test'))



    #test rename of directory
    os.rename(os.path.join(mountpoint_dir, 'exc'),os.path.join(mountpoint_dir, 'exc2'))
    assert os.path.exists(os.path.join(mountpoint_dir, 'exc2', 'test'))
    assert not os.path.exists(os.path.join(mountpoint_dir, 'exc', 'test'))
    assert not os.path.exists(os.path.join(mountpoint_dir, 'exc'))

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])

    clean_up(root_dir=root_dir, mountpoint_dir=mountpoint_dir, process=process)

#Same as above but will manually specify cache_dir to also cheack each time the presence of excluded dir in it
@pytest.mark.xdist_group(name="cli")
@pytest.mark.parametrize("complementary_option",['',',patterns=**/*.txt',',patterns=**/*.txt:**/exc/*',',patterns=**/*.txt:**/exc/*'])
def test_cli_cache(command_location,complementary_option):
    """Test the CLI of the filesystem."""

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = determine_mountdir_based_on_os()
    cache_dir = tempfile.mkdtemp()

    # Run the CLI command in a separate process
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir},cache_dir={cache_dir}{complementary_option}",
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")


    time.sleep(5)

    #create file in the underlying filesystem
    with open(os.path.join(root_dir, 'test'), 'w') as f:
        f.write('test')

    # Verify the file is accessible in the mounted filesystem
    assert os.path.exists(os.path.join(mountpoint_dir, 'test'))

    # Verify the content of the file
    with open(os.path.join(mountpoint_dir, 'test'), 'r') as f:
        assert f.read() == 'test'

    #Test the exclude glob
    with open(os.path.join(mountpoint_dir, 'test.txt'), 'w') as f:
        f.write('test')

    #Check if the file is excluded
    assert os.path.exists(os.path.join(mountpoint_dir, 'test.txt'))
    #If we are in the paramtetrise '**/*.txt' case, the file should not be present in root_dir and present in cache_dir
    if '**/*.txt' in complementary_option:
        assert not os.path.exists(os.path.join(root_dir, 'test.txt'))
        assert os.path.exists(os.path.join(cache_dir, 'test.txt'))

    # create dir exc and file in it
    os.mkdir(os.path.join(mountpoint_dir, 'exc'))
    with open(os.path.join(mountpoint_dir, 'exc', 'test'), 'w') as f:
        f.write('test')
    assert os.path.exists(os.path.join(mountpoint_dir, 'exc', 'test'))
    #If we are in the paramtetrise '**/exc/*' case, the file should not be present in root_dir and present in cache_dir
    if '**/exc/*' in complementary_option:
        assert not os.path.exists(os.path.join(root_dir, 'exc', 'test'))
        assert os.path.exists(os.path.join(cache_dir, 'exc', 'test'))

    #test rename of directory
    os.rename(os.path.join(mountpoint_dir, 'exc'),os.path.join(mountpoint_dir, 'exc2'))
    assert os.path.exists(os.path.join(mountpoint_dir, 'exc2', 'test'))
    assert not os.path.exists(os.path.join(mountpoint_dir, 'exc', 'test'))
    assert not os.path.exists(os.path.join(mountpoint_dir, 'exc'))

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])

    clean_up(root_dir, mountpoint_dir, process, cache_dir)

#Same as above but will use capsys to check the stdout against  the debug=False option
@pytest.mark.xdist_group(name="cli")
@pytest.mark.parametrize("debug", [True, False])
def test_cli_debug(command_location, debug):
    """Test the CLI of the filesystem."""
    import threading

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = determine_mountdir_based_on_os()

    # Run the CLI command in a separate process
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir},debug={debug}"]

    process = subprocess.Popen(cli_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1,shell=False,text=True)

    #Its a bit hacky but retrieving the stdout from the process with communicate or stdout.read* will cause a deadlock.
    class StdoutReader(threading.Thread):
        def __init__(self, process):
            threading.Thread.__init__(self)
            self.process = process
            self.stdout = ''
            self.daemon = True  # Daemonize the thread
        def run(self):
            for line in iter(self.process.stdout.readline, b''):
                self.stdout += line

    stdout_reader = StdoutReader(process)
    stdout_reader.start()



    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")


    time.sleep(5)

    #create file in the underlying filesystem
    with open(os.path.join(root_dir, 'test'), 'w') as f:
        f.write('test')

    # Verify the file is accessible in the mounted filesystem
    assert os.path.exists(os.path.join(mountpoint_dir, 'test'))

    # Verify the content of the file
    with open(os.path.join(mountpoint_dir, 'test'), 'r') as f:
        assert f.read() == 'test'

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])


    clean_up(root_dir=root_dir, mountpoint_dir=mountpoint_dir, process=process)
    out = stdout_reader.stdout
    if debug:
        assert 'Verbose mode enabled' in out
    else:
        assert 'Verbose mode enabled' not in out

@pytest.mark.xdist_group(name="cli")
def test_cli_escaping_patterns(command_location):
    """Test the CLI of the filesystem with escaping."""

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = determine_mountdir_based_on_os()
    cache_dir = tempfile.mkdtemp()

    # Run the CLI command in a separate process with escaping
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir},cache_dir={cache_dir},patterns=**/\\,test\\=file.txt:**/\\ exc\\ dir/*"
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")

    time.sleep(5)

    # Create file in the underlying filesystem
    with open(os.path.join(root_dir, ',test=file.txt'), 'w') as f:
        f.write('test')

    # Verify the file is accessible in the mounted filesystem
    assert os.path.exists(os.path.join(mountpoint_dir, ',test=file.txt'))

    # Verify the file is in the cache directory
    assert os.path.exists(os.path.join(cache_dir, ',test=file.txt'))
    # Verify the file is not in the root directory
    assert not os.path.exists(os.path.join(root_dir, ',test=file.txt'))
    
    # Create dir and file in it
    os.mkdir(os.path.join(mountpoint_dir, ' exc dir'))
    with open(os.path.join(mountpoint_dir, ' exc dir', 'test'), 'w') as f:
        f.write('test')
    assert os.path.exists(os.path.join(mountpoint_dir, ' exc dir', 'test'))

    # Verify the file is in the cache directory
    assert os.path.exists(os.path.join(cache_dir, ' exc dir', 'test'))

    # Verify the file is not in the root directory
    assert not os.path.exists(os.path.join(root_dir, ' exc dir', 'test'))

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])

    clean_up(root_dir=root_dir, mountpoint_dir=mountpoint_dir, process=process, cache_dir=cache_dir)

@pytest.mark.xdist_group(name="cli")
def test_cli_escaping_mountdir(command_location):
    """Test the CLI of the filesystem with escaping in mountdir."""

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = tempfile.mkdtemp(prefix="mount,dir=")

    # Run the CLI command in a separate process with escaping
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir}"
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")

    time.sleep(5)

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])

    clean_up(root_dir=root_dir, mountpoint_dir=mountpoint_dir, process=process)

@pytest.mark.xdist_group(name="cli")
def test_cli_escaping_rootdir(command_location):
    """Test the CLI of the filesystem with escaping in rootdir."""

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp(prefix="root,dir=")
    root_dir_to_pass = root_dir.replace(',', '\\,').replace('=', '\\=')
    mountpoint_dir = determine_mountdir_based_on_os()

    print(f'root_dir: {root_dir}')

    # Run the CLI command in a separate process with escaping
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir_to_pass}"
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")

    time.sleep(5)

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])

    clean_up(root_dir=root_dir, mountpoint_dir=mountpoint_dir, process=process)

@pytest.mark.xdist_group(name="cli")
def test_cli_escaping_cachedir(command_location):
    """Test the CLI of the filesystem with escaping in cachedir."""

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = determine_mountdir_based_on_os()
    cache_dir = tempfile.mkdtemp(prefix="cache,dir=")
    cache_dir_to_pass = cache_dir.replace(",", "\\,").replace("=", "\\=")


    # Run the CLI command in a separate process with escaping
    cli_command = [
        str(command_location / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir},cache_dir={cache_dir_to_pass}"
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(4)

    # Verify the filesystem is mounted
    try:
        os.listdir(mountpoint_dir)
    except OSError:
        pytest.fail("Filesystem failed to mount")

    time.sleep(5)

    # Unmount the filesystem
    if os.name == 'nt':
        # subprocess.check_call(["fusermount", "-u", mountpoint_dir])  # Replace with Windows equivalent
        pass
    else:
        subprocess.check_call(["fusermount", "-u", mountpoint_dir])

    clean_up(root_dir=root_dir, mountpoint_dir=mountpoint_dir, process=process, cache_dir=cache_dir)

