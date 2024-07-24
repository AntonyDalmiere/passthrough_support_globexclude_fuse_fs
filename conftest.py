# import platform
# from typing import List

# def pytest_configure(config) -> None:
#     required_workers_count = 4 if platform.system() == 'Windows' else 12
#     config.option.dist = 'loadgroup'
#     config.option.numprocesses= required_workers_count
#     config.option.cov_source = ['passthrough_support_excludeglob_fs']
#     print(config.option)