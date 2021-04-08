import inspect
import os
from functools import wraps
from io import BytesIO
from zipfile import (
    ZipFile,
    ZIP_STORED,
    ZIP_DEFLATED,
    ZIP_BZIP2,
    ZIP_LZMA,
)
from py2store.base import KvReader, KvPersister
from py2store.filesys import FileCollection
from py2store.util import lazyprop, fullpath


class COMPRESSION:
    ZIP_STORED = ZIP_STORED  # The numeric constant for an uncompressed archive member.
    ZIP_DEFLATED = ZIP_DEFLATED  # The numeric constant for the usual ZIP compression method. This requires zlib module.
    ZIP_BZIP2 = ZIP_BZIP2  # The numeric constant for the BZIP2 compression method. This requires the bz2 module.
    ZIP_LZMA = ZIP_LZMA  # The numeric constant for the LZMA compression method. This requires the lzma module.


def func_conjunction(func1, func2):
    """Returns a function that is equivalent to lambda x: func1(x) and func2(x)"""
    # Should assert that the input paramters of func1 and func2 are the same
    assert (
            inspect.signature(func1).parameters
            == inspect.signature(func2).parameters
    )

    @wraps(func2)
    def func(*args, **kwargs):
        return func1(*args, **kwargs) and func2(*args, **kwargs)

    return func


def take_everything(fileinfo):
    return True


