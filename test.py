import os
import shutil
import tempfile
import unittest
from main import start_passthrough_fs
import multiprocessing
import time

def determine_mountdir_based_on_os():
    if os.name == 'nt':
        return 'T:'
    else:
        return tempfile.mkdtemp()

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
        self.p = multiprocessing.Process(target=start_passthrough_fs, args=(self.mounted_dir, self.temp_dir, ['*.txt'], self.cache_dir))
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

    def tearDown(self):
        self.p.kill()
        time.sleep(2)
        #remove the temporary directories even if they are not empty
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        shutil.rmtree(self.mounted_dir, ignore_errors=True)
if __name__ == '__main__':
    unittest.main()