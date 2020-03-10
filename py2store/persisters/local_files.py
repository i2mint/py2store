import os
import re
from glob import iglob
from pathlib import Path
from itertools import takewhile

from py2store.errors import NoSuchKeyError

from py2store.base import KeyValidationABC
from py2store.mixins import FilteredKeysMixin, IterBasedSizedMixin
from py2store.parse_format import match_re_for_fstring
from py2store.base import KvReader

DFLT_OPEN_MODE = ''

file_sep = os.path.sep
inf = float('infinity')


class FolderNotFoundError(NoSuchKeyError): ...


########################################################################################################################
# File system navigation: Utils

def ensure_slash_suffix(path):
    if not path.endswith(file_sep):
        return path + file_sep
    else:
        return path


def pattern_filter(pattern):
    pattern = re.compile(pattern)

    def _pattern_filter(s):
        return pattern.match(s) is not None

    return _pattern_filter


def paths_in_dir_with_slash_suffix_for_dirs(rootdir):
    for f in iglob(ensure_slash_suffix(rootdir) + '*'):
        if os.path.isdir(f):
            yield ensure_slash_suffix(f)
        else:
            yield f


def iter_relative_files_and_folder(root_folder):
    root_folder = ensure_slash_suffix(root_folder)
    return map(lambda x: x.replace(root_folder, ''), iglob(root_folder + '*'))


def iter_filepaths_in_folder(root_folder):
    return (os.path.join(root_folder, name) for name in iter_relative_files_and_folder(root_folder))


def paths_in_dir(rootdir):
    return iglob(ensure_slash_suffix(rootdir) + '*')


def filepaths_in_dir(rootdir):
    return filter(os.path.isfile, iglob(ensure_slash_suffix(rootdir) + '*'))


def dirpaths_in_dir(rootdir):
    return filter(os.path.isdir, iglob(ensure_slash_suffix(rootdir) + '*'))


def iter_filepaths_in_folder_recursively(root_folder, max_levels=None, _current_level=0):
    if max_levels is None:
        max_levels = inf
    for full_path in paths_in_dir(root_folder):
        if os.path.isdir(full_path):
            if _current_level < max_levels:
                for entry in iter_filepaths_in_folder_recursively(full_path, max_levels, _current_level + 1):
                    yield entry
        else:
            if os.path.isfile(full_path):
                yield full_path


def iter_dirpaths_in_folder_recursively(root_folder, max_levels=None, _current_level=0):
    if max_levels is None:
        max_levels = inf
    for full_path in paths_in_dir(root_folder):
        if os.path.isdir(full_path):
            yield full_path
            if _current_level < max_levels:
                for entry in iter_dirpaths_in_folder_recursively(full_path, max_levels, _current_level + 1):
                    yield entry


class PrefixedFilepaths:
    """
    Keys collection for local files, where the keys are full filepaths DIRECTLY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """
    _max_levels = None

    def __iter__(self):
        return iter_relative_files_and_folder(self._prefix, max_levels=self._max_levels)

    def __contains__(self, k):
        """
        Check if filepath exists (i.e. the path exists and is a file)
        :param k: A key to search for
        :return: True if k exists, False if not
        """
        return os.path.isfile(k)


class PrefixedFilepathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """
    _max_levels = None

    def __iter__(self):
        return iter_filepaths_in_folder_recursively(self._prefix, max_levels=self._max_levels)


class PrefixedDirpathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """
    _max_levels = None

    def __iter__(self):
        return iter_dirpaths_in_folder_recursively(self._prefix, max_levels=self._max_levels)


def path_match_regex_from_path_format(path_format):
    if '{' not in path_format:
        # if the path_format is equal to the _prefix (i.e. there's no {} formatting)
        # ... append a formatting element so that the matcher can match all subfiles.
        path_format = path_format + '{}'

    return match_re_for_fstring(path_format)


