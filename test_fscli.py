import pytest
import os
import shutil
import subprocess
import tempfile
import time
import pytest


@pytest.fixture
def virtual_env(tmp_path):
    """Create a virtual environment for testing."""
    venv_dir = tmp_path / "venv"
    subprocess.check_call(["python3", "-m", "venv", str(venv_dir)])
    return venv_dir

@pytest.mark.xdist_group(name="cli")
@pytest.mark.parametrize("complementary_option",['',',patterns=**/*.txt',',patterns=**/*.txt:**/exc/*'])
def test_cli(virtual_env,complementary_option):
    """Test the CLI of the filesystem."""

    # Install the filesystem package
    subprocess.check_call([str(virtual_env / "bin" / "pip"), "install", "."])

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = tempfile.mkdtemp()

    # Run the CLI command in a separate process
    cli_command = [
        str(virtual_env / "bin" / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir}{complementary_option}",
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(2)

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

    # Clean up
    process.terminate()
    shutil.rmtree(root_dir)
    shutil.rmtree(mountpoint_dir)


#Same as above but will manually specify cache_dir to also cheack each time the presence of excluded dir in it
@pytest.mark.xdist_group(name="cli")
@pytest.mark.parametrize("complementary_option",['',',patterns=**/*.txt',',patterns=**/*.txt:**/exc/*',',patterns=**/*.txt:**/exc/*'])
def test_cli_cache(virtual_env,complementary_option):
    """Test the CLI of the filesystem."""

    # Install the filesystem package
    subprocess.check_call([str(virtual_env / "bin" / "pip"), "install", "."])

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = tempfile.mkdtemp()
    cache_dir = tempfile.mkdtemp()

    # Run the CLI command in a separate process
    cli_command = [
        str(virtual_env / "bin" / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir},cache_dir={cache_dir}{complementary_option}",
    ]
    process = subprocess.Popen(cli_command)

    # Wait for the filesystem to mount
    time.sleep(2)

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

    # Clean up
    process.terminate()
    shutil.rmtree(root_dir)
    shutil.rmtree(mountpoint_dir)
    shutil.rmtree(cache_dir)

#Same as above but will use capsys to check the stdout against  the debug=False option
@pytest.mark.xdist_group(name="cli")
@pytest.mark.parametrize("debug", [True, False])
def test_cli_debug(virtual_env, debug):
    """Test the CLI of the filesystem."""

    # Install the filesystem package
    subprocess.check_call([str(virtual_env / "bin" / "pip"), "install", "."])

    # Create temporary directories for root and mountpoint
    root_dir = tempfile.mkdtemp()
    mountpoint_dir = tempfile.mkdtemp()

    # Run the CLI command in a separate process
    cli_command = [
        str(virtual_env / "bin" / "passthrough_support_excludeglob_fs"),
        mountpoint_dir,
        "-o",
        f"root={root_dir},debug={debug}"]
    process = subprocess.Popen(cli_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the filesystem to mount
    time.sleep(2)

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

    # Clean up
    process.terminate()
    shutil.rmtree(root_dir)
    shutil.rmtree(mountpoint_dir)

    out, err = process.communicate()
    if debug:
        assert b'Verbose mode enabled' in out
    else:
        assert b'Verbose mode enabled' not in out
