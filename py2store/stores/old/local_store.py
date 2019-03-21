from glob import iglob
import os
import re
from typing import Callable, Union, Any
# import soundfile as sf  # TODO: Replace by another wav reader, and move to another module

# from py2store.base import Keys
from py2store.base import StoreBaseMixin, IdentityKvWrapMixin, StoreMutableMapping, KeyValidationABC
from py2store.mixins import IterBasedSizedMixin, FilteredKeysMixin
from py2store.parse_format import match_re_for_fstring
from py2store.core import PrefixRelativizationMixin

DFLT_READ_MODE = ''
DFLT_WRITE_MODE = ''
DFLT_DELETE_MODE = True

file_sep = os.path.sep


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


def iter_relative_files_and_folder(root_folder):
    root_folder = ensure_slash_suffix(root_folder)
    return map(lambda x: x.replace(root_folder, ''), iglob(root_folder + '*'))


def iter_filepaths_in_folder(root_folder):
    return (os.path.join(root_folder, name) for name in iter_relative_files_and_folder(root_folder))


def iter_filepaths_in_folder_recursively(root_folder):
    for full_path in iter_filepaths_in_folder(root_folder):
        if os.path.isdir(full_path):
            for entry in iter_filepaths_in_folder_recursively(full_path):
                yield entry
        else:
            if os.path.isfile(full_path):
                yield full_path


def iter_dirpaths_in_folder_recursively(root_folder):
    for full_path in iter_filepaths_in_folder(root_folder):
        if os.path.isdir(full_path):
            yield full_path
            for entry in iter_dirpaths_in_folder_recursively(full_path):
                yield entry


########################################################################################################################
# File system navigation: Classes
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


# class FilepathFormatKeys(FilteredKeysMixin, KeyValidationABC, PrefixedFilepathsRecursive, IterBasedSizedMixin):
class FilepathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                         PrefixedFilepathsRecursive, IterBasedSizedMixin):
    pass


class DirpathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                        PrefixedDirpathsRecursive, IterBasedSizedMixin):
    pass


########################################################################################################################
# Local File Persistence : Utils
from functools import partial


