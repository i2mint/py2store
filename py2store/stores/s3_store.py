"""Forwards to s3dol.s3_store

"""
from contextlib import suppress

with suppress(ModuleNotFoundError):
    from s3dol.s3_store import *
