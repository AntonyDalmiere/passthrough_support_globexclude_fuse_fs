from setuptools import setup, find_packages
from setuptools.command.install import install



with open('requirements.txt') as f:
    requirements = f.read().splitlines()

#Show a warning if winfsp is not installed if the user is on windows
class CustomInstall(install):
     def run(self):
        import platform
        if platform.system() == 'Windows':
            #type hint to retype all winreg functions
            import winreg as reg #type: str
            
            def Reg32GetValue(rootkey, keyname, valname):
                key, val = None, None
                try:
                    key = reg.OpenKey(rootkey, keyname, 0, reg.KEY_READ | reg.KEY_WOW64_32KEY)
                    val = str(reg.QueryValueEx(key, valname)[0])
                except OSError:
                    pass
                finally:
                    if key is not None:
                        reg.CloseKey(key)
                return val

            _libfuse_path = Reg32GetValue(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp", r"InstallDir")
            if not _libfuse_path:
                   print("WinFsp is not installed. Please install it from https://winfsp.dev/")
                                   
        install.run(self)

setup(
    name='passthrough_support_excludeglob_fs',
    version='1.14',
    packages=find_packages(),
    description='A user-space filesystem that allows to exclude files from being shown in the filesystem using glob patterns',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Antony Dalmiere',
    author_email='zbkk9jrxo@mozmail.com',
    url='https://github.com/AntonyDalmiere/passthrough_support_globexclude_fuse_fs',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Topic :: System :: Filesystems'
    ],
    keywords='fuse, filesystem, passthrough, excludeglob',
    install_requires=requirements,
    cmdclass={'install':CustomInstall},
    entry_points={
        'console_scripts': [
            'passthrough_support_excludeglob_fs=passthrough_support_excludeglob_fs:cli',
        ],
    },
    license='CC BY-NC-NDA 4.0',
)