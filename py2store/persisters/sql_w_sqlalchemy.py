"""Forwards to sqldol

"""
from contextlib import suppress

with suppress(ModuleNotFoundError):
    from sqldol import *
