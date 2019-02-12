import abc
from typing import Any, Callable
from i2i.py2store import Path, Obj, Data


class PathOf(object):
    """Template of a PathOf class"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __call__(self, key):
        raise NotImplementedError("This method needs to be implemented")

    @abc.abstractmethod
    def key_of(self, path):
        raise NotImplementedError("This method needs to be implemented")

class IdentityPathOf(PathOf):
    def __call__(self, key):
        return key

    def key_of(self, path):
        return path


class KeyValPersister(object):
    """
    The interface for a data store. A data store provides key-value persistence functionality.
    The base interface provides the following basic methods:
    :param dump: A method that saves something (first argument) somewhere (second argument)
    :param load: A method that loads something (the return value) from somewhere (the unique argument)
    :param delete: A method that deletes the item saved under a given path
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def dump(self, val, key):
        raise NotImplementedError

    @abc.abstractmethod
    def load(self, key):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, key):
        raise NotImplementedError

    # :param __iter__: A method that lists (iteratively) the paths that the store contains.
    # @abc.abstractmethod
    # def __iter__(self):
    #     """Iterate over item references (paths)"""
    #     raise NotImplementedError


# from i2i.pymint import name_of_obj
# from i2i.core import inject_method
#
# def mk_data_store(dump, load, delete, __iter__):
#     data_store = KeyValPersister()
#     dump
#     # merge args and kwargs to a single kwargs (using name of arguments of args as the keys)
#     kwargs = dict(kwargs,
#                   **{method_name: method_func for method_name, method_func in zip(map(name_of_obj, args), args)})
#     data_store = KeyValPersister()
#     for method_name, method_func in kwargs.items():
#         inject_method(data_store, method_func, method_name)
#     return data_store


class ObjStore(object):
    """
    A class that implements object storage. Usually for objects of a specific type at a specific location.
    The object store is defined by the specification of how to resolve a path (full location specification) from
    a specification of a location, how to serialize/deserialize an object, and how to dump/load
    these serializations.

    This class is meant to be used in situations where a program needs to store and load various resources, and may
    need to handle different resources in different ways, or keep the interface of storage abstract enough to be
    able to be changed easily. The suggested use is to define an ObjStore for each.
    In most situations, several types of resources are needed. In this case, it is suggested that one make an obj store
    for each type of objects.

    For ease of flexibility and adaptation three following concerns are separated:
        * resolving a path to a location: path_of
        * object serialization/deserialization: data_of_obj, obj_of_data
        * serialized object save/load: dump_serial, load_serial

    Other concerns can be inject through decorators.
    """

    def __init__(self,
                 persister: KeyValPersister,
                 path_of: PathOf = IdentityPathOf(),
                 data_of_obj: Callable[[Obj], Data] = lambda obj: obj,
                 obj_of_data: Callable[[Data], Obj] = lambda data: data):
        """
        Construct an ObjStore instance.
        :param persister: A KeyValPersister object (which should contain dump, load, and delete methods
        :param path_of: A function that resolves a specification (in any form) of a resource) to a path
            (a full specification of the location of the resource, which is used by dump_data and load_serial)
        :param data_of_obj: A function that transforms an obj into something (a serial) that can be stored
        :param obj_of_data: A function that can reconstruct an obj from a serial
        """
        self.persister = persister
        self.path_of = path_of
        self.data_of_obj = data_of_obj
        self.obj_of_data = obj_of_data

    def dump(self, obj, key):
        return self.persister.dump(self.data_of_obj(obj), self.path_of(key))

    def load(self, key):
        return self.persister.load(self.path_of(key))

    def delete(self, key):
        return self.persister.delete(self.path_of(key))

    def __iter__(self, *args, **kwargs):
        return map(self.path_of.key_of, self.persister.__iter__(*args, **kwargs))


class InMemoryKeyValPersister(KeyValPersister):
    def __init__(self):
        self._d = dict()

    def dump(self, data, path):
        self._d[path] = data

    def load(self, path):
        return self._d[path]

    def delete(self, path):
        del self._d[path]

    def __iter__(self):
        return self._d.keys()


def mk_in_memory_obj_store():
    """
    Make an ObjStore instance with an InMemoryKeyValPersister.

    >>> obj_store = mk_in_memory_obj_store()
    >>>
    >>> obj_store.dump(3, 'three')
    >>> obj_store.dump([1, 2, 3], 'a list')
    >>> [x for x in obj_store]
    ['three', 'a list']
    >>> obj_store.load('three')
    3
    >>> obj_store.dump(obj='not 3 any more!', key='three')
    >>> obj_store.load('three')
    'not 3 any more!'
    >>> obj_store.load('a list')
    [1, 2, 3]
    >>> obj_store.delete('a list')
    >>> try:
    ...     obj_store.load('a list')
    ... except Exception as err:
    ...     print("{}: {}".format(type(err), err))
    <class 'KeyError'>: 'a list'
    """
    persister = InMemoryKeyValPersister()
    return ObjStore(persister=persister,
                    path_of=IdentityPathOf(),
                    data_of_obj=lambda obj: obj,
                    obj_of_data=lambda data: data)


# TODO: Make object validation and dump_only_if_does_not_exist decorators
# def add_obj_validation(obj_store, obj_validaton: Union[Callable[[Obj], bool], None]):
#     """
#     Add object validation (before serialization) to obj_store.
#     :param obj_store: a ObjStore instance
#     :param obj_is_valid: None, or a boolean function that returns True iff the object is valid (meaning that the
#     ObjStore instance is designed to work with it). If non-None, obj_is_valid will be called on the obj before
#     any attempt of serialization and storing is done. This allows object stores to avoid handling objects is
#     was not meant to handle.
#     :return:
#     """
#
#     def modifier(func):
#         @wraps(func)
#         def wrapper(self, *args, **kwargs):
#             # self is an instance of the class
#             self.data
#             return func(self, *args, **kwargs)
#
#         return wrapper

