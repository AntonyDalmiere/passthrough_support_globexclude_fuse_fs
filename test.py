import os
import shutil
import stat
import subprocess
import tempfile
import threading
import unittest

import psutil
from main import start_passthrough_fs
import multiprocessing
import time
import random
import concurrent.futures
def determine_mountdir_based_on_os():
    if os.name == 'nt':
        return 'T:'
    else:
        return tempfile.mkdtemp()
    
def is_symlink(path):
    if os.lstat(path).st_mode & 0o120000 == 0o120000:
        return True
    else:
        return False

        
class TestFSOperations(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()
        self.mounted_dir = determine_mountdir_based_on_os()
        print(f'Temporary directory: {self.temp_dir} and mounted directory: {self.mounted_dir}')
        # Create a new process to launch the function start_passthrough_fs
        self.p = multiprocessing.Process(target=start_passthrough_fs, args=(self.mounted_dir, self.temp_dir))
        self.p.start()
        time.sleep(5)

    #create file in self.mounted_dir directory and check its effective presence in self.temp_dir 
    def test_create_file(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'testfile')
        self.assertTrue(os.path.exists(file_path2))
        

    def test_read_file(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'testfile')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    #same as read test but invert file_path1 and file_path2
    def test_write_file(self):
        file_path1 = os.path.join(self.temp_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'testfile')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_file_not_found(self):
        file_path = os.path.join(self.temp_dir, 'nonexistentfile')
        with self.assertRaises(FileNotFoundError):
            with open(file_path, 'r') as f:
                pass

    def test_write_to_read_only_file(self):
        file_path = os.path.join(self.temp_dir, 'readonlyfile')
        with open(file_path, 'w') as f:
            f.write('test data')
        os.chmod(file_path, 0o444)  # make the file read-only
        with self.assertRaises(PermissionError):
            with open(file_path, 'w') as f:
                f.write('new data')

    def test_delete_nonexistent_file(self):
        file_path = os.path.join(self.temp_dir, 'nonexistentfile')
        with self.assertRaises(FileNotFoundError):
            os.remove(file_path)

    def test_rename_nonexistent_file(self):
        file_path1 = os.path.join(self.temp_dir, 'nonexistentfile')
        file_path2 = os.path.join(self.temp_dir, 'newname')
        with self.assertRaises(FileNotFoundError):
            os.rename(file_path1, file_path2)

    def test_rename_file(self):
        file_path1 = os.path.join(self.temp_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'newname')
        os.rename(file_path1, file_path2)
        self.assertFalse(os.path.exists(file_path1))
        self.assertTrue(os.path.exists(file_path2))

    def test_rename_file_to_existing_file(self):
        file_path1 = os.path.join(self.temp_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'existingfile')
        with open(file_path2, 'w') as f:
            f.write('existing data')
        with self.assertRaises(FileExistsError):
            os.rename(file_path1, file_path2)

    def test_mkdir(self):
        dir_path = os.path.join(self.temp_dir, 'testdir')
        os.mkdir(dir_path)
        self.assertTrue(os.path.exists(dir_path))

    def test_rmdir(self):
        dir_path = os.path.join(self.temp_dir, 'testdir')
        os.mkdir(dir_path)
        os.rmdir(dir_path)
        self.assertFalse(os.path.exists(dir_path))

    def test_rmdir_nonexistent_dir(self):
        dir_path = os.path.join(self.temp_dir, 'nonexistentdir')
        with self.assertRaises(FileNotFoundError):
            os.rmdir(dir_path)

    def test_listdir(self):
        dir_path = os.path.join(self.temp_dir, 'testdir')
        os.mkdir(dir_path)
        file_path = os.path.join(dir_path, 'testfile')
        with open(file_path, 'w') as f:
            f.write('test data')
        entries = os.listdir(dir_path)
        self.assertEqual(entries, ['testfile'])

    def test_listdir_nonexistent_dir(self):
        dir_path = os.path.join(self.temp_dir, 'nonexistentdir')
        with self.assertRaises(FileNotFoundError):
            os.listdir(dir_path)

    def test_stat(self):
        file_path = os.path.join(self.temp_dir, 'testfile')
        with open(file_path, 'w') as f:
            f.write('test data')
        stat = os.stat(file_path)
        self.assertTrue(stat.st_size > 0)

    #benchmark the read speed with time measurment on the fs, dont fail, just print the byte per second
    def test_readspeed(self):
        file_path = os.path.join(self.temp_dir, 'testfile')
        with open(file_path, 'w') as f:
            f.write('a'*1000000)
        start = time.time()
        with open(file_path, 'r') as f:
            data = f.read()
        end = time.time()
        print(f"Read speed: {(len(data)/(end-start))/(1024*1024)} megabytes per second")

    def tearDown(self):
        self.p.kill()
        time.sleep(2)
        #remove the temporary directories even if they are not empty
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        shutil.rmtree(self.mounted_dir, ignore_errors=True)


class TestFSOperationsWithExclusion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()
        self.mounted_dir = determine_mountdir_based_on_os()
        print(f'Temporary directory: {self.temp_dir} and mounted directory: {self.mounted_dir}')
        # Create a new process to launch the function start_passthrough_fs
        self.p = multiprocessing.Process(target=start_passthrough_fs, args=(self.mounted_dir, self.temp_dir, ['*.txt','**/*.txt/*','**/*.config'], self.cache_dir))
        self.p.start()
        time.sleep(5)
        

    def test_create_file(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'testfile.txt')
        self.assertFalse(os.path.exists(file_path2))

    def test_create_file2(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'testfile')
        self.assertTrue(os.path.exists(file_path2))

    def test_write_file_totemp(self):
        file_path1 = os.path.join(self.temp_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_read_file(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    #same as test_read_file with file nested in excluded folder formated as : 'mounted_dir' = 'excluded pattern' = 'file.a'
    def test_read_file_complexpath(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt', 'file.a')
        #create the path to this file
        os.makedirs(os.path.dirname(file_path1), exist_ok=True)
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'testfile.txt', 'file.a')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_write_file_complexpathexcluded_is_written_goodplace(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt', 'file.a')
        #create the path to this file
        os.makedirs(os.path.dirname(file_path1), exist_ok=True)
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2: str = os.path.join(self.temp_dir, 'testfile.txt', 'file.a')
        self.assertFalse(os.path.exists(file_path2))

    def test_write_file_complexpathexcluded_is_written_goodplace2(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt', 'file.a')
        #create the path to this file
        os.makedirs(os.path.dirname(file_path1), exist_ok=True)
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.cache_dir, 'testfile.txt', 'file.a')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')
        
    def test_write_file_tocache(self):
        file_path1 = os.path.join(self.cache_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_file_not_found(self):
        file_path = os.path.join(self.temp_dir, 'nonexistentfile.txt')
        with self.assertRaises(FileNotFoundError):
            with open(file_path, 'r') as f:
                pass


    def test_rename_file(self):
        file_path1 = os.path.join(self.temp_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'newname.txt')
        os.rename(file_path1, file_path2)
        self.assertFalse(os.path.exists(file_path1))
        self.assertTrue(os.path.exists(file_path2))

    def test_rename_file_to_existing_file(self):
        file_path1 = os.path.join(self.temp_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.temp_dir, 'existingfile.txt')
        with open(file_path2, 'w') as f:
            f.write('existing data')
        with self.assertRaises(FileExistsError):
            os.rename(file_path1, file_path2)

    def test_mkdir(self):
        dir_path = os.path.join(self.temp_dir, 'testdir')
        os.mkdir(dir_path)
        self.assertTrue(os.path.exists(dir_path))

    def test_already_exclude_file(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.cache_dir, 'testfile.txt')
        with open(file_path2, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_rename_excluded_to_non_excluded(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'newname')
        os.rename(file_path1, file_path2)
        self.assertFalse(os.path.exists(file_path1))
        self.assertTrue(os.path.exists(file_path2))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'newname')))
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, 'testfile.txt')))

    def test_rename_non_excluded_to_excluded(self):
        file_path1 = os.path.join(self.mounted_dir, 'testfile')
        with open(file_path1, 'w') as f:
            f.write('test data')
        file_path2 = os.path.join(self.mounted_dir, 'newname.txt')
        os.rename(file_path1, file_path2)
        self.assertFalse(os.path.exists(file_path1))
        self.assertTrue(os.path.exists(file_path2))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'newname.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'newname.txt')))

    def test_write_large_file_excluded(self):
        file_path = os.path.join(self.mounted_dir, 'largefile.txt')
        large_data = 'a' * 10_000_000  # 10 MB of data
        with open(file_path, 'w') as f:
            f.write(large_data)
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'largefile.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'largefile.txt')))
        with open(file_path, 'r') as f:
            read_data = f.read()
        self.assertEqual(read_data, large_data)

    def test_concurrent_read_write(self):
        file_path = os.path.join(self.mounted_dir, 'concurrent.txt')
        with open(file_path, 'w') as f:
            f.write('initial data')
        
        def read_file():
            with open(file_path, 'r') as f:
                return f.read()
        
        def write_file():
            with open(file_path, 'a') as f:
                f.write('appended data')
        
        read_thread = threading.Thread(target=read_file)
        write_thread = threading.Thread(target=write_file)
        
        read_thread.start()
        write_thread.start()
        
        read_thread.join()
        write_thread.join()
        
        with open(file_path, 'r') as f:
            final_content = f.read()
        
        self.assertEqual(final_content, 'initial dataappended data')

    def test_symlink_excluded_file(self):
        #skip on windows
        if os.name == 'nt':
            self.skipTest('Symlinks are not supported on Windows')
        original_path = os.path.join(self.mounted_dir, 'original.txt')
        with open(original_path, 'w') as f:
            f.write('original content')
        
        symlink_path = os.path.join(self.mounted_dir, 'symlink.txt')
        os.symlink(original_path, symlink_path)
        
        #List all file and their stats
        debug_text = ""
        for file_name in os.listdir(self.mounted_dir):
            file_path = os.path.join(self.mounted_dir, file_name)
            file_stat = os.stat(file_path)
            debug_text += f"{file_name}: {file_stat}\n"

        self.assertTrue(os.path.exists(symlink_path))
        self.assertTrue(is_symlink(os.path.join(self.cache_dir,'symlink.txt')))
        with open(symlink_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'original content')

    def test_hardlink_excluded_file(self):
        #Assert raise an OSError exception
        with self.assertRaises(OSError):
            original_path = os.path.join(self.mounted_dir, 'original.txt')
            with open(original_path, 'w') as f:
                f.write('original content')
            
            hardlink_path = os.path.join(self.mounted_dir, 'hardlink.txt')
            os.link(original_path, hardlink_path)

    def test_move_file_between_directories(self):
        dir1 = os.path.join(self.mounted_dir, 'dir1')
        dir2 = os.path.join(self.mounted_dir, 'dir2')
        os.makedirs(dir1)
        os.makedirs(dir2)
        
        file_path1 = os.path.join(dir1, 'testfile.txt')
        with open(file_path1, 'w') as f:
            f.write('test data')
        
        file_path2 = os.path.join(dir2, 'testfile.txt')
        shutil.move(file_path1, file_path2)
        
        self.assertFalse(os.path.exists(file_path1))
        self.assertTrue(os.path.exists(file_path2))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'dir2', 'testfile.txt')))

    def test_rename_directory_with_excluded_files(self):
        dir1 = os.path.join(self.mounted_dir, 'dir1')
        os.makedirs(dir1)
        
        file_path1 = os.path.join(dir1, 'testfile1.txt')
        file_path2 = os.path.join(dir1, 'testfile2')
        
        with open(file_path1, 'w') as f:
            f.write('test data 1')
        with open(file_path2, 'w') as f:
            f.write('test data 2')
        
        dir2 = os.path.join(self.mounted_dir, 'dir2')
        os.rename(dir1, dir2)
        
        self.assertFalse(os.path.exists(dir1))
        self.assertTrue(os.path.exists(dir2))
        self.assertTrue(os.path.exists(os.path.join(dir2, 'testfile1.txt')))
        self.assertTrue(os.path.exists(os.path.join(dir2, 'testfile2')))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'dir2', 'testfile1.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'dir2', 'testfile2')))

    def test_rename_excluded_file_within_excluded_directory(self):
        os.makedirs(os.path.join(self.mounted_dir, 'excluded_dir.txt'))
        with open(os.path.join(self.mounted_dir, 'excluded_dir.txt', 'file.txt'), 'w') as f:
            f.write('test data')
        os.rename(os.path.join(self.mounted_dir, 'excluded_dir.txt', 'file.txt'),
                  os.path.join(self.mounted_dir, 'excluded_dir.txt', 'renamed.txt'))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt', 'renamed.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt', 'file.txt')))

    def test_rename_non_excluded_file_to_excluded_directory(self):
        with open(os.path.join(self.mounted_dir, 'non_excluded.file'), 'w') as f:
            f.write('test data')
        os.makedirs(os.path.join(self.mounted_dir, 'excluded_dir.txt'))
        os.rename(os.path.join(self.mounted_dir, 'non_excluded.file'),
                  os.path.join(self.mounted_dir, 'excluded_dir.txt', 'renamed.file'))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt', 'renamed.file')))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'non_excluded.file')))

    def test_rename_excluded_file_to_non_excluded_directory(self):
        with open(os.path.join(self.mounted_dir, 'excluded.txt'), 'w') as f:
            f.write('test data')
        os.makedirs(os.path.join(self.mounted_dir, 'non_excluded_dir'))
        os.rename(os.path.join(self.mounted_dir, 'excluded.txt'),
                  os.path.join(self.mounted_dir, 'non_excluded_dir', 'renamed.file'))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'non_excluded_dir', 'renamed.file')))
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, 'excluded.txt')))

    def test_rename_directory_with_mixed_content(self):
        os.makedirs(os.path.join(self.mounted_dir, 'mixed_dir'))
        with open(os.path.join(self.mounted_dir, 'mixed_dir', 'excluded.txt'), 'w') as f:
            f.write('excluded data')
        with open(os.path.join(self.mounted_dir, 'mixed_dir', 'non_excluded.file'), 'w') as f:
            f.write('non-excluded data')
        os.rename(os.path.join(self.mounted_dir, 'mixed_dir'),
                  os.path.join(self.mounted_dir, 'renamed_mixed_dir'))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'renamed_mixed_dir', 'excluded.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'renamed_mixed_dir', 'non_excluded.file')))

    def test_rename_excluded_directory_to_non_excluded_name(self):
        os.makedirs(os.path.join(self.mounted_dir, 'excluded_dir.txt'))
        with open(os.path.join(self.mounted_dir, 'excluded_dir.txt', 'file'), 'w') as f:
            f.write('test data')
        os.rename(os.path.join(self.mounted_dir, 'excluded_dir.txt'),
                  os.path.join(self.mounted_dir, 'non_excluded_dir'))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'non_excluded_dir', 'file')))
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt')))

    def test_rename_non_excluded_directory_to_excluded_name(self):
        os.makedirs(os.path.join(self.mounted_dir, 'non_excluded_dir'))
        with open(os.path.join(self.mounted_dir, 'non_excluded_dir', 'file.txt'), 'w') as f:
            f.write('test data')
        os.rename(os.path.join(self.mounted_dir, 'non_excluded_dir'),
                  os.path.join(self.mounted_dir, 'excluded_dir.txt'))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt', 'file.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'non_excluded_dir')))

    def test_rename_file_to_existing_excluded_file(self):
        with open(os.path.join(self.mounted_dir, 'source.file'), 'w') as f:
            f.write('source data')
        with open(os.path.join(self.mounted_dir, 'target.txt'), 'w') as f:
            f.write('target data')
        with self.assertRaises(FileExistsError):
            os.rename(os.path.join(self.mounted_dir, 'source.file'),
                      os.path.join(self.mounted_dir, 'target.txt'))

    def test_rename_excluded_file_to_existing_non_excluded_file(self):
        with open(os.path.join(self.mounted_dir, 'source.txt'), 'w') as f:
            f.write('source data')
        with open(os.path.join(self.mounted_dir, 'target.file'), 'w') as f:
            f.write('target data')
        with self.assertRaises(FileExistsError):
            os.rename(os.path.join(self.mounted_dir, 'source.txt'),
                      os.path.join(self.mounted_dir, 'target.file'))

    def test_rename_with_complex_exclusion_pattern(self):
        # Assuming '**/*.config' is an exclusion pattern
        os.makedirs(os.path.join(self.mounted_dir, 'dir1', 'subdir'))
        with open(os.path.join(self.mounted_dir, 'dir1', 'subdir', 'file.config'), 'w') as f:
            f.write('config data')
        os.rename(os.path.join(self.mounted_dir, 'dir1'),
                  os.path.join(self.mounted_dir, 'dir2'))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'dir2', 'subdir', 'file.config')))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'dir2', 'subdir', 'file.config')))

    def test_rename_large_directory_structure(self):
        # Create a large directory structure with mixed content
        root_dir = os.path.join(self.mounted_dir, 'large_dir')
        os.makedirs(root_dir)
        for i in range(10):
            subdir = os.path.join(root_dir, f'subdir_{i}')
            os.makedirs(subdir)
            for j in range(10):
                with open(os.path.join(subdir, f'file_{j}.{"txt" if j % 2 == 0 else "file"}'), 'w') as f:
                    f.write(f'data_{i}_{j}')

        os.rename(root_dir, os.path.join(self.mounted_dir, 'renamed_large_dir'))

        # Verify the renamed structure
        for i in range(10):
            for j in range(10):
                file_name = f'file_{j}.{"txt" if j % 2 == 0 else "file"}'
                if file_name.endswith('.txt'):
                    self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'renamed_large_dir', f'subdir_{i}', file_name)))
                else:
                    self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'renamed_large_dir', f'subdir_{i}', file_name)))

        self.assertFalse(os.path.exists(root_dir))
    
    def test_create_and_read_large_file(self):
        large_file_path = os.path.join(self.mounted_dir, 'large_file.bin')
        size = 100 * 1024 * 1024  # 100 MB
        with open(large_file_path, 'wb') as f:
            f.write(os.urandom(size))
        
        with open(large_file_path, 'rb') as f:
            content = f.read()
        
        self.assertEqual(len(content), size)

    def test_concurrent_file_operations(self):
        def worker(file_name, content):
            file_path = os.path.join(self.mounted_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(content)
            time.sleep(0.1)
            with open(file_path, 'r') as f:
                return f.read()

        threads = []
        results = {}
        for i in range(10):
            t = threading.Thread(target=lambda: results.update({f'file_{i}.txt': worker(f'file_{i}.txt', f'content_{i}')}))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for i in range(10):
            self.assertEqual(results[f'file_{i}.txt'], f'content_{i}')

    def test_file_permissions(self):
        file_path = os.path.join(self.mounted_dir, 'permissions_test.txt')
        with open(file_path, 'w') as f:
            f.write('test content')

        if os.name != 'nt': # POSIX
            os.chmod(file_path, 0o644)
            stat_result = os.stat(file_path)
            self.assertEqual(stat.S_IMODE(stat_result.st_mode), 0o644)

            os.chmod(file_path, 0o444)
            stat_result = os.stat(file_path)
            self.assertEqual(stat.S_IMODE(stat_result.st_mode), 0o444)
            with self.assertRaises(PermissionError):
                with open(file_path, 'w') as f:
                    f.write('should fail')
        else: # WINDOWS
            os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE)
            self.assertTrue(os.access(file_path, os.R_OK | os.W_OK))

            os.chmod(file_path, stat.S_IREAD)
            self.assertTrue(os.access(file_path, os.R_OK))
            self.assertTrue(os.access(file_path, os.W_OK))
       

    def test_file_timestamps(self):
        file_path = os.path.join(self.mounted_dir, 'timestamp_test.txt')
        with open(file_path, 'w') as f:
            f.write('test content')
        
        current_time = time.time()
        os.utime(file_path, (current_time, current_time))
        
        stat_result = os.stat(file_path)
        self.assertAlmostEqual(stat_result.st_atime, current_time, delta=1)
        self.assertAlmostEqual(stat_result.st_mtime, current_time, delta=1)

    def test_symlink_to_excluded_file(self):
        if os.name == 'nt':
            self.skipTest('Symlinks are not fully supported on Windows')
        
        excluded_file = os.path.join(self.mounted_dir, 'excluded.txt')
        with open(excluded_file, 'w') as f:
            f.write('excluded content')
        
        symlink_path = os.path.join(self.mounted_dir, 'symlink_to_excluded')
        os.symlink(excluded_file, symlink_path)
        
        self.assertTrue(os.path.islink(symlink_path))
        with open(symlink_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'excluded content')

    def test_rename_open_file(self):
        if(os.name == 'nt'):
            self.skipTest('Rename open file is not supported on Windows')
        file_path = os.path.join(self.mounted_dir, 'open_file.txt')
        new_path = os.path.join(self.mounted_dir, 'renamed_open_file.txt')
        
        with open(file_path, 'w') as f:
            f.write('initial content')
            os.rename(file_path, new_path)
            f.write(' additional content')
        
        with open(new_path, 'r') as f:
            content = f.read()
        
        self.assertEqual(content, 'initial content additional content')
        self.assertFalse(os.path.exists(file_path))
        self.assertTrue(os.path.exists(new_path))

    def test_create_file_in_nonexistent_directory(self):
        nested_file_path = os.path.join(self.mounted_dir, 'nonexistent', 'nested', 'file.txt')
        
        with self.assertRaises(FileNotFoundError):
            with open(nested_file_path, 'w') as f:
                f.write('test content')

    def test_move_directory_between_excluded_and_non_excluded(self):
        non_excluded_dir = os.path.join(self.mounted_dir, 'non_excluded_dir')
        excluded_dir = os.path.join(self.mounted_dir, 'excluded_dir.txt')
        
        os.makedirs(non_excluded_dir)
        with open(os.path.join(non_excluded_dir, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(non_excluded_dir, 'file2'), 'w') as f:
            f.write('content2')
        
        shutil.move(non_excluded_dir, excluded_dir)
        
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt', 'file1.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt', 'file2')))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'non_excluded_dir')))

        shutil.move(excluded_dir, non_excluded_dir)
        
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, 'non_excluded_dir', 'file1.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'non_excluded_dir', 'file2')))
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, 'excluded_dir.txt')))

    def test_delete_file(self):
        file_path = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path, 'w') as f:
            f.write('test data')
        os.remove(file_path)
        self.assertFalse(os.path.exists(file_path))

    def test_delete_directory(self):
        dir_path = os.path.join(self.mounted_dir, 'testdir')
        os.makedirs(dir_path)
        self.assertTrue(os.path.exists(dir_path))
        shutil.rmtree(dir_path)
        self.assertFalse(os.path.exists(dir_path))

    def test_copy_file(self):
        source_path = os.path.join(self.mounted_dir, 'source.txt')
        target_path = os.path.join(self.mounted_dir, 'target.txt')
        with open(source_path, 'w') as f:
            f.write('test data')
        shutil.copy(source_path, target_path)
        self.assertTrue(os.path.exists(target_path))
        with open(target_path, 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_copy_directory(self):
        source_dir = os.path.join(self.mounted_dir, 'source_dir')
        target_dir = os.path.join(self.mounted_dir, 'target_dir')
        os.makedirs(source_dir)
        with open(os.path.join(source_dir, 'file.txt'), 'w') as f:
            f.write('test data')
        shutil.copytree(source_dir, target_dir)
        self.assertTrue(os.path.exists(target_dir))
        self.assertTrue(os.path.exists(os.path.join(target_dir, 'file.txt')))
        with open(os.path.join(target_dir, 'file.txt'), 'r') as f:
            data = f.read()
        self.assertEqual(data, 'test data')

    def test_file_exists(self):
        file_path = os.path.join(self.mounted_dir, 'testfile.txt')
        self.assertFalse(os.path.exists(file_path))
        with open(file_path, 'w') as f:
            f.write('test data')
        self.assertTrue(os.path.exists(file_path))

    def test_directory_exists(self):
        dir_path = os.path.join(self.mounted_dir, 'testdir')
        self.assertFalse(os.path.exists(dir_path))
        os.makedirs(dir_path)
        self.assertTrue(os.path.exists(dir_path))

    def test_file_extension(self):
        file_path = os.path.join(self.mounted_dir, 'testfile.txt')
        self.assertEqual(os.path.splitext(file_path)[1], '.txt')

    def test_file_size(self):
        file_path = os.path.join(self.mounted_dir, 'testfile.txt')
        with open(file_path, 'w') as f:
            f.write('test data')
        self.assertEqual(os.path.getsize(file_path), 9)

    def test_directory_listing(self):
        dir_path = os.path.join(self.mounted_dir, 'testdir')
        os.makedirs(dir_path)
        with open(os.path.join(dir_path, 'file1.txt'), 'w') as f:
            f.write('test data 1')
        with open(os.path.join(dir_path, 'file2.txt'), 'w') as f:
            f.write('test data 2')
        listing = os.listdir(dir_path)
        self.assertEqual(len(listing), 2)
        self.assertIn('file1.txt', listing)
        self.assertIn('file2.txt', listing)

    def test_file_descriptor_leaks(self):
        if os.name == 'nt':
            self.skipTest('File descriptor count are not avaible on Windows')
        file_path = os.path.join(self.mounted_dir, 'fd_test.txt')
        initial_fds = psutil.Process().num_fds()
        
        for _ in range(100):
            with open(file_path, 'w') as f:
                f.write('test content')
            with open(file_path, 'r') as f:
                f.read()
        
        final_fds = psutil.Process().num_fds()
        self.assertLess(final_fds - initial_fds, 10)  # Allow for some fluctuation, but ensure no major leaks

    def test_concurrent_rename_operations(self):
        def rename_worker(old_name, new_name):
            old_path = os.path.join(self.mounted_dir, old_name)
            new_path = os.path.join(self.mounted_dir, new_name)
            with open(old_path, 'w') as f:
                f.write(f'content of {old_name}')
            time.sleep(0.1)
            os.rename(old_path, new_path)

        threads = []
        for i in range(10):
            t = threading.Thread(target=rename_worker, args=(f'old_file_{i}.txt', f'new_file_{i}.txt'))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for i in range(10):
            self.assertFalse(os.path.exists(os.path.join(self.mounted_dir, f'old_file_{i}.txt')))
            self.assertTrue(os.path.exists(os.path.join(self.mounted_dir, f'new_file_{i}.txt')))

    def test_read_write_at_file_boundaries(self):
        file_path = os.path.join(self.mounted_dir, 'boundary_test.txt')
        data: bytes = b'a' * 4096 + b'b' * 4096  # Two pages of data
        
        with open(file_path, 'wb') as f:
            f.write(data)
        
        with open(file_path, 'rb') as f:
            f.seek(4095)
            self.assertEqual(f.read(2), b'ab')
            
            f.seek(8191)
            self.assertEqual(len(f.read(2)), second=1)

            f.seek(10000)
            self.assertEqual(f.read(200), b'')

    def test_execute_permission_on_files(self):
        if os.name == 'nt':
            self.skipTest('Execute permissions are not applicable on Windows')
        
        file_path = os.path.join(self.mounted_dir, 'executable.sh')
        with open(file_path, 'w') as f:
            f.write('#!/bin/sh\necho "Hello, World!"')
        
        os.chmod(file_path, 0o755)
        stat_result = os.stat(file_path)
        self.assertTrue(stat_result.st_mode & stat.S_IXUSR)

        result = subprocess.run([file_path], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "Hello, World!")

    def test_file_content_integrity_after_multiple_writes(self):
        file_path = os.path.join(self.mounted_dir, 'integrity_test.txt')
        
        content = 'Initial content\n'

        with open(file_path, 'w') as f:
            f.write(content)

        for i in range(100):
            with open(file_path, 'a') as f:
                f.write(f'Append {i}\n')

        with open(file_path, 'r') as f:
            file_content = f.read()

        expected_content = content + ''.join([f'Append {i}\n' for i in range(100)])
        self.assertEqual(file_content, expected_content)

    def test_file_content_integrity_after_random_seeks_and_writes(self):
        file_path = os.path.join(self.mounted_dir, 'random_seek_test')
        content = 'x' * 10000
        with open(file_path, 'w') as f:
            f.write(content)
        
        nbr_y_written = 0
        for _ in range(1000):
            with open(file_path, 'r+') as f:
                pos = random.randint(0, 9999)
                f.seek(pos)
                if f.read(1) != 'y':  # read the character at the position
                    f.seek(pos)  # move the pointer back after reading
                    f.write('y')
                    nbr_y_written += 1
                
        
        with open(file_path, 'r') as f:
            modified_content = f.read()
        
        self.assertEqual(len(modified_content), 10000)
        self.assertEqual(modified_content.count('y'), nbr_y_written)

    def test_concurrent_reads_same_file(self):
        file_path = os.path.join(self.mounted_dir, 'concurrent_read.txt')
        content = 'x' * 1000000
        with open(file_path, 'w') as f:
            f.write(content)
        
        def read_file():
            with open(file_path, 'r') as f:
                return f.read()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: read_file(), range(10)))
        
        for result in results:
            self.assertEqual(result, content)

    def test_concurrent_writes_different_files(self):
        def write_file(file_name):
            file_path = os.path.join(self.mounted_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(f'Content of {file_name}')
        
        file_names = [f'concurrent_write_{i}.txt' for i in range(100)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(write_file, file_names)
        
        for file_name in file_names:
            file_path = os.path.join(self.mounted_dir, file_name)
            with open(file_path, 'r') as f:
                self.assertEqual(f.read(), f'Content of {file_name}')

    def test_large_directory_listing(self):
        dir_path = os.path.join(self.mounted_dir, 'large_dir')
        os.makedirs(dir_path)
        for i in range(10000):
            with open(os.path.join(dir_path, f'file_{i}.txt'), 'w') as f:
                f.write(f'Content of file {i}')
        
        start_time = time.time()
        files = os.listdir(dir_path)
        end_time = time.time()
        
        self.assertEqual(len(files), 10000)
        self.assertLess(end_time - start_time, 5)  # Ensure listing is reasonably fast

    def test_file_creation_time(self):
        file_path = os.path.join(self.mounted_dir, 'creation_time_test')
        before = time.time()
        with open(file_path, 'w') as f:
            f.write('test content')
        after = time.time()
        print("STTI" + str(os.stat(file_path)))
        creation_time = os.path.getctime(file_path)
        print("CT " + str(creation_time))
        self.assertGreaterEqual(creation_time, before)
        self.assertLessEqual(creation_time, after)

    def test_extended_attributes(self):
        if not hasattr(os, 'setxattr'):
            self.skipTest('Extended attributes are not supported on this platform')
        
        file_path = os.path.join(self.mounted_dir, 'xattr_test.txt')
        with open(file_path, 'w') as f:
            f.write('test content')
        
        os.setxattr(file_path, b'user.test_attr', b'test_value')
        value = os.getxattr(file_path, b'user.test_attr')
        self.assertEqual(value, b'test_value')

    def test_sparse_file_support(self):
        file_path = os.path.join(self.mounted_dir, 'sparse_test.txt')
        with open(file_path, 'wb') as f:
            f.seek(1000000)
            f.write(b'end')
        
        self.assertEqual(os.path.getsize(file_path), 1000003)
        with open(file_path, 'rb') as f:
            f.seek(0)
            start = f.read(10)
            f.seek(999990)
            end = f.read(13)
        
        self.assertEqual(start, b'\0' * 10)
        self.assertEqual(end, b'\0' * 10 + b'end')

    def test_file_truncate(self):
        file_path = os.path.join(self.mounted_dir, 'truncate_test.txt')
        with open(file_path, 'w') as f:
            f.write('0123456789')
        
        with open(file_path, 'r+') as f:
            f.truncate(5)
        
        with open(file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, '01234')

    def test_rename_to_existing_file(self):
        file1 = os.path.join(self.mounted_dir, 'file1.txt')
        file2 = os.path.join(self.mounted_dir, 'file2')
        
        with open(file1, 'w') as f:
            f.write('content1')
        with open(file2, 'w') as f:
            f.write('content2')

        with self.assertRaises(FileExistsError):        
            os.rename(file1, file2)
        
        self.assertTrue(os.path.exists(file1))
        with open(file2, 'r') as f:
            self.assertEqual(f.read(), 'content2')

    def test_rename_open_file_windows(self):
        if os.name != 'nt':
            self.skipTest('This test is specific to Windows')
        
        file_path = os.path.join(self.mounted_dir, 'rename_open_win.txt')
        new_path = os.path.join(self.mounted_dir, 'renamed_open_win.txt')
        
        with open(file_path, 'w') as f:
            f.write('initial content')
            with self.assertRaises(PermissionError):
                os.rename(file_path, new_path)

    def test_case_sensitivity(self):
        lower_path = os.path.join(self.mounted_dir, 'case_test.txt')
        upper_path = os.path.join(self.mounted_dir, 'CASE_TEST.TXT')
        
        with open(lower_path, 'w') as f:
            f.write('lower case')
        
        if os.name == 'nt':
            # Windows is case-insensitive by default
            with open(upper_path, 'r') as f:
                self.assertEqual(f.read(), 'lower case')
        else:
            # Unix-like systems are case-sensitive
            with open(upper_path, 'w') as f:
                f.write('UPPER CASE')
            with open(lower_path, 'r') as f:
                self.assertEqual(f.read(), 'lower case')
            with open(upper_path, 'r') as f:
                self.assertEqual(f.read(), 'UPPER CASE')

    def test_middle_file_names(self):
        long_name = 'a' * 200  # Maximum allowed in many filesystems
        file_path = os.path.join(self.mounted_dir, long_name)
        with open(file_path, 'w') as f:
            f.write('test content')
        self.assertTrue(os.path.exists(file_path))

    def test_dot_files(self):
        dot_file = os.path.join(self.mounted_dir, '.hidden_file')
        with open(dot_file, 'w') as f:
            f.write('hidden content')
        self.assertTrue(os.path.exists(dot_file))
        self.assertIn('.hidden_file', os.listdir(self.mounted_dir))

    def test_file_name_with_special_characters(self):
        special_chars = 'file with !@#$%^&()_+-=[]{};\',. 你好.txt'
        file_path = os.path.join(self.mounted_dir, special_chars)
        with open(file_path, 'w') as f:
            f.write('special content')
        self.assertTrue(os.path.exists(file_path))
        self.assertIn(special_chars, os.listdir(self.mounted_dir))

    def test_large_file_read_write(self):
        file_path = os.path.join(self.mounted_dir, 'large_file_test.bin')
        size = 1 * 1024 * 1024 * 1024  # 1 GB
        chunk_size = 1024 * 1024  # 1 MB
        
        # Write
        with open(file_path, 'wb') as f:
            for _ in range(size // chunk_size):
                f.write(os.urandom(chunk_size))
        
        # Read and verify
        with open(file_path, 'rb') as f:
            read_size = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                read_size += len(chunk)
        
        self.assertEqual(read_size, size)

    def test_directory_mtime_update(self):
        dir_path = os.path.join(self.mounted_dir, 'mtime_test_dir')
        os.mkdir(dir_path)
        dir_mtime = os.stat(dir_path).st_mtime
        
        time.sleep(1)  # Ensure enough time has passed for mtime to change
        file_path = os.path.join(dir_path, 'new_file')
        with open(file_path, 'w') as f:
            f.write('test content')
        
        new_dir_mtime = os.stat(dir_path).st_mtime
        self.assertGreater(new_dir_mtime, dir_mtime)

    def test_symlink_to_directory(self):
        if os.name == 'nt':
            self.skipTest('Symlinks to directories are not fully supported on Windows')
        
        dir_path = os.path.join(self.mounted_dir, 'symlink_target_dir')
        os.mkdir(dir_path)
        symlink_path = os.path.join(self.mounted_dir, 'dir_symlink')
        os.symlink(dir_path, symlink_path)
        
        self.assertTrue(os.path.islink(symlink_path))
        self.assertTrue(os.path.isdir(symlink_path))

    def test_recursive_directory_removal(self):
        root_dir = os.path.join(self.mounted_dir, 'recursive_test')
        os.makedirs(os.path.join(root_dir, 'subdir1', 'subdir2'))
        with open(os.path.join(root_dir, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(root_dir, 'subdir1', 'file2.txt'), 'w') as f:
            f.write('content2')
        
        shutil.rmtree(root_dir)
        self.assertFalse(os.path.exists(root_dir))

    def test_file_creation_in_readonly_directory(self):
        if os.name == 'nt':
            self.skipTest('Changing directory permissions is limited on Windows')
        
        dir_path = os.path.join(self.mounted_dir, 'readonly_dir')
        os.mkdir(dir_path)
        os.chmod(dir_path, 0o555)  # Read and execute permissions only
        
        file_path = os.path.join(dir_path, 'test_file.txt')
        with self.assertRaises(PermissionError):
            with open(file_path, 'w') as f:
                f.write('test content')

    def test_disk_space_reporting(self):
        total, used, free = shutil.disk_usage(self.mounted_dir)
        self.assertGreater(total, 0)
        self.assertGreater(free, 0)
        self.assertLessEqual(used, total)

    def test_end_to_end_document_editing_workflow(self):
        # Simulate a user creating, editing, and organizing documents
        
        # 1. Create a new document
        doc_path = os.path.join(self.mounted_dir, 'my_document.txt')
        with open(doc_path, 'w') as f:
            f.write('Initial content')
        
        # 2. Read the document
        with open(doc_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'Initial content')
        
        # 3. Edit the document
        with open(doc_path, 'a') as f:
            f.write('\nAdditional content')
        
        # 4. Create a new directory for organizing
        os.mkdir(os.path.join(self.mounted_dir, 'Documents'))
        
        # 5. Move the document to the new directory
        new_doc_path = os.path.join(self.mounted_dir, 'Documents', 'my_document.txt')
        os.rename(doc_path, new_doc_path)
        
        # 6. Verify the move
        self.assertFalse(os.path.exists(doc_path))
        self.assertTrue(os.path.exists(new_doc_path))
        
        # 7. Read the moved document
        with open(new_doc_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'Initial content\nAdditional content')
        
        # 8. Create a backup of the document
        backup_path = os.path.join(self.mounted_dir, 'Documents', 'my_document_backup.txt')
        shutil.copy2(new_doc_path, backup_path)
        
        # 9. Verify both files exist and have the same content
        self.assertTrue(os.path.exists(new_doc_path))
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        self.assertEqual(content, backup_content)
        
        # 10. Delete the original document
        os.remove(new_doc_path)
        self.assertFalse(os.path.exists(new_doc_path))
        self.assertTrue(os.path.exists(backup_path))

    def test_end_to_end_software_development_workflow(self):
        # Simulate a software development workflow
        
        # 1. Create a project directory
        project_dir = os.path.join(self.mounted_dir, 'my_project')
        os.mkdir(project_dir)
        
        # 2. Create a source file
        src_file = os.path.join(project_dir, 'main.py')
        with open(src_file, 'w') as f:
            f.write('print("Hello, World!")')
        
        # 3. Create a git ignore file (excluded)
        gitignore_file = os.path.join(project_dir, '.gitignore')
        with open(gitignore_file, 'w') as f:
            f.write('*.pyc\n__pycache__')
        
        # 4. Compile the source file (creating a .pyc file, which should be excluded)
        import py_compile
        py_compile.compile(src_file)
        
        # 5. Verify .pyc file is not visible in the mounted directory
        pyc_file = src_file + 'c'  # Python 3.2+ uses .pyc in __pycache__
        self.assertFalse(os.path.exists(pyc_file))
        
        # 6. Create a subdirectory for tests
        test_dir = os.path.join(project_dir, 'tests')
        os.mkdir(test_dir)
        
        # 7. Create a test file
        test_file = os.path.join(test_dir, 'test_main.py')
        with open(test_file, 'w') as f:
            f.write('assert True')
        
        # 8. List the project directory
        project_contents = os.listdir(project_dir)
        self.assertIn('main.py', project_contents)
        self.assertIn('.gitignore', project_contents)
        self.assertIn('tests', project_contents)
        self.assertNotIn('main.pyc', project_contents)
        
        # 9. Rename the test directory
        new_test_dir = os.path.join(project_dir, 'unit_tests')
        os.rename(test_dir, new_test_dir)
        
        # 10. Verify the rename
        self.assertFalse(os.path.exists(test_dir))
        self.assertTrue(os.path.exists(new_test_dir))
        self.assertTrue(os.path.exists(os.path.join(new_test_dir, 'test_main.py')))

    def test_end_to_end_file_syncing_scenario(self):
        # Simulate a file syncing scenario with excluded and non-excluded files
        
        # 1. Create a sync directory
        sync_dir = os.path.join(self.mounted_dir, 'sync_folder')
        os.mkdir(sync_dir)
        
        # 2. Create some files in the sync directory
        with open(os.path.join(sync_dir, 'document.txt'), 'w') as f:
            f.write('Important document')
        with open(os.path.join(sync_dir, 'script.py'), 'w') as f:
            f.write('print("Hello")')
        with open(os.path.join(sync_dir, 'large_file.bin'), 'wb') as f:
            f.write(os.urandom(1024 * 1024))  # 1 MB random data
        
        # 3. Create some excluded files
        with open(os.path.join(sync_dir, '.DS_Store'), 'w') as f:
            f.write('Fake DS_Store file')
        with open(os.path.join(sync_dir, 'temp.txt'), 'w') as f:
            f.write('Temporary file')
        
        # 4. List the directory and check for correct visibility
        sync_contents = os.listdir(sync_dir)
        self.assertIn('document.txt', sync_contents)
        self.assertIn('script.py', sync_contents)
        self.assertIn('large_file.bin', sync_contents)
        self.assertIn('.DS_Store', sync_contents)
        self.assertIn('temp.txt', sync_contents)
        
        # 5. Simulate sync by copying to a new location
        sync_target = os.path.join(self.mounted_dir, 'synced_folder')
        shutil.copytree(sync_dir, sync_target)
        
        # 6. Verify synced contents
        synced_contents = os.listdir(sync_target)
        self.assertIn('document.txt', synced_contents)
        self.assertIn('script.py', synced_contents)
        self.assertIn('large_file.bin', synced_contents)
        self.assertIn('.DS_Store', synced_contents)
        self.assertIn('temp.txt', synced_contents)
        self.assertNotIn('tempqsdd', synced_contents)

        # 7. Modify an excluded file
        with open(os.path.join(sync_target, '.DS_Store'), 'a') as f:
            f.write('\nModified content')
        
        # 8. Simulate incremental sync
        shutil.copytree(sync_dir, sync_target, dirs_exist_ok=True)
        
        # 9. Verify the excluded file was not synced
        with open(os.path.join(sync_target, '.DS_Store'), 'r') as f:
            content = f.read()
        self.assertNotIn('Modified content', content)
        
        # 10. Clean up by removing the sync directories
        shutil.rmtree(sync_dir)
        shutil.rmtree(sync_target)
        self.assertFalse(os.path.exists(sync_dir))
        self.assertFalse(os.path.exists(sync_target))


# Don't forget to import necessary modules at the beginning of your file:
# import random, concurrent.futures, fcntl, resource
    def tearDown(self):
        self.p.kill()
        time.sleep(2)
        #remove the temporary directories even if they are not empty
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
  
        shutil.rmtree(self.mounted_dir, ignore_errors=True)

if __name__ == '__main__':
    unittest.main()