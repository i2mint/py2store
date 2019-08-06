import os
import re
from functools import partial
from glob import iglob

from py2store.base import KeyValidationABC
from py2store.errors import ReadsNotAllowed, WritesNotAllowed, DeletionsNotAllowed
from py2store.mixins import FilteredKeysMixin, IterBasedSizedMixin
from py2store.parse_format import match_re_for_fstring

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


# class FilepathFormatKeys(FilteredKeysMixin, KeyValidationABC, PrefixedFilepathsRecursive, IterBasedSizedMixin):
class FilepathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                         PrefixedFilepathsRecursive, IterBasedSizedMixin):
    pass


class DirpathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                        PrefixedDirpathsRecursive, IterBasedSizedMixin):
    pass


########################################################################################################################
# Local File Persistence : Utils


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


class FilepathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                         PrefixedFilepathsRecursive, IterBasedSizedMixin):
    pass


class PathFormatPersister(FilepathFormatKeys, LocalFileRWD):
    def __init__(self, path_format, read=DFLT_READ_MODE, write=DFLT_WRITE_MODE, delete=DFLT_DELETE_MODE,
                 buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        FilepathFormatKeys.__init__(self, path_format)
        LocalFileRWD.__init__(self, read, write, delete,
                              buffering=buffering, encoding=encoding, errors=errors,
                              newline=newline, closefd=closefd, opener=opener)


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
