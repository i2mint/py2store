from glob import iglob
import os
import re
from typing import Callable, Union, Any
import soundfile as sf  # TODO: Replace by another wav reader, and move to another module

from py2store.base import AbstractKeys, AbstractObjSource, FilteredKeys
from py2store.parse_format import match_re_for_fstring

from py2store.base import KeyValidation

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


########################################################################################################################
# File system navigation: Classes
class PrefixedFilepaths(AbstractKeys):
    """
    Keys collection for local files under a given prefix (root).
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


class PrefixedFilepathsRecursive(AbstractKeys):
    """
    Keys collection for local files.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_relative_files_and_folder(self._prefix)


class FilepathFormatKeys(FilteredKeys, PrefixedFilepathsRecursive):
    def __init__(self, path_format: str):
        """

        :param path_format: The f-string format that the fullpath keys of the obj source should have.
            Often, just the root directory whose FILES contain the (full_filepath, content) data
            Also common is to use path_format='{rootdir}/{relative_path}.EXT' to impose a specific extension EXT
        :param contents_of_file: The function that returns the python object stored at a given key (path)
        """
        if '{' not in path_format:
            self._prefix = path_format
        else:
            rootdir = re.match('[^\{]*', path_format).group(0)
            self._prefix = os.path.dirname(rootdir)

        self._prefix = ensure_slash_suffix(self._prefix)

        if path_format == self._prefix:  # if the path_format is equal to the _rootdir (i.e. there's no {} formatting)
            path_format += '{}'  # ... add a formatting element so that the matcher can match all subfiles.
        self._path_match_re = match_re_for_fstring(path_format)

        def _key_filt(k):
            return bool(self._path_match_re.match(k))

        self._key_filt = _key_filt
        self._path_format = path_format  # not intended for use, but keeping in case, for now


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
        return self._read_file(k)


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
        return self._delete_file(k)


class LocalFileRWD(LocalFileReader, LocalFileWriter, LocalFileDeleter):
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


