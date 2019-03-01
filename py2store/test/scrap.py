



########################################################################################################################
# LocalFile Daccs
class PrefixValidationMixin(KeyValidation):
    def is_valid_key(self, k):
        return k.startswith(self._prefix)



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

