"""Forwards to aiofiledol

"""

from contextlib import suppress

with suppress(ModuleNotFoundError):
    from aiofiledol import *
