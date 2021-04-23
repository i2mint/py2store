"""Forwards to s3dol.s3_w_boto3

"""
from contextlib import suppress

with suppress(ModuleNotFoundError):
    from s3dol.s3_w_boto3 import *