def _specific_open(mode, buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    return partial(open, mode=mode, buffering=buffering, encoding=encoding,
                   errors=errors, newline=newline, closefd=closefd, opener=opener)


def mk_file_reader(mode_suffix='', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    specific_open = _specific_open(mode='r' + mode_suffix, buffering=buffering, encoding=encoding,
                                   errors=errors, newline=newline, closefd=closefd, opener=opener)

    def read_file(filepath):
        with specific_open(filepath) as fp:
            return fp.read()

    return read_file


def mk_file_writer(mode_suffix='', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    specific_open = _specific_open(mode='w' + mode_suffix, buffering=buffering, encoding=encoding,
                                   errors=errors, newline=newline, closefd=closefd, opener=opener)

    def write_to_file(filepath, data):
        with specific_open(filepath) as fp:
            return fp.write(data)

    return write_to_file


########################################################################################################################
# Local File Persistence : Classes

from py2store.errors import ReadsNotAllowed, WritesNotAllowed, DeletionsNotAllowed


class LocalFileReader:
    def __init__(self, read_mode=DFLT_READ_MODE,
                 buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if read_mode is False:
            def _read_file(k):
                raise ReadsNotAllowed("Read permissions were disabled for this data accessor")

            self._read_file = _read_file
        else:
            read_mode = read_mode or ''
            self._read_file = mk_file_reader(read_mode, buffering=buffering, encoding=encoding,
                                             errors=errors, newline=newline, closefd=closefd, opener=opener)

    def __getitem__(self, k):
        try:
            return self._read_file(k)
        except FileNotFoundError as e:
            raise KeyError("{}: {}".format(type(e).__name__, e))


class LocalFileWriter:
    def __init__(self, write_mode=DFLT_WRITE_MODE,
                 buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if write_mode is False:
            def _write_to_file(k):
                raise WritesNotAllowed("Write permissions were disabled for this data accessor")

            self._write_to_file = _write_to_file
        else:
            write_mode = write_mode or ''
            self._write_to_file = mk_file_writer(write_mode, buffering=buffering, encoding=encoding,
                                                 errors=errors, newline=newline, closefd=closefd, opener=opener)

    def __setitem__(self, k, v):
        return self._write_to_file(k, v)


class LocalFileDeleter:
    def __init__(self, deletion_mode=DFLT_DELETE_MODE):
        if deletion_mode is False:
            def _delete_file(k):
                raise DeletionsNotAllowed("Delete permissions were disabled for this data accessor")

            self._delete_file = _delete_file
        else:
            def _delete_file(k):
                os.remove(k)

            self._delete_file = _delete_file

    def __delitem__(self, k):
        try:
            return self._delete_file(k)
        except FileNotFoundError as e:
            raise KeyError("{}: {}".format(type(e).__name__, e))


class LocalFileRWD(LocalFileReader, LocalFileWriter, LocalFileDeleter):
    """
    A class providing get, set and delete functionality using local files as the storage backend.
    """

    def __init__(self, read=DFLT_READ_MODE, write=DFLT_WRITE_MODE, delete=DFLT_DELETE_MODE,
                 buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        rw_kwargs = dict(buffering=buffering, encoding=encoding, errors=errors,
                         newline=newline, closefd=closefd, opener=opener)
        if not isinstance(read, dict):
            read = dict(rw_kwargs, read_mode=read)
        if not isinstance(write, dict):
            write = dict(rw_kwargs, write_mode=write)

        LocalFileReader.__init__(self, **read)
        LocalFileWriter.__init__(self, **write)
        LocalFileDeleter.__init__(self, delete)


class PathFormatPersister(FilepathFormatKeys, LocalFileRWD):
    def __init__(self, path_format, read=DFLT_READ_MODE, write=DFLT_WRITE_MODE, delete=DFLT_DELETE_MODE,
                 buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        FilepathFormatKeys.__init__(self, path_format)
        LocalFileRWD.__init__(self, read, write, delete,
                              buffering=buffering, encoding=encoding, errors=errors,
                              newline=newline, closefd=closefd, opener=opener)


class PathFormatStore(StoreBaseMixin, IdentityKvWrapMixin, PathFormatPersister, StoreMutableMapping):
    """
    Union of FilepathFormatKeys and LocalFileRWD.

    >>> from tempfile import gettempdir
    >>> import os
    >>>
    >>> def write_to_key(fullpath_of_relative_path, relative_path, content):  # a function to write content in files
    ...    with open(fullpath_of_relative_path(relative_path), 'w') as fp:
    ...        fp.write(content)
    >>>
    >>> # Preparation: Make a temporary rootdir and write two files in it
    >>> rootdir = os.path.join(gettempdir(), 'path_format_store_test' + os.sep)
    >>> if not os.path.isdir(rootdir):
    ...     os.mkdir(rootdir)
    >>> # recreate directory (remove existing files, delete directory, and re-create it)
    >>> for f in os.listdir(rootdir):
    ...     fullpath = os.path.join(rootdir, f)
    ...     if os.path.isfile(fullpath):
    ...         os.remove(os.path.join(rootdir, f))
    >>> if os.path.isdir(rootdir):
    ...     os.rmdir(rootdir)
    >>> if not os.path.isdir(rootdir):
    ...    os.mkdir(rootdir)
    >>>
    >>> filepath_of = lambda p: os.path.join(rootdir, p)  # a function to get a fullpath from a relative one
    >>> # and make two files in this new dir, with some content
    >>> write_to_key(filepath_of, 'a', 'foo')
    >>> write_to_key(filepath_of, 'b', 'bar')
    >>>
    >>> # point the obj source to the rootdir
    >>> s = PathFormatStore(path_format=rootdir)
    >>>
    >>> # assert things...
    >>> assert s._prefix == rootdir  # the _rootdir is the one given in constructor
    >>> assert s[filepath_of('a')] == 'foo'  # (the filepath for) 'a' contains 'foo'
    >>>
    >>> # two files under rootdir (as long as the OS didn't create it's own under the hood)
    >>> len(s)
    2
    >>> assert list(s) == [filepath_of('a'), filepath_of('b')]  # there's two files in s
    >>> filepath_of('a') in s  # rootdir/a is in s
    True
    >>> filepath_of('not_there') in s  # rootdir/not_there is not in s
    False
    >>> filepath_of('not_there') not in s  # rootdir/not_there is not in s
    True
    >>> assert list(s.keys()) == [filepath_of('a'), filepath_of('b')]  # the keys (filepaths) of s
    >>> sorted(list(s.values())) # the values of s (contents of files)
    ['bar', 'foo']
    >>> assert list(s.items()) == [(filepath_of('a'), 'foo'), (filepath_of('b'), 'bar')]  # the (path, content) items
    >>> assert s.get('this key is not there', None) is None  # trying to get the val of a non-existing key returns None
    >>> s.get('this key is not there', 'some default value')  # ... or whatever you say
    'some default value'
    >>>
    >>> # add more files to the same folder
    >>> write_to_key(filepath_of, 'this.txt', 'this')
    >>> write_to_key(filepath_of, 'that.txt', 'blah')
    >>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
    >>> # see that you now have 5 files
    >>> len(s)
    5
    >>> # and these files contain values:
    >>> sorted(s.values())
    ['bar', 'blah', 'bloo', 'foo', 'this']
    >>>
    >>> # but if we make an obj source to only take files whose extension is '.txt'...
    >>> s = PathFormatStore(path_format=rootdir + '{}.txt')
    >>>
    >>> rootdir_2 = os.path.join(gettempdir(), 'obj_source_test_2') # get another rootdir
    >>> if not os.path.isdir(rootdir_2):
    ...    os.mkdir(rootdir_2)
    >>> filepath_of_2 = lambda p: os.path.join(rootdir_2, p)
    >>> # and make two files in this new dir, with some content
    >>> write_to_key(filepath_of, 'this.txt', 'this')
    >>> write_to_key(filepath_of, 'that.txt', 'blah')
    >>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
    >>>
    >>> ss = PathFormatStore(path_format=rootdir_2 + '{}.txt')
    >>>
    >>> assert s != ss  # though pointing to identical content, o and oo are not equal since the paths are not equal!
    """
    pass


class RelativePathFormatStore(PrefixRelativizationMixin, PathFormatStore):
    pass


class RelativeDirPathFormatKeys(PrefixRelativizationMixin, StoreBaseMixin, IdentityKvWrapMixin, DirpathFormatKeys):
    pass


