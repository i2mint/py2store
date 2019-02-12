from glob import iglob
import os
import re
from typing import Callable, Union, Any
import soundfile as sf  # TODO: Replace by another wav reader, and move to another module
from functools import wraps
from i2i.py2store.obj_source import ObjSource
from i2i.py2store.parse_format import match_re_for_fstring

file_sep = os.path.sep


########################################################################################################################
# File system navigation

def iter_relative_files_and_folder(root_folder):
    if not root_folder.endswith(file_sep):
        root_folder += file_sep
    return map(lambda x: x.replace(root_folder, ''), iglob(root_folder + '*'))


def pattern_filter(pattern):
    pattern = re.compile(pattern)

    def _pattern_filter(s):
        return pattern.match(s) is not None

    return _pattern_filter


def recursive_file_walk_iterator_with_filepath_filter(root_folder,
                                                      filt: Union[str, Callable] = None,
                                                      return_full_path=True):
    if not callable(filt):
        if filt is None:
            filt = lambda x: x
        else:  # isinstance(filt, str):
            filt = pattern_filter(filt)
    for name in iter_relative_files_and_folder(root_folder):
        full_path = os.path.join(root_folder, name)
        if os.path.isdir(full_path):
            for entry in recursive_file_walk_iterator_with_filepath_filter(full_path, filt, return_full_path):
                yield entry
        else:
            if os.path.isfile(full_path):
                if filt(full_path):
                    if return_full_path:
                        yield full_path
                    else:
                        yield name


########################################################################################################################
# File readers

def _mk_file_reader_for_dflt(mode='r', **kwargs):
    """
    Makes a function that reads a json file, returning a dict.

    Signature is that of builtin open function.
    """

    def contents_of_file(filepath):
        """Reads a file.
        Generated from _mk_file_reader_for_dflt"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        with open(filepath, mode=mode, **kwargs) as fp:
            return fp.read()

    return contents_of_file


# @wraps(sf.read)
def _mk_file_reader_for_wav(dtype='int16', wf_only=True, assert_sr=None, **kwargs):
    """
    Makes a function that reads a wav file, returning a waveform (if wf_only=True) or a
    (waveform, samplerate) pair (if wf_only=False), asserting that the samplerate is equal to assert_sr, if given.
    By default, the dtype of the numpy array returned is int16, unless otherwise specified.
    All other kwargs are those from the signature of soundfile.read function, pasted below.
    """
    if assert_sr is not None:
        assert isinstance(assert_sr, int), "assert_sr must be an int"

    def contents_of_file(filepath):
        """Reads a wav file.
        Generated from _mk_file_reader_for_wav"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        wf, sr = sf.read(filepath, dtype=dtype, **kwargs)
        if assert_sr is not None:
            assert sr == assert_sr, "Sample rate must be {} (was {})".format(assert_sr, sr)
        if wf_only:
            return wf
        else:
            return wf, sr

    return contents_of_file


def _mk_file_read_for_json(open_kwargs=None, cls=None, object_hook=None, parse_float=None,
                           parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    """
    Makes a function that reads a json file, returning a dict.

    Signature is that of json.load.
    """
    import json

    if open_kwargs is None:
        open_kwargs = dict(mode='r', buffering=-1, encoding=None,
                           errors=None, newline=None, closefd=True, opener=None)
    def contents_of_file(filepath):
        """Reads a json file.
        Generated from _mk_file_read_for_json"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        return json.load(open(filepath, **open_kwargs),
                         cls=cls, object_hook=object_hook, parse_float=parse_float,
                         parse_int=parse_int, parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)

    return contents_of_file


def _mk_file_read_for_pickle(open_kwargs=None, fix_imports=True, encoding='ASCII', errors='strict'):
    """Makes a function that reads a pickle file, returning a python object.

    Signature is that of pickle.load, pasted below:

    {}
    """

    import pickle

    if open_kwargs is None:
        open_kwargs = dict(mode='rb', buffering=-1, encoding=None,
                           errors=None, newline=None, closefd=True, opener=None)
    def contents_of_file(filepath):
        """Reads a pickle file.
        Generated from _mk_file_read_for_pickle"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        return pickle.load(open(filepath, **open_kwargs),
                           fix_imports=fix_imports, encoding=encoding, errors=errors)

    return contents_of_file


_file_reader_for_kind = {
    'dflt': _mk_file_reader_for_dflt,
    'wav': _mk_file_reader_for_wav,  # TODO: Deprecate and use wav_wf instead
    'wav_wf': _mk_file_reader_for_wav,
    'json': _mk_file_read_for_json,
    'pickle': _mk_file_read_for_pickle
}


def mk_file_reader_func(kind: str = 'dflt', **kwargs):
    if kind is None:
        print("Possible kinds: {}".format(', '.join(_file_reader_for_kind)))
        return None
    return _file_reader_for_kind[kind](**kwargs)


########################################################################################################################
# LocalFileObjSource

dflt_contents_of_file = mk_file_reader_func(kind='dflt')


class LocalFileObjSource(ObjSource):
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

    def __getitem__(self, k):
        try:
            return self._contents_of_file(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(e.__class__.__name__, k, e))

    def __len__(self):
        # TODO: Use itertools, or some other means to more quickly count files
        count = 0
        for _ in self.__iter__():
            count += 1
        return count

    def __iter__(self):
        return recursive_file_walk_iterator_with_filepath_filter(
            self._rootdir, filt=self.is_valid_key, return_full_path=True)
        # return filter(os.path.isfile, iglob('{}/*'.format(self._rootdir)))

    def __contains__(self, k):  # override abstract version, which is not as efficient
        return self.is_valid_key(k) and os.path.isfile(k)
