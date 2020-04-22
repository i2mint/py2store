import os
from os import stat as os_stat
from functools import wraps

from py2store.base import Collection, KvReader, KvPersister
from py2store.key_mappers.naming import mk_pattern_from_template_and_format_dict
from py2store.key_mappers.paths import mk_relative_path_store
from py2store.persisters.local_files import inf, ensure_slash_suffix, iter_filepaths_in_folder_recursively, \
    iter_dirpaths_in_folder_recursively

# TODO: subpath: Need to be able to allow named and unnamed file format markers (i.e {} and {named})

_dflt_not_valid_error_msg = "Key not valid (usually because does not exist or access not permitted): {}"
_dflt_not_found_error_msg = "Key not found: {}"


class KeyValidationError(KeyError):
    pass


# TODO: The validate and try/except is a frequent pattern. Make it a decorator.
def validate_key_and_raise_key_error_on_exception(func):
    @wraps(func)
    def wrapped_method(self, k, *args, **kwargs):
        self.validate_key(k)
        try:
            return func(self, k, *args, **kwargs)
        except Exception as e:
            raise KeyError(e)

    return wrapped_method


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

    def validate_key(self, k, err_msg_format=_dflt_not_valid_error_msg, err_type=KeyValidationError):
        if not self.is_valid_key(k):
            raise err_type(err_msg_format.format(k))


class DirCollection(FileSysCollection):

    def __iter__(self):
        yield from filter(self.is_valid_key,
                          iter_dirpaths_in_folder_recursively(self.rootdir, max_levels=self._max_levels))

    def __contains__(self, k):
        return self.is_valid_key(k) and os.path.isdir(k)


class FileCollection(FileSysCollection):

    def __iter__(self):
        """
        Iterator of valid filepaths.
        >>> import os
        >>> filepath = __file__  # path to this module
        >>> dirpath = os.path.dirname(__file__)  # path of the directory where I (the module file) am
        >>> s = FileCollection(dirpath, max_levels=0)
        >>>
        >>> files_in_this_dir = list(s)
        >>> filepath in files_in_this_dir
        True
        """
        yield from filter(self.is_valid_key,
                          iter_filepaths_in_folder_recursively(self.rootdir, max_levels=self._max_levels))

    def __contains__(self, k):
        """
        Checks if k is valid and contained in the store
        >>> import os
        >>> filepath = __file__  # path to this module
        >>> dirpath = os.path.dirname(__file__)  # path of the directory where I (the module file) am
        >>> s = FileCollection(dirpath, max_levels=0)
        >>>
        >>> filepath in s
        True
        >>> '_this_filepath_will_never_be_valid_' in s
        False
        """
        return self.is_valid_key(k) and os.path.isfile(k)


class FileInfoReader(FileCollection):
    def __getitem__(self, k):
        self.validate_key(k)
        return os_stat(k)


class FileBytesReader(FileCollection, KvReader):
    _read_open_kwargs = dict(mode='rb', buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
                             opener=None)

    @validate_key_and_raise_key_error_on_exception
    def __getitem__(self, k):
        """
        Gets the bytes contents of the file k.
        >>> import os
        >>> filepath = __file__
        >>> dirpath = os.path.dirname(__file__)  # path of the directory where I (the module file) am
        >>> s = FileBytesReader(dirpath, max_levels=0)
        >>>
        >>> ####### Get the first 9 characters (as bytes) of this module #####################
        >>> s[filepath][:9]
        b'import os'
        >>>
        >>> ####### Test key validation #####################
        >>> s['not_a_valid_key']  # this key is not valid since not under the dirpath folder
        Traceback (most recent call last):
            ...
        filesys.KeyValidationError: 'Key not valid (usually because does not exist or access not permitted): not_a_valid_key'
        >>>
        >>> ####### Test further exceptions (that should be wrapped in KeyError) #####################
        >>> # this key is valid, since under dirpath, but the file itself doesn't exist (hopefully for this test)
        >>> non_existing_file = os.path.join(dirpath, 'non_existing_file')
        >>> try:
        ...     s[non_existing_file]
        ... except KeyError:
        ...     print("KeyError (not FileNotFoundError) was raised.")
        KeyError (not FileNotFoundError) was raised.
        """
        with open(k, **self._read_open_kwargs) as fp:
            return fp.read()


class FileBytesPersister(FileBytesReader, KvPersister):
    _write_open_kwargs = dict(mode='wb', buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
                              opener=None)

    @validate_key_and_raise_key_error_on_exception
    def __setitem__(self, k, v):
        with open(k, **self._write_open_kwargs) as fp:
            return fp.write(v)

    @validate_key_and_raise_key_error_on_exception
    def __delitem__(self, k):
        os.remove(k)


RelPathFileBytesReader = mk_relative_path_store(FileBytesReader,
                                                name='RelPathFileBytesReader',
                                                prefix_attr='rootdir')
