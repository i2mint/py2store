from abc import ABCMeta, abstractmethod
from typing import Union
from collections.abc import Collection, Mapping, MutableMapping, Container
from py2store.errors import KeyValidationError, OverWritesNotAllowedError


def _check_methods(C, *methods):
    """
    Check that all methods listed are in the __dict__ of C, or in the classes of it's mro.
    One trick pony borrowed from collections.abc.
    """
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        else:
            return NotImplemented
    return True


class StoreInterface:

    ####################################################################################################################
    # Default interface methods

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

    ####################################################################################################################
    # Interface CRUD method (that depend on some definition of the "internal" methods pointed to by super)

    def __getitem__(self, k):
        return self._obj_of_data(super().__getitem__(self._id_of_key(k)))

    def __setitem__(self, k, v):
        return super().__setitem__(self._id_of_key(k), self._data_of_obj(v))

    def __delitem__(self, k):
        return super().__delitem__(self._id_of_key(k))

    def __iter__(self):
        return map(self._key_of_id, super().__iter__())

    ####################################################################################################################
    # Default __len__ and __contains__ (that depend on the definition of an __iter__)

    def __len__(self) -> int:
        """
        Number of elements in collection of keys.
        Note: This method iterates over all elements of the collection and counts them.
        Therefore it is not efficient, and in most cases should be overridden with a more efficient version.
        :return: The number (int) of elements in the collection of keys.
        """
        # TODO: some other means to more quickly count files?
        # Note: Found that sum(1 for _ in self.__iter__()) was slower for small, slightly faster for big inputs.
        count = 0
        for _ in self.__iter__():
            count += 1
        return count

    def __contains__(self, k) -> bool:
        """
        Check if collection of keys contains k.
        Note: This method iterates over all elements of the collection to check if k is present.
        Therefore it is not efficient, and in most cases should be overridden with a more efficient version.
        :return: True if k is in the collection, and False if not
        """
        for collection_key in self.__iter__():
            if collection_key == k:
                return True
        return False  # return False if the key wasn't found


class AbstractKeys(Collection):
    """
    An ABC that defines
        (a) how to iterate over a collection of elements (keys) (__iter__)
        (b) check that a key is contained in the collection (__contains__), and
        (c) how to get the number of elements in the collection
    This is exactly what the collections.abc.Collection (from which Keys inherits) does.
    The difference here, besides the "Keys" purpose-explicit name, is that Keys offers default
     __len__ and __contains__  definitions based on what ever __iter__ the concrete class defines.

    Keys is a collection (i.e. a Sized (has __len__), Iterable (has __iter__), Container (has __contains__).
    It's purpose is to serve as a collection of object identifiers in a key->obj mapping.
    The Keys class doesn't implement __iter__ (so needs to be subclassed with a concrete class), but
    offers mixin __len__ and __contains__ methods based on a given __iter__ method.
    Note that usually __len__ and __contains__ should be overridden to more, context-dependent, efficient methods.
    """

    def __len__(self) -> int:
        """
        Number of elements in collection of keys.
        Note: This method iterates over all elements of the collection and counts them.
        Therefore it is not efficient, and in most cases should be overridden with a more efficient version.
        :return: The number (int) of elements in the collection of keys.
        """
        # TODO: some other means to more quickly count files?
        # Note: Found that sum(1 for _ in self.__iter__()) was slower for small, slightly faster for big inputs.
        count = 0
        for _ in self.__iter__():
            count += 1
        return count

    def __contains__(self, k) -> bool:
        """
        Check if collection of keys contains k.
        Note: This method iterates over all elements of the collection to check if k is present.
        Therefore it is not efficient, and in most cases should be overridden with a more efficient version.
        :return: True if k is in the collection, and False if not
        """
        for collection_key in self.__iter__():
            if collection_key == k:
                return True
        return False  # return False if the key wasn't found


class FilteredKeys(AbstractKeys):
    """
    Filters __iter__ and __contains__ with (the boolean filter function attribute) _key_filt.
    """

    def __iter__(self):
        return filter(self._key_filt, super().__iter__())

    def __contains__(self, k) -> bool:
        """
        Check if collection of keys contains k.
        Note: This method iterates over all elements of the collection to check if k is present.
        Therefore it is not efficient, and in most cases should be overridden with a more efficient version.
        :return: True if k is in the collection, and False if not
        """
        return self._key_filt(k) and super().__contains__(k)




class AbstractObjReader(metaclass=ABCMeta):
    """
    An ABC for an object reader.
    Single purpose: returning the object keyed by a requested key k.
    How the data is retrieved and deserialized into an object should be defined in a concrete subclass.
    """
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, k):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractObjReader:
            return _check_methods(C, "__getitem__")
        return NotImplemented


class AbstractObjWriter(metaclass=ABCMeta):
    """
    An ABC for an object writer.
    Single purpose: store an object under a given key.
    How the object is serialized and or physically stored should be defined in a concrete subclass.
    """
    __slots__ = ()

    @abstractmethod
    def __setitem__(self, k, v):
        pass

    @abstractmethod
    def __delitem__(self, k):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractObjWriter:
            return _check_methods(C, "__setitem__", "__delitem__")
        return NotImplemented


class AbstractObjSource(AbstractKeys, AbstractObjReader, Mapping):
    """
    Interface for an Object Source.
    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
    mixin methods that collections.abc.Mapping adds automatically:
        __contains__, keys, items, values, get, __eq__, and __ne__
    (see https://docs.python.org/3/library/collections.abc.html)

    """
    pass


class AbstractObjStore(AbstractObjSource, AbstractObjWriter, MutableMapping):
    def clear(self):
        """
        clear method was removed from MutableMapping subclass for safety reasons (too easy to delete all data).
        It can easily be added back in situations where a blankey "delete everything" method it is desired.
        Alternatively, one can loop over all keys() and use __delitem__(k) on them, if deleting all data is desired.
        """
        raise NotImplementedError("clear method was removed from MutableMapping subclass for safety reasons")


class KeyValidation(metaclass=ABCMeta):
    """
    An ABC for an object writer.
    Single purpose: store an object under a given key.
    How the object is serialized and or physically stored should be defined in a concrete subclass.
    """
    __slots__ = ()

    @abstractmethod
    def is_valid_key(self, k):
        pass

    def check_key_is_valid(self, k):
        if not self.is_valid_key(k):
            raise KeyValidationError("key is not valid: {}".format(k))

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractObjWriter:
            return _check_methods(C, "is_valid_key", "check_key_is_valid")
        return NotImplemented


# TODO: Would this need better be served by a (class or object) decorator?
class OverWritesNotAllowed:
    def __setitem__(self: Union[AbstractObjWriter, Container], k, v):
        if self.__contains__(k):
            raise OverWritesNotAllowedError(
                "key {} already exists and cannot be overwritten. "
                "If you really want to write to that key, delete it before writing".format(k))
        super().__setitem__(k, v)