class ZipReader(KvReader):
    """A KvReader to read the contents of a zip file.
    Provides a KV perspective of https://docs.python.org/3/library/zipfile.html

    ``ZipReader`` has two value categories: Directories and Files.
    Both categories are distinguishable by the keys, through the "ends with slash" convention.

    When a file, the value return is bytes, as usual.

    When a directory, the value returned is a ``ZipReader`` itself, with all params the same, except for the ``prefix``
     which serves `to specify the subfolder (that is, ``prefix`` acts as a filter).

    Note: If you get data zipped by a mac, you might get some junk along with it.
    Namely `__MACOSX` folders `.DS_Store` files. I won't rant about it, since others have.
    But you might find it useful to remove them from view. One choice is to use `py2store.trans.filt_iter`
    to get a filtered view of the zips contents. In most cases, this should do the job:
    ```
    # applied to store instance or class:
    store = filt_iter(filt=lambda x: not x.startswith('__MACOSX') and '.DS_Store' not in x)(store)
    ```

    Another option is just to remove these from the zip file once and for all. In unix-like systems:
    ```
    zip -d filename.zip __MACOSX/\*
    zip -d filename.zip \*/.DS_Store
    ```

    Examples:
        # >>> s = ZipReader('/path/to/some_zip_file.zip')
        # >>> len(s)
        # 53432
        # >>> list(s)[:3]  # the first 3 elements (well... their keys)
        # ['odir/', 'odir/app/', 'odir/app/data/']
        # >>> list(s)[-3:]  # the last 3 elements (well... their keys)
        # ['odir/app/data/audio/d/1574287049078391/m/Ctor.json',
        #  'odir/app/data/audio/d/1574287049078391/m/intensity.json',
        #  'odir/app/data/run/status.json']
        # >>> # getting a file (note that by default, you get bytes, so need to decode)
        # >>> s['odir/app/data/run/status.json'].decode()
        # b'{"test_phase_number": 9, "test_phase": "TestActions.IGNORE_TEST", "session_id": 0}'
        # >>> # when you ask for the contents for a key that's a directory,
        # >>> # you get a ZipReader filtered for that prefix:
        # >>> s['odir/app/data/audio/']
        # ZipReader('/path/to/some_zip_file.zip', 'odir/app/data/audio/', {}, <function take_everything at 0x1538999e0>)
        # >>> # Often, you only want files (not directories)
        # >>> # You can filter directories out using the file_info_filt argument
        # >>> s = ZipReader('/path/to/some_zip_file.zip', file_info_filt=ZipReader.FILES_ONLY)
        # >>> len(s)  # compare to the 53432 above, that contained dirs too
        # 53280
        # >>> list(s)[:3]  # first 3 keys are all files now
        # ['odir/app/data/plc/d/1574304926795633/d/1574305026895702',
        #  'odir/app/data/plc/d/1574304926795633/d/1574305276853053',
        #  'odir/app/data/plc/d/1574304926795633/d/1574305159343326']
        # >>>
        # >>> # ZipReader.FILES_ONLY and ZipReader.DIRS_ONLY are just convenience filt functions
        # >>> # Really, you can provide any custom one yourself.
        # >>> # This filter function should take a ZipInfo object, and return True or False.
        # >>> # (https://docs.python.org/3/library/zipfile.html#zipfile.ZipInfo)
        # >>>
        # >>> import re
        # >>> p = re.compile('audio.*\.json$')
        # >>> my_filt_func = lambda fileinfo: bool(p.search(fileinfo.filename))
        # >>> s = ZipReader('/Users/twhalen/Downloads/2019_11_21.zip', file_info_filt=my_filt_func)
        # >>> len(s)
        # 48
        # >>> list(s)[:3]
        # ['odir/app/data/audio/d/1574333557263758/m/Ctor.json',
        #  'odir/app/data/audio/d/1574333557263758/m/intensity.json',
        #  'odir/app/data/audio/d/1574288084739961/m/Ctor.json']
    """

    def __init__(
            self, zip_file, prefix="", open_kws=None, file_info_filt=None
    ):
        """

        Args:
            zip_file: A path to make ZipFile(zip_file)
            prefix: A prefix to filter by.
            open_kws:  To be used when doing a ZipFile(...).open
            file_info_filt: Filter for the FileInfo objects (see https://docs.python.org/3/library/zipfile.html)
                of the paths listed in the zip file
        """
        self.open_kws = open_kws or {}
        self.file_info_filt = file_info_filt or ZipReader.EVERYTHING
        self.prefix = prefix
        if not isinstance(zip_file, ZipFile):
            if isinstance(zip_file, str):
                zip_file = fullpath(zip_file)
            if isinstance(zip_file, dict):
                zip_file = ZipFile(**zip_file)
            elif isinstance(zip_file, (tuple, list)):
                zip_file = ZipFile(*zip_file)
            elif isinstance(zip_file, bytes):
                zip_file = ZipFile(BytesIO(zip_file))
            else:
                zip_file = ZipFile(zip_file)
        self.zip_file = zip_file

    @classmethod
    def for_files_only(
            cls, zip_file, prefix="", open_kws=None, file_info_filt=None
    ):
        if file_info_filt is None:
            file_info_filt = ZipReader.FILES_ONLY
        else:
            _file_info_filt = file_info_filt

            def file_info_filt(x):
                return ZipReader.FILES_ONLY(x) and _file_info_filt(x)

        return cls(zip_file, prefix, open_kws, file_info_filt)

    @lazyprop
    def info_for_key(self):
        return {
            x.filename: x
            for x in self.zip_file.infolist()
            if x.filename.startswith(self.prefix) and self.file_info_filt(x)
        }

    def __iter__(self):
        # using zip_file.infolist(), we could also filter for info (like directory/file)
        yield from self.info_for_key.keys()

    def __getitem__(self, k):
        if not self.info_for_key[k].is_dir():
            with self.zip_file.open(k, **self.open_kws) as fp:
                return fp.read()
        else:  # is a directory
            return self.__class__(
                self.zip_file, k, self.open_kws, self.file_info_filt
            )

    def __len__(self):
        return len(self.info_for_key)

    @staticmethod
    def FILES_ONLY(fileinfo):
        return not fileinfo.is_dir()

    @staticmethod
    def DIRS_ONLY(fileinfo):
        return fileinfo.is_dir()

    @staticmethod
    def EVERYTHING(fileinfo):
        return True

    def __repr__(self):
        args_str = ", ".join(
            (
                f"'{self.zip_file.filename}'",
                f"'{self.prefix}'",
                f"{self.open_kws}",
                f"{self.file_info_filt}",
            )
        )
        return f"{self.__class__.__name__}({args_str})"