class PathFormatStore(FilepathFormatKeys, LocalFileRWD):
    """
    An implementation of an ObjSource that uses local files as to store things.
    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
        mixin methods that collections.abc.Mapping adds automatically:
            __contains__, keys, items, values, get, __eq__, and __ne__
    >>> from tempfile import gettempdir
    >>> import os
    >>>
    >>> def write_to_key(fullpath_of_relative_path, relative_path, content):  # a function to write content in files
    ...    with open(fullpath_of_relative_path(relative_path), 'w') as fp:
    ...        fp.write(content)
    >>>
    >>> # Preparation: Make a temporary rootdir and write two files in it
    >>> rootdir = os.path.join(gettempdir(), 'obj_source_test')
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

    #
    # >>> filepath_of = lambda p: os.path.join(rootdir, p)  # a function to get a fullpath from a relative one
    # >>> # and make two files in this new dir, with some content
    # >>> write_to_key(filepath_of, 'a', 'foo')
    # >>> write_to_key(filepath_of, 'b', 'bar')
    # >>>
    # >>> # point the obj source to the rootdir
    # >>> o = LocalFileObjSource(path_format=rootdir)
    # >>>
    # >>> # assert things...
    # >>> assert o._rootdir == rootdir  # the _rootdir is the one given in constructor
    # >>> assert o[filepath_of('a')] == 'foo'  # (the filepath for) 'a' contains 'foo'
    # >>>
    # >>> # two files under rootdir (as long as the OS didn't create it's own under the hood)
    # >>> len(o)
    # 2
    # >>> assert list(o) == [filepath_of('a'), filepath_of('b')]  # there's two files in o
    # >>> filepath_of('a') in o  # rootdir/a is in o
    # True
    # >>> filepath_of('not_there') in o  # rootdir/not_there is not in o
    # False
    # >>> filepath_of('not_there') not in o  # rootdir/not_there is not in o
    # True
    # >>> assert list(o.keys()) == [filepath_of('a'), filepath_of('b')]  # the keys (filepaths) of o
    # >>> sorted(list(o.values())) # the values of o (contents of files)
    # ['bar', 'foo']
    # >>> assert list(o.items()) == [(filepath_of('a'), 'foo'), (filepath_of('b'), 'bar')]  # the (path, content) items
    # >>> assert o.get('this key is not there') == None  # trying to get the value of a non-existing key returns None...
    # >>> o.get('this key is not there', 'some default value')  # ... or whatever you say
    # 'some default value'
    # >>>
    # >>> # add more files to the same folder
    # >>> write_to_key(filepath_of, 'this.txt', 'this')
    # >>> write_to_key(filepath_of, 'that.txt', 'blah')
    # >>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
    # >>> # see that you now have 5 files
    # >>> len(o)
    # 5
    # >>> # and these files contain values:
    # >>> sorted(o.values())
    # ['bar', 'blah', 'bloo', 'foo', 'this']
    # >>>
    # >>> # but if we make an obj source to only take files whose extension is '.txt'...
    # >>> o = LocalFileObjSource(path_format=rootdir + '{}.txt')
    # >>>
    # >>>
    # >>> rootdir_2 = os.path.join(gettempdir(), 'obj_source_test_2') # get another rootdir
    # >>> if not os.path.isdir(rootdir_2):
    # ...    os.mkdir(rootdir_2)
    # >>> filepath_of_2 = lambda p: os.path.join(rootdir_2, p)
    # >>> # and make two files in this new dir, with some content
    # >>> write_to_key(filepath_of, 'this.txt', 'this')
    # >>> write_to_key(filepath_of, 'that.txt', 'blah')
    # >>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
    # >>>
    # >>> oo = LocalFileObjSource(path_format=rootdir_2 + '{}.txt')
    # >>>
    # >>> assert o != oo  # though pointing to identical content, o and oo are not equal since the paths are not equal!
    """

    def __init__(self, path_format, read=DFLT_READ_MODE, write=DFLT_WRITE_MODE, delete=DFLT_DELETE_MODE,
                 buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        FilepathFormatKeys.__init__(self, path_format)
        LocalFileRWD.__init__(self, read, write, delete,
                              buffering=buffering, encoding=encoding, errors=errors,
                              newline=newline, closefd=closefd, opener=opener)


########################################################################################################################
# LocalFile Daccs
class PrefixValidationMixin(KeyValidation):
    def is_valid_key(self, k):
        return k.startswith(self._prefix)


from py2store.base import KeyValidation, StoreInterface

#
# class LocalDacc(StoreInterface, KeyValidation):
#     def __init__(self, ):
#         """
#         S3 Bucket accessor.
#         This class is meant to be subclassed, used with other mixins that actually add read and write methods.
#         All S3BucketDacc does is create (or maintain) a bucket object, offer validation (is_valid)
#         and assertion methods (assert_is_valid) methods to check that a key is prefixed by given _prefix, and
#         more importantly, offers a hidden _id_of_key method that returns an object for a given key.
#
#         Observe that the _s3_bucket constructor argument is a boto3 s3.Bucket, but offers other factories to make
#         a S3BucketDacc instance.
#         For example. if you only have access and secrete keys (and possibly endpoint url, config, etc.)
#         then use the class method from_s3_resource_kwargs to construct.
#
#         :param bucket_name: Bucket name (string)
#         :param _s3_bucket: boto3 s3.Bucket object.
#         :param _prefix: prefix that all accessed keys should have
#         """
#         self.bucket_name = bucket_name
#         self._s3_bucket = _s3_bucket
#         self._prefix = _prefix
#
#     def is_valid_key(self, k):
#         return k.startswith(self._prefix)
#
#     def _id_of_key(self, k):
#         self.check_key_is_valid(k)
#         return self._s3_bucket.Object(key=k)
#
#     def _key_of_id(self, _id):
#         return _id.key

#
# class PrefixedKeysMixin(AbstractKeys):
#     """
#     A S3BucketDacc collection.
#     A collection is a iterable and sizable container.
#     That is, this mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)) to S3BucketDacc.
#     """
#
#     def __iter__(self):
#         return map(self._key_of_id, self._s3_bucket.objects.filter(Prefix=prefix))
#
#     def __contains__(self, k):
#         """
#         Check if key exists
#         :param k: A key to search for
#         :return: True if k exists, False if not
#         """
#         # TODO: s3_client.head_object(Bucket=dacc.bucket_name, Key=k) slightly more efficient but needs boto3.client
#         try:
#             self._id_of_key(k).load()
#         except ClientError as e:
#             if e.response['Error']['Code'] == "404":
#                 # The object does not exist.
#                 return False
#             else:
#                 # Something else has gone wrong.
#                 raise
#         else:
#             return True
#
#     # def __len__(self, k):  # TODO: Is there a s3 specific more efficient way of doing __len__?
#     #     pass
#
#
# class S3BucketReaderMixin(AbstractObjReader):
#     """ Mixin to add read functionality to a S3BucketDacc."""
#
#     def __getitem__(self, k):
#         try:  # TODO: Didn't manage to catch this exception for some reason. Make it work!
#             return k.get()['Body'].read()
#         except Exception as e:
#             if hasattr(e, '__name__'):
#                 if e.__name__ == 'NoSuchKey':
#                     raise NoSuchKeyError("Key wasn't found: {}".format(k))
#             raise  # if you got so far
#
#
# class S3BucketWriterMixin(AbstractObjWriter):
#     """ A mixin to add write and delete functionality """
#
#     def __setitem__(self, k, v):
#         """
#         Write data to s3 key.
#         Method will check if key is valid before writing data to it,
#         but will not check if data is already stored there.
#         This means that any data previously stored at the key's location will be lost.
#         :param k: s3 key
#         :param v: data to write
#         :return: None
#         """
#         # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
#
#     def __delitem__(self, k):
#         """
#         Delete data stored at key k.
#         Method will check if key is valid before deleting its data.
#         :param k:
#         :return:
#         """
#         # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
#         try:  # TODO: Didn't manage to catch this exception for some reason. Make it work!
#             k.delete()
#         except Exception as e:
#             if hasattr(e, '__name__'):
#                 if e.__name__ == 'NoSuchKey':
#                     raise NoSuchKeyError("Key wasn't found: {}".format(k))
#             raise  # if you got so far


########################################################################################################################
# LocalFileObjSource

mk_file_reader_func = None
dflt_contents_of_file = None


class LocalFileObjSource(AbstractObjSource):
    def __init__(self, contents_of_file: Callable[[str], Any]):
        """

        :param contents_of_file: The function that returns the python object stored at a given key (path)
        """
        self._contents_of_file = contents_of_file

    @classmethod
    def for_kind(cls, kind: str = 'dflt', **kwargs):
        """
        Makes a LocalFileObjSource using specific kind of serialization.
        :param path_format: the path_format to use for the LocalFileObjSource
        :param kind: kind of file reader to use ('dflt', 'wav', 'json', 'pickle')
        :param kwargs: to feed to the mk_file_reader_func to control the file reader that is made
        :return: an instance of LocalFileObjSource

        >>> import tempfile
        >>> import json, pickle
        >>>
        >>> ####### Testing the 'json' kind
        >>> filepath = tempfile.mktemp(suffix='.json')  # making a filepath for a json
        >>> d = {'a': 'foo', 'b': {'c': 'bar', 'd': 3}, 'c': [1, 2, 3], 'd': True, 'none': None}  # making some data
        >>> json.dump(d, open(filepath, 'w'))  # saving this data as a json file
        >>>
        >>> obj_source = LocalFileObjSource.for_kind(path_format='', kind='json')  # make an obj_source for json
        >>> assert d == obj_source[filepath]  # see that obj_source returns the same data we put into it
        >>>
        >>> ####### Testing the 'pickle' kind
        >>> filepath = tempfile.mktemp(suffix='.p')  # making a filepath for a pickle
        >>> import pandas as pd; d = pd.DataFrame({'A': [1, 2, 3], 'B': ['one', 'two', 'three']})  # make some data
        >>> pickle.dump(d, open(filepath, 'wb'), )  # save the data in the filepath
        >>> obj_source = LocalFileObjSource.for_kind(path_format='', kind='pickle')  # make an obj_source for pickles
        >>> assert all(d == obj_source[filepath])  # get the data in filepath and assert it's the same as the saved
        """
        contents_of_file = mk_file_reader_func(kind=kind, **kwargs)
        return cls(contents_of_file)

    def __getitem__(self, k):
        try:
            return self._contents_of_file(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(e.__class__.__name__, k, e))


class LocalFileObjSourceWithPathCollection(AbstractObjSource):
    """
    An implementation of an ObjSource that uses local files as to store things.
    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
        mixin methods that collections.abc.Mapping adds automatically:
            __contains__, keys, items, values, get, __eq__, and __ne__
    """

    def __init__(self, paths, contents_of_file: Callable[[str], Any] = dflt_contents_of_file):
        """

        :param paths: A collection (e.g. list, tuple, set) of paths
        :param contents_of_file: The function that returns the python object stored at a given key (path)
        """
        self.paths = paths
        self._contents_of_file = contents_of_file

    @classmethod
    def for_kind(cls, path_format: str, kind: str = 'dflt', **kwargs):
        """
        Makes a LocalFileObjSource using specific kind of serialization.
        :param path_format: the path_format to use for the LocalFileObjSource
        :param kind: kind of file reader to use ('dflt', 'wav', 'json', 'pickle')
        :param kwargs: to feed to the mk_file_reader_func to control the file reader that is made
        :return: an instance of LocalFileObjSource

        >>> import tempfile
        >>> import json, pickle
        >>>
        >>> ####### Testing the 'json' kind
        >>> filepath = tempfile.mktemp(suffix='.json')  # making a filepath for a json
        >>> d = {'a': 'foo', 'b': {'c': 'bar', 'd': 3}, 'c': [1, 2, 3], 'd': True, 'none': None}  # making some data
        >>> json.dump(d, open(filepath, 'w'))  # saving this data as a json file
        >>>
        >>> obj_source = LocalFileObjSource.for_kind(path_format='', kind='json')  # make an obj_source for json
        >>> assert d == obj_source[filepath]  # see that obj_source returns the same data we put into it
        >>>
        >>> ####### Testing the 'pickle' kind
        >>> filepath = tempfile.mktemp(suffix='.p')  # making a filepath for a pickle
        >>> import pandas as pd; d = pd.DataFrame({'A': [1, 2, 3], 'B': ['one', 'two', 'three']})  # make some data
        >>> pickle.dump(d, open(filepath, 'wb'), )  # save the data in the filepath
        >>> obj_source = LocalFileObjSource.for_kind(path_format='', kind='pickle')  # make an obj_source for pickles
        >>> assert all(d == obj_source[filepath])  # get the data in filepath and assert it's the same as the saved
        """
        contents_of_file = mk_file_reader_func(kind=kind, **kwargs)
        return cls(path_format, contents_of_file)

    def is_valid_key(self, k):
        return k in self.paths

    def __iter__(self):
        return self.paths

    def __contains__(self, k):  # override abstract version, which is not as efficient
        return self.is_valid_key(k) and os.path.isfile(k)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, k):
        try:
            return self._contents_of_file(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(e.__class__.__name__, k, e))


