import inspect
from functools import wraps
from zipfile import ZipFile

from py2store import KvReader
from py2store.filesys import FileCollection
from py2store.util import lazyprop


def func_conjunction(func1, func2):
    """Returns a function that is equivalent to lambda x: func1(x) and func2(x)"""
    # Should assert that the input paramters of func1 and func2 are the same
    assert inspect.signature(func1).parameters == inspect.signature(func2).parameters

    @wraps(func2)
    def func(*args, **kwargs):
        return func1(*args, **kwargs) and func2(*args, **kwargs)

    return func


def take_everything(fileinfo):
    return True


class ZipReader(KvReader):
    """A KvReader to read the contents of a zip file.
    Provides a KV perspective of https://docs.python.org/3/library/zipfile.html

    Note: If you get data zipped by a mac, you might get some junk along with it.
    Namely `__MACOSX` folders `.DS_Store` files. I won't rant about it, since others have.
    But you might find it useful to remove them from view. One choice is to use `py2store.trans.filtered_iter`
    to get a filtered view of the zips contents. In most cases, this should do the job:
    ```
    # applied to store instance or class:
    store = filtered_iter(lambda x: not x.startswith('__MACOSX') and '.DS_Store' not in x)(store)
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

    def __init__(self, zip_file, prefix='', open_kws=None, file_info_filt=None):
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
            if isinstance(zip_file, dict):
                zip_file = ZipFile(**zip_file)
            elif isinstance(zip_file, (tuple, list)):
                zip_file = ZipFile(*zip_file)
            else:
                zip_file = ZipFile(zip_file)
        self.zip_file = zip_file

    @classmethod
    def for_files_only(cls, zip_file, prefix='', open_kws=None, file_info_filt=None):
        if file_info_filt is None:
            file_info_filt = ZipReader.FILES_ONLY
        else:
            _file_info_filt = file_info_filt

            def file_info_filt(x):
                return ZipReader.FILES_ONLY(x) and _file_info_filt(x)

        return cls(zip_file, prefix, open_kws, file_info_filt)

    @lazyprop
    def info_for_key(self):
        return {x.filename: x for x in self.zip_file.infolist()
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
            return self.__class__(self.zip_file, k, self.open_kws, self.file_info_filt)

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
        args_str = ', '.join((
            f"'{self.zip_file.filename}'",
            f"'{self.prefix}'",
            f"{self.open_kws}",
            f"{self.file_info_filt}"
        ))
        return f"{self.__class__.__name__}({args_str})"


class ZipFilesReader(FileCollection, KvReader):
    """A local file reader whose keys are the zip filepaths of the rootdir and values are corresponding ZipReaders.
    """

    def __init__(self, rootdir, subpath='.+\.zip', pattern_for_field=None, max_levels=0,
                 prefix='', open_kws=None, file_info_filt=ZipReader.FILES_ONLY):
        super().__init__(rootdir, subpath, pattern_for_field, max_levels)
        self.zip_reader_kwargs = dict(prefix=prefix, open_kws=open_kws, file_info_filt=file_info_filt)

    def __getitem__(self, k):
        return ZipReader(k, **self.zip_reader_kwargs)


class FlatZipFilesReader(ZipFilesReader):
    """Read the union of the contents of multiple zip files.
    A local file reader whose keys are the zip filepaths of the rootdir and values are corresponding ZipReaders.

    """

    @lazyprop
    def _zip_readers(self):
        rootdir_len = len(self.rootdir)
        return {fullpath[rootdir_len:]: super(FlatZipFilesReader, self).__getitem__(fullpath)
                for fullpath in super().__iter__()}

    def __iter__(self):
        for zip_relpath, zip_reader in self._zip_readers.items():  # go through the zip paths
            for path_in_zip in zip_reader:  # go through the keys of the ZipReader (the zipped filepaths)
                yield (zip_relpath, path_in_zip)

    def __getitem__(self, k):
        zip_relpath, path_in_zip = k  # k is a pair of the path to the zip file and the path of a file within it
        return self._zip_readers[zip_relpath][path_in_zip]


ZipFileReader = ZipFilesReader  # back-compatibility alias


class FilesOfZip(ZipReader):
    def __init__(self, zip_file, prefix='', open_kws=None):
        super().__init__(zip_file, prefix=prefix, open_kws=open_kws, file_info_filt=ZipReader.FILES_ONLY)

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
