import os
import shutil
import tempfile
import threading
import unittest
from main import start_passthrough_fs
import multiprocessing
import time

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
    
    def tearDown(self):
        self.p.kill()
        time.sleep(2)
        #remove the temporary directories even if they are not empty
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
  
        shutil.rmtree(self.mounted_dir, ignore_errors=True)

if __name__ == '__main__':
    unittest.main()