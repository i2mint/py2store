from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping, MutableMapping


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


class Keys(Collection):
    """
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
        # TODO: Use itertools, or some other means to more quickly count files
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


class ObjReader(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, k):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is ObjReader:
            return _check_methods(C, "__getitem__")
        return NotImplemented


class ObjWriter(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __setitem__(self, k):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is ObjReader:
            return _check_methods(C, "__setitem__")
        return NotImplemented


class ObjSource(Keys, ObjReader, Mapping):
    """
    Interface for an Object Source.
    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
    mixin methods that collections.abc.Mapping adds automatically:
        __contains__, keys, items, values, get, __eq__, and __ne__
    (see https://docs.python.org/3/library/collections.abc.html)

    """
    pass


class ObjStore(ObjSource, ObjWriter, MutableMapping):
    pass
