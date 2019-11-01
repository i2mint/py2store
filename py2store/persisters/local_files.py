import os
import re
from glob import iglob
from collections.abc import Mapping

from py2store.errors import NoSuchKeyError

from py2store.base import KeyValidationABC
from py2store.mixins import FilteredKeysMixin, IterBasedSizedMixin
from py2store.parse_format import match_re_for_fstring
from py2store.base import Persister, KvReader
from py2store.errors import KeyValidationError

DFLT_OPEN_MODE = ''

file_sep = os.path.sep
inf = float('infinity')

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


def iter_filepaths_in_folder_recursively(root_folder, max_levels=inf, _current_level=0):
    for full_path in paths_in_dir(root_folder):
        if os.path.isdir(full_path):
            if _current_level < max_levels:
                for entry in iter_filepaths_in_folder_recursively(full_path, max_levels, _current_level + 1):
                    yield entry
        else:
            if os.path.isfile(full_path):
                yield full_path


def iter_dirpaths_in_folder_recursively(root_folder):
    for full_path in paths_in_dir(root_folder):
        if os.path.isdir(full_path):
            yield full_path
            for entry in iter_dirpaths_in_folder_recursively(full_path):
                yield entry


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
        with open(k, **self._open_kwargs_for_write) as fp:
            fp.write(v)

    def __delitem__(self, k):
        try:
            return os.remove(k)
        except FileNotFoundError as e:
            raise KeyError("{}: {}".format(type(e).__name__, e))


class FilepathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                         PrefixedFilepathsRecursive, IterBasedSizedMixin):
    pass


class DirpathFormatKeys(PathFormat, FilteredKeysMixin, KeyValidationABC,
                        PrefixedDirpathsRecursive, IterBasedSizedMixin):
    pass


class PathFormatPersister(FilepathFormatKeys, LocalFileRWD):
    def __init__(self, path_format, mode=DFLT_OPEN_MODE, **open_kwargs):
        FilepathFormatKeys.__init__(self, path_format)
        LocalFileRWD.__init__(self, mode, **open_kwargs)


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
    """ KV Reader whose keys (AND VALUES) are directory full paths of the subdirectories of _prefix rootdir.
    """

    def __init__(self, _prefix):
        self._prefix = ensure_slash_suffix(_prefix)
        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self._new_node = self.__class__
        self._class_name = self.__class__.__name__

    def _extended_prefix(self, new_prefix):
        return extend_prefix(self._prefix, new_prefix)

    def __contains__(self, k):
        return k.startswith(self._prefix) and os.path.isdir(k)

    def __iter__(self):
        return filter(os.path.isdir,  # (3) filter out any non-directories
                      map(self._extended_prefix,  # (2) extend prefix with sub-path name
                          os.listdir(self._prefix)))  # (1) list file names under _prefix

    def __getitem__(self, k):
        if os.path.isdir(k):
            return self._new_node(k)
        else:
            raise NoSuchKeyError(f"No such key (perhaps it's not a directory, or was deleted?): {k}")

    def __repr__(self):
        return f"{self._class_name}('{self._prefix}')"


class FileReader(KvReader):
    """ KV Reader whose keys (AND VALUES) are file full paths of _prefix (rootdir).
    """

    def __init__(self, _prefix):
        self._prefix = ensure_slash_suffix(_prefix)
        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self._new_node = self.__class__
        self._class_name = self.__class__.__name__

    def _extended_prefix(self, new_prefix):
        return extend_prefix(self._prefix, new_prefix)

    def __contains__(self, k):
        return k.startswith(self._prefix) and os.path.isdir(k)

    def __iter__(self):
        return filter(os.path.isdir,  # (3) filter out any non-directories
                      map(self._extended_prefix,  # (2) extend prefix with sub-path name
                          os.listdir(self._prefix)))  # (1) list file names under _prefix

    def __getitem__(self, k):
        if os.path.isdir(k):
            return self._new_node(k)
        else:
            raise NoSuchKeyError(f"No such key (perhaps it's not a directory, or was deleted?): {k}")

    def __repr__(self):
        return f"{self._class_name}('{self._prefix}')"


from py2store.base import KvCollection


class FileCollection(KvCollection):
    def __init__(self, _prefix, max_levels=inf):
        self._prefix = ensure_slash_suffix(_prefix)
        self._max_levels = max_levels

    def __iter__(self):
        yield from iter_filepaths_in_folder_recursively(self._prefix, max_levels=self._max_levels)

    def __contains__(self, k):
        return k.startswith(self._prefix) and os.path.isfile(k)

#
# if __name__ == '__main__':
#     from py2store.test.simple import test_local_file_ops
#
#     test_local_file_ops()
