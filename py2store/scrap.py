from abc import ABCMeta, abstractmethod
from typing import Union
from collections.abc import Collection, Mapping, MutableMapping, Container
from py2store.errors import KeyValidationError, OverWritesNotAllowedError


class StoreInterface(MutableMapping):
    def _id_of_key(self, k):
        """
        Maps an interface identifier (key) to an internal identifier (_id) that is actually used to perform operations.
        Can also perform validation and permission checks.
        :param k: interface identifier of some data
        :return: internal identifier _id
        """
        return k

    def _key_of_id(self, _id):
        """
        The inverse of _id_of_key. Maps an internal identifier (_id) to an interface identifier (key)
        :param _id:
        :return:
        """
        return _id

    def _data_of_obj(self, v):
        """
        Serialization of a python object.
        :param v: A python object.
        :return: The serialization of this object, in a format that can be stored by super().__getitem__
        """
        return v

    def _obj_of_data(self, data):
        """
        Deserialization. The inverse of _data_of_obj.
        :param data: Serialized data.
        :return: The python object corresponding to this data.
        """
        return data

    def __getitem__(self, k):
        return self._obj_of_data(super().__getitem__(self._id_of_key(k)))

    def __setitem__(self, k, v):
        return super().__setitem__(self._id_of_key(k), self._data_of_obj(v))

    def __delitem__(self, k):
        return super().__delitem__(self._id_of_key(k))




class Loader:

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


class Dumper:
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

# def _check_methods(C, *methods):
#     """
#     Check that all methods listed are in the __dict__ of C, or in the classes of it's mro.
#     One trick pony borrowed from collections.abc.
#     """
#     mro = C.__mro__
#     for method in methods:
#         for B in mro:
#             if method in B.__dict__:
#                 if B.__dict__[method] is None:
#                     return NotImplemented
#                 break
#         else:
#             return NotImplemented
#     return True


# class Serializer(metaclass=ABCMeta):
#     """
#     An ABC for an object serializer.
#     Single purpose: returning data is meant to be persisted
#     How the object serialized into data to be persisted should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, obj):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Serializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
#
#
# class Deserializer(metaclass=ABCMeta):
#     """
#     An ABC for an object deserializer.
#     Single purpose: returning the object keyed by a requested key k.
#     How the data is deserialized into an object should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, data: bytes):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Deserializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
#
#
# class Persister(metaclass=ABCMeta):
#     """
#     An ABC for an object serializer.
#     Single purpose: returning data is meant to be persisted
#     How the object serialized into data to be persisted should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, obj):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Serializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
#
#
# class Loader(metaclass=ABCMeta):
#     """
#     An ABC for an object deserializer.
#     Single purpose: returning the object keyed by a requested key k.
#     How the data is deserialized into an object should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, data: bytes):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Deserializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
