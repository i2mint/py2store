"""Forwards to dropboxdol
"""
from contextlib import suppress

with suppress(ModuleNotFoundError):
    from dropboxdol import *
