from typing import Callable, Mapping, Collection

from py2store.core import ExplicitKeys


class ObjLoader(object):
    def __init__(self, data_of_key, obj_of_data=None):
        self.data_of_key = data_of_key
        if obj_of_data is not None or not callable(obj_of_data):
            raise TypeError('serializer must be None or a callable')
        self.obj_of_data = obj_of_data

    def __call__(self, k):
        if self.obj_of_data is not None:
            return self.obj_of_data(self.data_of_key(k))
        else:
            return self.data_of_key(k)


class ObjReader:
    """
    py2store.base.AbstractObjReader implementation that uses a specified function to get the contents for a given key.

    >>> # define a contents_of_key that reads stuff from a dict
    >>> data = {'foo': 'bar', 42: "everything"}
    >>> def read_dict(k):
    ...     return data[k]
    >>> pr = ObjReader(_obj_of_key=read_dict)
    >>> pr['foo']
    'bar'
    >>> pr[42]
    'everything'
    >>>
    >>> # define contents_of_key that reads stuff from a file given it's path
    >>> def read_file(path):
    ...     with open(path) as fp:
    ...         return fp.read()
    >>> pr = ObjReader(_obj_of_key=read_file)
    >>> file_where_this_code_is = __file__  # it should be THIS file you're reading right now!
    >>> print(pr[file_where_this_code_is][:100])  # print the first 100 characters of this file
    from collections.abc import Mapping, Collection
    from typing import Callable
    from py2store.util impor
    """

    def __init__(self, _obj_of_key: Callable):
        self._obj_of_key = _obj_of_key

    @classmethod
    def from_composition(cls, data_of_key, obj_of_data=None):
        return cls(_obj_of_key=ObjLoader(data_of_key=data_of_key, obj_of_data=obj_of_data))

    def __getitem__(self, k):
        try:
            return self._obj_of_key(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(
                e.__class__.__name__, k, e))


class ExplicitKeysSource(ExplicitKeys, ObjReader, Mapping):
    """
    An object source that uses an explicit keys collection and a specified function to read contents for a key.
    """

    def __init__(self, key_collection: Collection, _obj_of_key: Callable):
        """

        :param key_collection: The collection of keys that this source handles
        :param _obj_of_key: The function that returns the contents for a key
        """
        ExplicitKeys.__init__(self, key_collection)
        ObjReader.__init__(self, _obj_of_key)


class ObjDumper(object):
    def __init__(self, save_data_to_key, data_of_obj=None):
        self.save_data_to_key = save_data_to_key
        if data_of_obj is not None or not callable(data_of_obj):
            raise TypeError('serializer must be None or a callable')
        self.data_of_obj = data_of_obj

    def __call__(self, k, v):
        if self.data_of_obj is not None:
            return self.save_data_to_key(k, self.data_of_obj(v))
        else:
            return self.save_data_to_key(k, v)