class PathFormat:
    def __init__(self, path_format: str):
        """
        A class for pattern-filtered exploration of file paths.
        :param path_format: The f-string format that the fullpath keys of the obj source should have.
            Often, just the root directory whose FILES contain the (full_filepath, content) data
            Also common is to use path_format='{rootdir}/{relative_path}.EXT' to impose a specific extension EXT
        """
        self._path_format = path_format  # not intended for use, but keeping in case, for now

        if '{' not in path_format:
            rootdir = ensure_slash_suffix(path_format)
            # if the path_format is equal to the _prefix (i.e. there's no {} formatting)
            # ... append a formatting element so that the matcher can match all subfiles.
            path_pattern = path_format + '{}'
        else:
            rootdir = ensure_slash_suffix(os.path.dirname(re.match('[^\{]*', path_format).group(0)))
            path_pattern = path_format

        self._prefix = rootdir
        self._path_match_re = match_re_for_fstring(path_pattern)

        def _key_filt(k):
            return bool(self._path_match_re.match(k))

        self._key_filt = _key_filt

    def is_valid_key(self, k):
        return self._key_filt(k)


def _is_not_dir(p):
    return not p.is_dir()


def first_non_existing_parent_dir(dirpath):
    parent = ''
    for parent in takewhile(_is_not_dir, Path(dirpath).parents):
        pass
    return str(parent)


########################################################################################################################
# Local File Persistence : Classes


class LocalFileRWD:
    """
    A class providing get, set and delete functionality using local files as the storage backend.
    """

    def __init__(self, mode='', **open_kwargs):
        if mode not in {'', 'b', 't'}:
            raise ValueError("mode should be '', 'b', or 't'")

        read_mode = open_kwargs.pop('read_mode', 'r' + mode)
        write_mode = open_kwargs.pop('write_mode', 'w' + mode)
        self._open_kwargs_for_read = dict(open_kwargs, mode=read_mode)
        self._open_kwargs_for_write = dict(open_kwargs, mode=write_mode)

    def __getitem__(self, k):
        try:
            with open(k, **self._open_kwargs_for_read) as fp:
                data = fp.read()
            return data
        except FileNotFoundError as e:
            raise KeyError("{}: {}".format(type(e).__name__, e))

    def __setitem__(self, k, v):
        try:
            with open(k, **self._open_kwargs_for_write) as fp:
                fp.write(v)
        except FileNotFoundError:
            raise FolderNotFoundError(f"The store you're using doesn't create directories for you. "
                                      f"You have to make the directories needed yourself manually, "
                                      f"or use a store that does that for you (example QuickStore). "
                                      f"This is the first directory that didn't exist:\n"
                                      f"{first_non_existing_parent_dir(k)}")

    def __delitem__(self, k):
        try:
            return os.remove(k)
        except FileNotFoundError as e:
            raise KeyError("{}: {}".format(type(e).__name__, e))


class FilepathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                         PrefixedFilepathsRecursive, IterBasedSizedMixin):
    def __init__(self, path_format: str, max_levels: int = inf):
        super().__init__(path_format)
        self._max_levels = max_levels


class DirpathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                        PrefixedDirpathsRecursive, IterBasedSizedMixin):
    def __init__(self, path_format: str, max_levels: int = inf):
        super().__init__(path_format)
        self._max_levels = max_levels


class PathFormatPersister(FilepathFormatKeys, LocalFileRWD):
    def __init__(self, path_format, max_levels: int = inf, mode=DFLT_OPEN_MODE, **open_kwargs):
        FilepathFormatKeys.__init__(self, path_format)
        LocalFileRWD.__init__(self, mode, **open_kwargs)
        self._max_levels = max_levels


