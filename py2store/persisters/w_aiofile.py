import asyncio
import os

from py2store.base import KvReader, KvPersister
from py2store.key_mappers.paths import mk_relative_path_store
from py2store.filesys import (
    FileCollection,
    validate_key_and_raise_key_error_on_exception,
)
from py2store.util import ModuleNotFoundWarning

with ModuleNotFoundWarning(f"Missing third-party package: aiofile"):
    from aiofile import AIOFile

_dflt_not_valid_error_msg = "Key not valid (usually because does not exist or access not permitted): {}"
_dflt_not_found_error_msg = "Key not found: {}"


class AioFileBytesReader(FileCollection, KvReader):
    _read_open_kwargs = dict(mode="rb")

    __getitem__ = None

    # @validate_key_and_raise_key_error_on_exception  # TODO: does this also wrap the async?
    async def aget(self, k):  # noqa
        """
        Gets the bytes contents of the file k.
        >>> import os
        >>> filepath = __file__
        >>> dirpath = os.path.dirname(__file__)  # path of the directory where I (the module file) am
        >>> s = AioFileBytesReader(dirpath, max_levels=0)
        >>>
        >>> ####### Get the first 9 characters (as bytes) of this module #####################
        >>> t = await s.aget(filepath)
        >>> t[:14]
        b'import asyncio'
        >>>
        >>> ####### Test key validation #####################
        >>> await s.aget('not_a_valid_key')  # this key is not valid since not under the dirpath folder
        Traceback (most recent call last):
            ...
        filesys.KeyValidationError: 'Key not valid (usually because does not exist or access not permitted): not_a_valid_key'
        >>>
        >>> ####### Test further exceptions (that should be wrapped in KeyError) #####################
        >>> # this key is valid, since under dirpath, but the file itself doesn't exist (hopefully for this test)
        >>> non_existing_file = os.path.join(dirpath, 'non_existing_file')
        >>> try:
        ...     await s.aget(non_existing_file)
        ... except KeyError:
        ...     print("KeyError (not FileNotFoundError) was raised.")
        KeyError (not FileNotFoundError) was raised.
        """

        async with AIOFile(k, **self._read_open_kwargs) as fp:
            v = (
                await fp.read()
            )  # Question: Is it faster if we just did `return await fp.read(), instead of assign?
        return v
        # with open(k, **self._read_open_kwargs) as fp:
        #     return fp.read()


class AioFileBytesPersister(AioFileBytesReader, KvPersister):
    _write_open_kwargs = dict(mode="wb")

    @validate_key_and_raise_key_error_on_exception
    async def asetitem(self, k, v):
        """

        >>> from py2store.persisters.w_aiofile import AioFileBytesPersister
        >>> from py2store.filesys import mk_tmp_py2store_dir
        >>> import os
        >>>
        >>> rootdir = mk_tmp_py2store_dir('test')
        >>> rpath = lambda *p: os.path.join(rootdir, *p)
        >>> s = AioFileBytesPersister(rootdir)
        >>> k = rpath('foo')
        >>> if k in s:
        ...     del s[k]  # delete key if present
        ...
        >>> n = len(s)  # number of items in store
        >>> await s.asetitem(k, b'bar')
        >>> assert len(s) == n + 1  # there's one more item in store
        >>> assert k in s
        >>> assert (await s[k]) == b'bar'
        """
        async with AIOFile(k, **self._write_open_kwargs) as fp:
            await fp.write(v)
            await fp.fsync()

    def __setitem__(self, k, v):
        return asyncio.create_task(self.asetitem(k, v))

    @validate_key_and_raise_key_error_on_exception
    def __delitem__(self, k):
        os.remove(k)

    # @validate_key_and_raise_key_error_on_exception
    # def __setitem__(self, k, v):
    #     with open(k, **self._write_open_kwargs) as fp:
    #         return fp.write(v)


RelPathAioFileBytesReader = mk_relative_path_store(
    AioFileBytesReader,
    prefix_attr="rootdir",
    __name__="RelPathAioFileBytesReader",
)


class AioFileStringReader(AioFileBytesReader):
    _read_open_kwargs = dict(AioFileBytesReader._read_open_kwargs, mode="rt")


class AioFileStringPersister(AioFileBytesPersister):
    _write_open_kwargs = dict(
        AioFileBytesPersister._write_open_kwargs, mode="wt"
    )


RelPathFileStringReader = mk_relative_path_store(
    AioFileStringReader,
    prefix_attr="rootdir",
    __name__="RelPathFileStringReader",
)

########## The simple store we made during meeting ################################################################

# import os
# from collections.abc import MutableMapping
# from aiofile import AIOFile, Reader, Writer
#
#
# class SimpleFilePersister(MutableMapping):
#     """Read/write (text or binary) data to files under a given rootdir.
#     Keys must be absolute file paths.
#     Paths that don't start with rootdir will be raise a KeyValidationError
#     """
#
#     def __init__(self, rootdir, mode='t'):
#         if not rootdir.endswith(os.path.sep):
#             rootdir = rootdir + os.path.sep
#         self.rootdir = rootdir
#         assert mode in {'t', 'b', ''}, f"mode ({mode}) not valid: Must be 't' or 'b'"
#         self.mode = mode
#
#     # TODO: __getitem__ can't be async?!?
#     # async def __getitem__(self, k):
#     #     async with AIOFile(k, 'r' + self.mode) as fp:
#     #         v = await fp.read()
#     #     return v
#
#     def __getitem__(self, k):
#         async with AIOFile(k, 'r' + self.mode) as fp:
#             v = await fp.read()  # Question: Is it faster if we just did `return await fp.read()
#         return v
#
#     async def asetitem(self, k, v):
#         async with AIOFile(k, 'w' + self.mode) as fp:
#             await fp.write(v)
#             await fp.fsync()
#
#     def __setitem__(self, k, v):
#         #         loop = asyncio.new_event_loop()
#         #         asyncio.set_event_loop(loop)
#         return asyncio.create_task(self.asetitem(k, v))
#
#     def __delitem__(self, k):
#         os.remove(k)
#
#     def __contains__(self, k):
#         """ Implementation of "k in self" check.
#         Note: MutableMapping gives you this for free, using a try/except on __getitem__,
#         but the following uses faster os functionality."""
#         return os.path.isfile(k)
#
#     def __iter__(self):
#         yield from filter(os.path.isfile,
#                           map(lambda x: os.path.join(self.rootdir, x),
#                               os.listdir(self.rootdir)))
#
#     def __len__(self):
#         """Note: There's system-specific faster ways to do this."""
#         count = 0
#         for _ in self.__iter__():
#             count += 1
#         return count
#
#     def clear(self):
#         """MutableMapping creates a 'delete all' functionality by default. Better disable it!"""
#         raise NotImplementedError("If you really want to do that, loop on all keys and remove them one by one.")
