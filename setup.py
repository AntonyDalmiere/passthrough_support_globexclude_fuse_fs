from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='passthrough_support_excludeglob_fuse_py',
    version='0.1',
    packages=find_packages(),
    description='A short description of your package',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Antony Dalmiere',
    author_email='zbkk9jrxo@mozmail.com',
    url='https://github.com/AntonyDalmiere/passthrough_support_globexclude_fuse_fs',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='fuse, filesystem, passthrough, excludeglob',
    install_requires=requirements,
)