class PrefixedFilepaths:
    """
    Keys collection for local files, where the keys are full filepaths DIRECTLY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_relative_files_and_folder(self._prefix)

    def __contains__(self, k):
        """
        Check if filepath exists (i.e. the path exists and is a file)
        :param k: A key to search for
        :return: True if k exists, False if not
        """
        return os.path.isfile(k)


class PrefixedFilepathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_filepaths_in_folder_recursively(self._prefix)


class PrefixedDirpathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_dirpaths_in_folder_recursively(self._prefix)


def extend_prefix(prefix, new_prefix):
    return ensure_slash_suffix(os.path.join(prefix, new_prefix))


class DirReader(KvReader):
    """ KV Reader whose keys (AND VALUES) are directory full paths of the subdirectories of rootdir.
    """

    def __init__(self, rootdir):
        self.rootdir = ensure_slash_suffix(rootdir)
        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self._new_node = self.__class__
        self._class_name = self.__class__.__name__

    def _extended_prefix(self, new_prefix):
        return extend_prefix(self.rootdir, new_prefix)

    def __contains__(self, k):
        return k.startswith(self.rootdir) and os.path.isdir(k)

    def __iter__(self):
        return filter(os.path.isdir,  # (3) filter out any non-directories
                      map(self._extended_prefix,  # (2) extend prefix with sub-path name
                          os.listdir(self.rootdir)))  # (1) list file names under _prefix

    def __getitem__(self, k):
        if os.path.isdir(k):
            return self._new_node(k)
        else:
            raise NoSuchKeyError(f"No such key (perhaps it's not a directory, or was deleted?): {k}")

    def __repr__(self):
        return f"{self._class_name}('{self.rootdir}')"


class FileReader(KvReader):
    """ KV Reader whose keys (AND VALUES) are file full paths of rootdir.
    """

    def __init__(self, rootdir):
        self.rootdir = ensure_slash_suffix(rootdir)
        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self._new_node = self.__class__
        self._class_name = self.__class__.__name__

    def _extended_prefix(self, new_prefix):
        return extend_prefix(self.rootdir, new_prefix)

    def __contains__(self, k):
        return k.startswith(self.rootdir) and os.path.isdir(k)

    def __iter__(self):
        return filter(os.path.isdir,  # (3) filter out any non-directories
                      map(self._extended_prefix,  # (2) extend prefix with sub-path name
                          os.listdir(self.rootdir)))  # (1) list file names under _prefix

    def __getitem__(self, k):
        if os.path.isdir(k):
            return self._new_node(k)
        else:
            raise NoSuchKeyError(f"No such key (perhaps it's not a directory, or was deleted?): {k}")

    def __repr__(self):
        return f"{self._class_name}('{self.rootdir}')"


from py2store.base import Collection
from py2store.key_mappers.naming import mk_pattern_from_template_and_format_dict


class FileSysCollection(Collection):
    def __init__(self, rootdir, subpath='', pattern_for_field=None, max_levels=None):
        if max_levels is None:
            max_levels = inf
        subpath_implied_min_levels = len(subpath.split(os.path.sep)) - 1
        assert max_levels >= subpath_implied_min_levels, \
            f"max_levels is {max_levels}, but subpath {subpath} would imply at least {subpath_implied_min_levels}"
        pattern_for_field = pattern_for_field or {}
        self.rootdir = ensure_slash_suffix(rootdir)
        self.subpath = subpath
        self._key_pattern = mk_pattern_from_template_and_format_dict(os.path.join(rootdir, subpath), pattern_for_field)
        self._max_levels = max_levels

    def is_valid_key(self, k):
        return bool(self._key_pattern.match(k))


class FileCollection(FileSysCollection):

    def __iter__(self):
        yield from filter(self.is_valid_key,
                          iter_filepaths_in_folder_recursively(self.rootdir, max_levels=self._max_levels))

    def __contains__(self, k):
        return k.startswith(self.rootdir) and os.path.isfile(k) and self.is_valid_key(k)


class DirCollection(FileSysCollection):

    def __iter__(self):
        yield from filter(self.is_valid_key,
                          iter_dirpaths_in_folder_recursively(self.rootdir, max_levels=self._max_levels))

    def __contains__(self, k):
        return k.startswith(self.rootdir) and os.path.isdir(k) and self.is_valid_key(k)


from zipfile import ZipFile
import os
import inspect
from functools import wraps
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


# TODO: The way prefix and file_info_filt is handled is not efficient
# TODO: prefix is silly: less general than filename_filt would be, and not even producing relative paths
# (especially when getitem returns subdirs)
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


class ZipFileReader(FileCollection, KvReader):
    """A local file reader whose keys are the zip filepaths of the rootdir and values are corresponding ZipReaders.
    """

    def __init__(self, rootdir, subpath='.+\.zip', pattern_for_field=None, max_levels=0,
                 prefix='', open_kws=None, file_info_filt=take_everything):
        super().__init__(rootdir, subpath, pattern_for_field, max_levels)
        self.zip_reader_kwargs = dict(prefix=prefix, open_kws=open_kws, file_info_filt=file_info_filt)

    def __getitem__(self, k):
        return ZipReader(k, **self.zip_reader_kwargs)


ZipFilesReader = ZipFileReader  # alias because singular ZipFileReader is misleading. Deprecate?


class FilesOfZip(ZipReader):
    def __init__(self, zip_file, prefix='', open_kws=None):
        super().__init__(zip_file, prefix=prefix, open_kws=open_kws, file_info_filt=ZipReader.FILES_ONLY)

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
