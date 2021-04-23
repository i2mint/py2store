"""Forwards to pydrivedol
"""
from contextlib import suppress

with suppress(ModuleNotFoundError):
    from pydrivedol import *
