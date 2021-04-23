"""
a data object layer for github
"""
from warnings import warn

warn('Moved to independent package: pip install hubcap')

from contextlib import suppress

with suppress(ModuleNotFoundError):
    from hubcap import *