class LocalFileObjSourceWithPathFormat(AbstractObjSource):
    """
    An implementation of an ObjSource that uses local files as to store things.
    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
        mixin methods that collections.abc.Mapping adds automatically:
            __contains__, keys, items, values, get, __eq__, and __ne__
    >>> from tempfile import gettempdir
    >>> import os
    >>>
    >>> def write_to_key(fullpath_of_relative_path, relative_path, content):  # a function to write content in files
    ...    with open(fullpath_of_relative_path(relative_path), 'w') as fp:
    ...        fp.write(content)
    >>>
    >>> # Preparation: Make a temporary rootdir and write two files in it
    >>> rootdir = os.path.join(gettempdir(), 'obj_source_test')
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
    >>> o = LocalFileObjSource(path_format=rootdir)
    >>>
    >>> # assert things...
    >>> assert o._rootdir == rootdir  # the _rootdir is the one given in constructor
    >>> assert o[filepath_of('a')] == 'foo'  # (the filepath for) 'a' contains 'foo'
    >>>
    >>> # two files under rootdir (as long as the OS didn't create it's own under the hood)
    >>> len(o)
    2
    >>> assert list(o) == [filepath_of('a'), filepath_of('b')]  # there's two files in o
    >>> filepath_of('a') in o  # rootdir/a is in o
    True
    >>> filepath_of('not_there') in o  # rootdir/not_there is not in o
    False
    >>> filepath_of('not_there') not in o  # rootdir/not_there is not in o
    True
    >>> assert list(o.keys()) == [filepath_of('a'), filepath_of('b')]  # the keys (filepaths) of o
    >>> sorted(list(o.values())) # the values of o (contents of files)
    ['bar', 'foo']
    >>> assert list(o.items()) == [(filepath_of('a'), 'foo'), (filepath_of('b'), 'bar')]  # the (path, content) items
    >>> assert o.get('this key is not there') == None  # trying to get the value of a non-existing key returns None...
    >>> o.get('this key is not there', 'some default value')  # ... or whatever you say
    'some default value'
    >>>
    >>> # add more files to the same folder
    >>> write_to_key(filepath_of, 'this.txt', 'this')
    >>> write_to_key(filepath_of, 'that.txt', 'blah')
    >>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
    >>> # see that you now have 5 files
    >>> len(o)
    5
    >>> # and these files contain values:
    >>> sorted(o.values())
    ['bar', 'blah', 'bloo', 'foo', 'this']
    >>>
    >>> # but if we make an obj source to only take files whose extension is '.txt'...
    >>> o = LocalFileObjSource(path_format=rootdir + '{}.txt')
    >>>
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
    >>> oo = LocalFileObjSource(path_format=rootdir_2 + '{}.txt')
    >>>
    >>> assert o != oo  # though pointing to identical content, o and oo are not equal since the paths are not equal!
    """

    def __init__(self, path_format: str, contents_of_file: Callable[[str], Any] = dflt_contents_of_file):
        """

        :param path_format: The f-string format that the fullpath keys of the obj source should have.
            Often, just the root directory whose FILES contain the (full_filepath, content) data
            Also common is to use path_format='{rootdir}/{relative_path}.EXT' to impose a specific extension EXT
        :param contents_of_file: The function that returns the python object stored at a given key (path)
        """
        if '{' not in path_format:
            self._rootdir = path_format
        else:
            rootdir = re.match('[^\{]*', path_format).group(0)
            self._rootdir = os.path.dirname(rootdir)

        self._rootdir = ensure_slash_suffix(self._rootdir)

        if path_format == self._rootdir:  # if the path_format is equal to the _rootdir (i.e. there's no {} formatting)
            path_format += '{}'  # ... add a formatting element so that the matcher can match all subfiles.
        self._path_match_re = match_re_for_fstring(path_format)
        self._path_format = path_format
        self._contents_of_file = contents_of_file

    @classmethod
    def for_kind(cls, path_format: str, kind: str = 'dflt', **kwargs):
        """
        Makes a LocalFileObjSource using specific kind of serialization.
        :param path_format: the path_format to use for the LocalFileObjSource
        :param kind: kind of file reader to use ('dflt', 'wav', 'json', 'pickle')
        :param kwargs: to feed to the mk_file_reader_func to control the file reader that is made
        :return: an instance of LocalFileObjSource

        >>> import tempfile
        >>> import json, pickle
        >>>
        >>> ####### Testing the 'json' kind
        >>> filepath = tempfile.mktemp(suffix='.json')  # making a filepath for a json
        >>> d = {'a': 'foo', 'b': {'c': 'bar', 'd': 3}, 'c': [1, 2, 3], 'd': True, 'none': None}  # making some data
        >>> json.dump(d, open(filepath, 'w'))  # saving this data as a json file
        >>>
        >>> obj_source = LocalFileObjSource.for_kind(path_format='', kind='json')  # make an obj_source for json
        >>> assert d == obj_source[filepath]  # see that obj_source returns the same data we put into it
        >>>
        >>> ####### Testing the 'pickle' kind
        >>> filepath = tempfile.mktemp(suffix='.p')  # making a filepath for a pickle
        >>> import pandas as pd; d = pd.DataFrame({'A': [1, 2, 3], 'B': ['one', 'two', 'three']})  # make some data
        >>> pickle.dump(d, open(filepath, 'wb'), )  # save the data in the filepath
        >>> obj_source = LocalFileObjSource.for_kind(path_format='', kind='pickle')  # make an obj_source for pickles
        >>> assert all(d == obj_source[filepath])  # get the data in filepath and assert it's the same as the saved
        """
        contents_of_file = mk_file_reader_func(kind=kind, **kwargs)
        return cls(path_format, contents_of_file)

    def is_valid_key(self, k):
        return bool(self._path_match_re.match(k))

    def __iter__(self):
        return filter(self.is_valid_key, filtered_iter_filepaths_in_folder_recursively(self._rootdir))
        # return filter(os.path.isfile, iglob('{}/*'.format(self._rootdir)))

    def __contains__(self, k):  # override abstract version, which is not as efficient
        return self.is_valid_key(k) and os.path.isfile(k)

    def __len__(self):
        count = 0
        for _ in self.__iter__():
            count += 1
        return count

    def __getitem__(self, k):
        try:
            return self._contents_of_file(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(e.__class__.__name__, k, e))


class LocalFileObjSourceWithCachedKeys(LocalFileObjSource):
    def __init__(self):
        pass
