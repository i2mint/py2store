"""
test files
"""
import sys
import os

try:
    from importlib.resources import files  # ... and any other things you want to get
except (ModuleNotFoundError, ImportError):
    from importlib_resources import files  # pip install importlib_resources

module_path = files(sys.modules[__name__])
ppath = module_path.joinpath

data_dirpath = str(module_path / 'data')
djoin = lambda *paths: os.path.join(data_dirpath, *paths)
minifs_dirpath = str(module_path / 'data' / 'minifs')
minifs_join = lambda *paths: os.path.join(minifs_dirpath, *paths)
