from glob import iglob
import os
import re
from typing import Callable, Union, Any
import soundfile as sf  # TODO: Replace by another wav reader, and move to another module

from py2store.base import AbstractKeys, AbstractObjSource
from py2store.parse_format import match_re_for_fstring

from py2store.base import KeyValidation

file_sep = os.path.sep


########################################################################################################################
# File system navigation


def pattern_filter(pattern):
    pattern = re.compile(pattern)

    def _pattern_filter(s):
        return pattern.match(s) is not None

    return _pattern_filter


def iter_relative_files_and_folder(root_folder):
    if not root_folder.endswith(file_sep):
        root_folder += file_sep
    return map(lambda x: x.replace(root_folder, ''), iglob(root_folder + '*'))


def iter_filepaths_in_folder(root_folder):
    return (os.path.join(root_folder, name) for name in iter_relative_files_and_folder(root_folder))


def iter_filepaths_in_folder_recursively(root_folder, filt: Union[str, Callable] = None):
    if not callable(filt):
        if filt is None:
            filt = lambda x: True
        else:  # isinstance(filt, str):
            filt = pattern_filter(filt)

    for full_path in iter_filepaths_in_folder(root_folder):
        if os.path.isdir(full_path):
            for entry in iter_filepaths_in_folder_recursively(full_path, filt):
                yield entry
        else:
            if os.path.isfile(full_path):
                if filt(full_path):
                    yield full_path


########################################################################################################################
# LocalFile Daccs
class PrefixValidation(KeyValidation):
    def __init__(self, _prefix=''):
        self._prefix = _prefix

    def is_valid_key(self, k):
        return k.startswith(self._prefix)

#
# class LocalPathKeys(AbstractKeys):
#     """
#     A S3BucketDacc collection.
#     A collection is a iterable and sizable container.
#     That is, this mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)) to S3BucketDacc.
#     """
#
#     def __iter__(self):
#         yield k from iter_filepaths_in_folder_recursively(self.prefix_)
#
#     def __contains__(self, k):
#         """
#         Check if file path exists
#         :param k: A path to search for
#         :return: True if k exists, False if not
#         """
#         return os.path.isfile(k)


class S3BucketKeys(AbstractKeys, S3BucketDacc):
    """
    A S3BucketDacc collection.
    A collection is a iterable and sizable container.
    That is, this mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)) to S3BucketDacc.
    """

    def __iter__(self, prefix=None):
        if prefix is None:  # NOTE: I hesitate whether to give control over prefix at iteration time or not
            prefix = self._prefix
        return (x.key for x in self._s3_bucket.objects.filter(Prefix=prefix))

    def __contains__(self, k):
        """
        Check if key exists
        :param k: A key to search for
        :return: True if k exists, False if not
        """
        # TODO: s3_client.head_object(Bucket=dacc.bucket_name, Key=k) slightly more efficient but needs boto3.client
        self.check_key_is_valid(k)
        try:
            self._obj_of_key(k).load()
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise
        else:
            return True

    # def __len__(self, k):  # TODO: Is there a s3 specific more efficient way of doing __len__?
    #     pass


class S3BucketReader(AbstractObjReader, S3BucketDacc):
    """ Adds a __getitem__ to S3BucketDacc, which returns a bucket's object binary data for a key."""

    def __getitem__(self, k):
        return self._obj_of_key(k).get()['Body'].read()


class S3BucketSource(AbstractObjSource, S3BucketKeys, S3BucketReader):
    """
    A S3BucketDacc mapping (i.e. a collection (iterable, sizable container) that has a reader (__getitem__),
    and mapping mixin methods such as get, keys, items, values, __eq__ and __ne__.
    """
    pass


class S3BucketWriter(AbstractObjWriter, S3BucketDacc):
    """ A S3BucketDacc that can write to s3 and delete keys (and data) """

    def __setitem__(self, k, v):
        """
        Write data to s3 key.
        Method will check if key is valid before writing data to it,
        but will not check if data is already stored there.
        This means that any data previously stored at the key's location will be lost.
        :param k: s3 key
        :param v: data to write
        :return: None
        """
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        self.check_key_is_valid(k)
        self._obj_of_key(k).put(Body=v)

    def __delitem__(self, k):
        """
        Delete data stored at key k.
        Method will check if key is valid before deleting its data.
        :param k:
        :return:
        """
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        self.check_key_is_valid(k)
        self._obj_of_key(k).delete()


class S3BucketWriterNoOverwrites(S3BucketWriter, OverWritesNotAllowed):
    """
    Exactly like S3BucketWriter, but where writes to an already existing key are protected.
    If a key already exists, __setitem__ will raise a OverWritesNotAllowedError
    """
    pass


class S3BucketWriterIfNotWrittenBefore(S3BucketWriter):
    """ A S3BucketDacc that can write to s3 and delete keys (and data) """

    def __setitem__(self, k, v):
        """
        Write data to s3 key, but raise an error if data was already stored
        Method will check if key is valid before writing data to it.
        :param k: s3 key
        :param v: data to write
        :return: None
        """
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        self.check_key_is_valid(k)
        self._obj_of_key(k).put(Body=v)


class S3BucketStore(AbstractObjStore, S3BucketSource, S3BucketWriter):
    """
    A S3BucketDacc MutableMapping.
    That is, a S3BucketDacc that can read and write, as well as iterate
    """
    pass


class S3BucketStoreNoOverwrites(OverWritesNotAllowed, S3BucketStore):
    """
    A S3BucketDacc MutableMapping.
    That is, a S3BucketDacc that can read and write, as well as iterate
    """
    pass



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
        return recursive_file_walk_iterator_with_filepath_filter(
            self._rootdir, filt=self.is_valid_key, return_full_path=True)
        # return filter(os.path.isfile, iglob('{}/*'.format(self._rootdir)))

    def __contains__(self, k):  # override abstract version, which is not as efficient
        return self.is_valid_key(k) and os.path.isfile(k)

    def __len__(self):
        # TODO: Use itertools, or some other means to more quickly count files
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
