"""Forwards to s3dol.new_s3

"""
from contextlib import suppress

with suppress(ModuleNotFoundError):
    from s3dol.new_s3 import *