class ZipFilesReader(FileCollection, KvReader):
    """A local file reader whose keys are the zip filepaths of the rootdir and values are corresponding ZipReaders.
    """

    def __init__(
            self,
            rootdir,
            subpath=".+\.zip",
            pattern_for_field=None,
            max_levels=0,
            zip_reader=ZipReader,
            **zip_reader_kwargs
    ):
        super().__init__(rootdir, subpath, pattern_for_field, max_levels)
        self.zip_reader = zip_reader
        self.zip_reader_kwargs = zip_reader_kwargs
        if self.zip_reader is ZipReader:
            self.zip_reader_kwargs = dict(
                dict(prefix="", open_kws=None, file_info_filt=ZipReader.FILES_ONLY),
                **self.zip_reader_kwargs
            )

    def __getitem__(self, k):
        try:
            return self.zip_reader(k, **self.zip_reader_kwargs)
        except FileNotFoundError as e:
            raise KeyError(f"FileNotFoundError: {e}")


class ZipFilesReaderAndBytesWriter(ZipFilesReader):
    """Like ZipFilesReader, but the ability to write bytes (assumed to be valid bytes of the zip format) to a key
    """

    def __setitem__(self, k, v):
        with open(k, 'wb') as fp:
            fp.write(v)


ZipFileReader = ZipFilesReader  # back-compatibility alias


# TODO: Add easy connection to ExplicitKeymapReader and other path trans and cache useful for the folder of zips context
class FlatZipFilesReader(ZipFilesReader):
    """Read the union of the contents of multiple zip files.
    A local file reader whose keys are the zip filepaths of the rootdir and values are corresponding ZipReaders.

    """

    @lazyprop
    def _zip_readers(self):
        rootdir_len = len(self.rootdir)
        return {
            path[rootdir_len:]: super(FlatZipFilesReader, self).__getitem__(
                path
            )
            for path in super().__iter__()
        }

    def __iter__(self):
        for (
                zip_relpath,
                zip_reader,
        ) in self._zip_readers.items():  # go through the zip paths
            for (
                    path_in_zip
            ) in (
                    zip_reader
            ):  # go through the keys of the ZipReader (the zipped filepaths)
                yield (zip_relpath, path_in_zip)

    def __getitem__(self, k):
        (
            zip_relpath,
            path_in_zip,
        ) = k  # k is a pair of the path to the zip file and the path of a file within it
        return self._zip_readers[zip_relpath][path_in_zip]


def mk_flatzips_store(dir_of_zips, zip_pair_path_preproc=sorted,
                      mk_store=FlatZipFilesReader, **extra_mk_store_kwargs):
    """A store so that you can work with a folder that has a bunch of zip files,
    as if they've all been extracted in the same folder.
    Note that `zip_pair_path_preproc` can be used to control how to resolve key conflicts
    (i.e. when you get two different zip files that have a same path in their contents).
    The last path encountered by `zip_pair_path_preproc(zip_path_pairs)` is the one that will be used, so
    one should make `zip_pair_path_preproc` act accordingly.
    """
    from py2store.utils.explicit import ExplicitKeymapReader

    z = mk_store(dir_of_zips, **extra_mk_store_kwargs)
    path_to_pair = {pair[1]: pair for pair in zip_pair_path_preproc(z)}
    return ExplicitKeymapReader(z, id_of_key=path_to_pair)


class FilesOfZip(ZipReader):
    def __init__(self, zip_file, prefix="", open_kws=None):
        super().__init__(
            zip_file,
            prefix=prefix,
            open_kws=open_kws,
            file_info_filt=ZipReader.FILES_ONLY,
        )


# TODO: This file object item is more fundemental than file contents. Should it be at the base?
class FileStreamsOfZip(FilesOfZip):
    """Like FilesOfZip, but object returns are file streams instead.
    So you use it like this:

    ```
    z = FileStreamsOfZip(rootdir)
    with z[relpath] as fp:
        ...  # do stuff with fp, like fp.readlines() or such...
    ```
    """

    def __getitem__(self, k):
        return self.zip_file.open(k, **self.open_kws)


