"""Forwards to redisdol
"""

from contextlib import suppress

with suppress(ModuleNotFoundError):
    from redisdol import *