from py2store.paths import mk_relative_path_store
from py2store.util import partialclass

ZipFileStreamsReader = mk_relative_path_store(
    partialclass(ZipFilesReader, zip_reader=FileStreamsOfZip),
    prefix_attr='rootdir'
)
ZipFileStreamsReader.__name__ = 'ZipFileStreamsReader'
ZipFileStreamsReader.__qualname__ = 'ZipFileStreamsReader'
ZipFileStreamsReader.__doc__ = """Like ZipFilesReader, but objects returned are file streams instead."""

from py2store.errors import OverWritesNotAllowedError


class OverwriteNotAllowed(FileExistsError, OverWritesNotAllowedError):
    ...


class EmptyZipError(KeyError, FileNotFoundError):
    ...


class _EmptyZipReader(KvReader):
    def __init__(self, zip_filepath):
        self.zip_filepath = zip_filepath

    def __iter__(self):
        yield from ()

    def infolist(self):
        return []

    def __getitem__(self, k):
        raise EmptyZipError(
            "The store is empty: ZipStore(zip_filepath={self.zip_filepath})"
        )

    def open(self, *args, **kwargs):
        raise EmptyZipError(
            f"The zip file doesn't exist yet! Nothing was written in it: {self.zip_filepath}"
        )
        #
        # class OpenedNotExistingFile:
        #     zip_filepath = self.zip_filepath
        #
        #     def read(self):
        #         raise EmptyZipError(
        #             f"The zip file doesn't exist yet! Nothing was written in it: {self.zip_filepath}")
        #
        #     def __enter__(self, ):
        #         return self
        #
        #     def __exit__(self, *exc):
        #         return False
        #
        # return OpenedNotExistingFile()


from zipfile import BadZipFile

# TODO: Do all systems have this? If not, need to choose dflt carefully (choose dynamically?)
DFLT_COMPRESSION = COMPRESSION.ZIP_DEFLATED


# TODO: Revise ZipReader and ZipFilesReader architecture and make ZipStore be a subclass of Reader if poss
# TODO: What if I just want to zip a (single) file. What does py2store offer for that?
# TODO: How about set_obj (in misc.py)? Make it recognize the .zip extension and subextension (e.g. .txt.zip) serialize
class ZipStore(KvPersister):
    """Zip read and writing.
    When you want to read zips, there's the `FilesOfZip`, `ZipReader`, or `ZipFilesReader` we know and love.

    Sometimes though, you want to write to zips too. For this, we have `ZipStore`.

    Since ZipStore can write to a zip, it's read functionality is not going to assume static data,
    and cache things, as your favorite zip readers did.
    This, and the acrobatics need to disguise the weird zipfile into something more... key-value natural,
    makes for a not so efficient store, out of the box.

    I advise using one of the zip readers if all you need to do is read, or subclassing or
     wrapping ZipStore with caching layers if it is appropriate to you.

    """

    _zipfile_init_kw = dict(
        compression=DFLT_COMPRESSION,
        allowZip64=True,
        compresslevel=None,
        strict_timestamps=True,
    )
    _open_kw = dict(pwd=None, force_zip64=False)
    _writestr_kw = dict(compress_type=None, compresslevel=None)
    zip_writer = None

    # @wraps(ZipReader.__init__)
    def __init__(
            self,
            zip_filepath,
            compression=DFLT_COMPRESSION,
            allow_overwrites=True,
            pwd=None,
    ):
        self.zip_filepath = fullpath(zip_filepath)
        self.zip_filepath = zip_filepath
        self.zip_writer_opened = False
        self.allow_overwrites = allow_overwrites
        self._zipfile_init_kw = dict(
            self._zipfile_init_kw, compression=compression
        )
        self._open_kw = dict(self._open_kw, pwd=pwd)

    @staticmethod
    def files_only_filt(fileinfo):
        return not fileinfo.is_dir()

    @property
    def zip_reader(self):
        if os.path.isfile(self.zip_filepath):
            return ZipFile(
                self.zip_filepath, mode="r", **self._zipfile_init_kw
            )
        else:
            return _EmptyZipReader(self.zip_filepath)

    def __iter__(self):
        # using zip_file.infolist(), we could also filter for info (like directory/file)
        yield from (
            fi.filename
            for fi in self.zip_reader.infolist()
            if self.files_only_filt(fi)
        )

    def __getitem__(self, k):
        with self.zip_reader.open(k, **dict(self._open_kw, mode="r")) as fp:
            return fp.read()

    def __repr__(self):
        args_str = ", ".join(
            (
                f"'{self.zip_filepath}'",
                f"'allow_overwrites={self.allow_overwrites}'",
            )
        )
        return f"{self.__class__.__name__}({args_str})"

    def __contains__(self, k):
        try:
            with self.zip_reader.open(
                    k, **dict(self._open_kw, mode="r")
            ) as fp:
                pass
            return True
        except (
                KeyError,
                BadZipFile,
        ):  # BadZipFile is to catch when zip file exists, but is empty.
            return False

    # # TODO: Find better way to avoid duplicate keys!
    # # TODO: What's the right Error to raise
    # def _assert_non_existing_key(self, k):
    #     # if self.zip_writer is not None:
    #     if not self.zip_writer_opened:
    #         try:
    #             self.zip_reader.open(k)
    #             raise OverwriteNotAllowed(f"You're not allowed to overwrite an existing key: {k}")
    #         except KeyError as e:
    #             if isinstance(e, EmptyZipError) or e.args[-1].endswith('archive'):
    #                 pass  #
    #             else:
    #                 raise OverwriteNotAllowed(f"You're not allowed to overwrite an existing key: {k}")

    # TODO: Repeated with zip_writer logic. Consider DRY possibilities.
    def __setitem__(self, k, v):
        if k in self:
            if self.allow_overwrites and not self.zip_writer_opened:
                del self[k]  # remove key so it can be overwritten
            else:
                if self.zip_writer_opened:
                    raise OverwriteNotAllowed(
                        f"When using the context mode, you're not allowed to overwrite an existing key: {k}"
                    )
                else:
                    raise OverwriteNotAllowed(
                        f"You're not allowed to overwrite an existing key: {k}"
                    )

        if self.zip_writer_opened:
            with self.zip_writer.open(
                    k, **dict(self._open_kw, mode="w")
            ) as fp:
                return fp.write(v)
        else:
            with ZipFile(
                    self.zip_filepath, mode="a", **self._zipfile_init_kw
            ) as zip_writer:
                with zip_writer.open(k, **dict(self._open_kw, mode="w")) as fp:
                    return fp.write(v)

    def __delitem__(self, k):
        try:
            os.system(f"zip -d {self.zip_filepath} {k}")
        except Exception as e:
            raise KeyError(f"{e.__class__}: {e.args}")
        # raise NotImplementedError("zipfile, the backend of ZipStore, doesn't support deletion, so neither will we.")

    def open(self):
        self.zip_writer = ZipFile(
            self.zip_filepath, mode="a", **self._zipfile_init_kw
        )
        self.zip_writer_opened = True
        return self

    def close(self):
        if self.zip_writer is not None:
            self.zip_writer.close()
        self.zip_writer_opened = False

    __enter__ = open

    def __exit__(self, *exc):
        self.close()
        return False

# TODO: The way prefix and file_info_filt is handled is not efficient
# TODO: prefix is silly: less general than filename_filt would be, and not even producing relative paths
# (especially when getitem returns subdirs)


# trans alternative:
# from py2store.trans import mk_kv_reader_from_kv_collection, wrap_kvs
#
# ZipFileReader = wrap_kvs(mk_kv_reader_from_kv_collection(FileCollection, name='_ZipFileReader'),
#                          name='ZipFileReader',
#                          obj_of_data=ZipReader)

#
# if __name__ == '__main__':
#     from py2store.test.simple import test_local_file_ops
#
#     test_local_file_ops()
