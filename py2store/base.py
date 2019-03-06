"""
Base classes for making stores.
In the language of the collections.abc module, a store is a MutableMapping that is configured to work with a specific
representation of keys, serialization of objects (python values), and persistence of the serialized data.

That is, stores offer the same interface as a dict, but where the actual implementation of writes, reads, and listing
are configurable.

Consider the following example. You're store is meant to store waveforms as wav files on a remote server.
Say waveforms are represented in python as a tuple (wf, sr), where wf is a list of numbers and sr is the sample
rate, an int). The __setitem__ method will specify how to store bytes on a remote server, but you'll need to specify
how to SERIALIZE (wf, sr) to the bytes that constitute that wav file: _data_of_obj specifies that.
You might also want to read those wav files back into a python (wf, sr) tuple. The __getitem__ method will get
you those bytes from the server, but the store will need to know how to DESERIALIZE those bytes back into a python
object: _obj_of_data specifies that

Further, say you're storing these .wav files in /some/folder/on/the/server/, but you don't want the store to use
these as the keys. For one, it's annoying to type and harder to read. But more importantly, it's an irrelevant
implementation detail that shouldn't be exposed. THe _id_of_key and _key_of_id pair are what allow you to
add this key interface layer.

These key converters object serialization methods default to the identity (i.e. they return the input as is).
This means that you don't have to implement these as all, and can choose to implement these concerns within
the storage methods themselves.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping, MutableMapping, Container
from py2store.errors import KeyValidationError, OverWritesNotAllowedError, \
    ReadsNotAllowed, WritesNotAllowed, DeletionsNotAllowed, IterationNotAllowed


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


class KeysWrap(metaclass=ABCMeta):
    """
    An ABC providing key conversion.
        _id_of_key(self, k): specifies how to convert incoming keys.
            Maps an interface identifier (key) to an internal identifier (_id) that is actually used to perform
            operations. Can also perform validation and permission checks.
        _key_of_id(self, _id): specifies how to convert outgoing keys (called _ids to distinguish from k)

    Note: It's expected, but not enforced, that _id_of_key and _key_of_id are inverse of each other.
    If this is not the case, strange things could happen.

    _id_of_key will be called by:	__getitem__	    __setitem__	    __delitem__
    _key_of_id will be called by:				                                    __iter__
    """
    __slots__ = ()

    @abstractmethod
    def _id_of_key(self, k):
        """
        Maps an interface identifier (key) to an internal identifier (_id) that is actually used to perform operations.
        Can also perform validation and permission checks.
        :param k: interface identifier of some data
        :return: internal identifier _id
        """
        pass

    @abstractmethod
    def _key_of_id(self, k):
        """
        The inverse of _id_of_key. Maps an internal identifier (_id) to an interface identifier (key)
        :param _id:
        :return:
        """
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is KeysWrap:
            return _check_methods(C, "_id_of_key", "_key_of_id")
        return NotImplemented


class ValsWrap(metaclass=ABCMeta):
    """
    An ABC providing value conversion. Intended to be used for serialization/deserialization.
        _data_of_obj(self, v): serialize: convert incoming object to data (data is what's given to __setitem__ to store)
        _obj_of_data(self, data): deserialize: convert incoming data to object (data is what's returned by __getitem__)

    Note: It's desirable to have _data_of_obj and _obj_of_data be inverse of eachother.
    Unlike with KeysWrap (_id_of_key and _key_of_id), it is not as crucial for the well functioning of stores.
    If serialization and deserialization are not inverse of each other, it just means that the object you get back
    is not the same as the one you stored. Which may be exactly what is desired sometimes.

    _data_of_obj will be called by:	                __setitem__
    _obj_of_data will be called by:	__getitem__
    """
    __slots__ = ()

    @abstractmethod
    def _data_of_obj(self, k):
        """
        Serialization of a python object.
        :param v: A python object.
        :return: The serialization of this object, in a format that can be stored by super().__getitem__
        """
        pass

    @abstractmethod
    def _obj_of_data(self, k):
        """
        Deserialization. Often the inverse of _data_of_obj.
        :param data: Serialized data.
        :return: The python object corresponding to this data.
        """
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is ValsWrap:
            return _check_methods(C, "_data_of_obj", "_obj_of_data")
        return NotImplemented


class IdentityKeysWrap(KeysWrap):
    """Transparent KeysWrap. Often placed in the mro to satisfy the KeysWrap need in a neutral way.
    This is useful in cases where the keys the persistence functions work with are the same as those you want to work
    with.
    """
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


class IdentityValsWrap:
    """ Transparent ValsWrap. Often placed in the mro to satisfy the KeysWrap need in a neutral way.
        This is useful in cases where the values can be persisted by __setitem__ as is (or the serialization is
        handled somewhere in the __setitem__ method.
    """
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


class IdentityKvWrap(IdentityKeysWrap, IdentityValsWrap):
    """Transparent Keys and Vals Wrap"""
    pass


class DfltWrapper(KeysWrap, ValsWrap):
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


class StoreBase:
    """Mixin that intercepts base store methods, transforming the keys and values involved.

    By store we mean key-value store. This could be files in a filesystem, objects in s3, or a database. Where and
    how the content is stored should be specified, but StoreInterface offers a dict-like interface to this.

    StoreBase provides an interface to create storage functionality, but no actual storage capabilities on
    it's own. A concrete Store must be provided by extending StoreInterface to specify the concrete storage
    functionality. Typically in the form:
        class ConcreteStore(StoreBase, ConcreteStorageSpec, Mixins...):
            pass

    ConcreteStorageSpec (or whatever classes follow StoreInterface in the mro) should specify at least four methods:
        __getitem__(self, k): How to get an item keyed by k
        __setitem__(self, k, v): How to store an object v under k
        __delitem__(self, k): How to delete the object under k
        __iter__(self): How to list (i.e. get an iterator of) all keys of the store

    Note: StoreInterface forwards the work to later mro classes.
    If any of these methods are not found, an AttributeError will be raised.
    To raise a specific OperationNotAllowed error instead, you can use StoreLeaf (placed, in the mro, after the
    definitions of the desired implemented methods.

    __getitem__ calls: _id_of_key			                    _obj_of_data
    __setitem__ calls: _id_of_key		        _data_of_obj
    __delitem__ calls: _id_of_key
    __iter__    calls:	            _key_of_id
    """

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

    def __contains__(self, k):
        return super().__contains__(self._id_of_key(k))


class StoreLeaf:
    """Meant to be placed at the end of the mro to raise more meaningful errors when a base method wasn't defined"""
    def __getitem__(self, k):
        raise ReadsNotAllowed("You can't read with that Store")

    def __setitem__(self, k, v):
        raise WritesNotAllowed("You can't write with that Store")

    def __delitem__(self, k):
        raise DeletionsNotAllowed("You can't delete with that Store")

    def __iter__(self):
        raise IterationNotAllowed("You can't iterate with that Store")

    def __contains__(self, k):
        return NotImplementedError("__contains__ (i.e. what gives you 'x in X' functionality) wasn't implemented")


########################################################################################################################
# Mixins to insert specific collection methods in stores

class GetBasedContainer:
    def __contains__(self, k) -> bool:
        """
        Check if collection of keys contains k.
        Note: This method actually fetches the contents for k, returning False if there's a key error trying to do so
        Therefore it may not be efficient, and in most cases, a method specific to the case should be used.
        :return: True if k is in the collection, and False if not
        """
        try:
            self.__getitem__(k)
            return True
        except KeyError:
            return False


class IterBasedContainer:
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


class IterBasedSized:
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


class IterBasedSizedContainer(IterBasedSized, IterBasedContainer):
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
    pass


class FilteredKeys:
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


class StoreMapping(Mapping):
    pass


class StoreMutableMapping(MutableMapping):
    def clear(self):
        raise DeletionsNotAllowed("Bulk deletes not allowed.")


# TODO: Would this need better be served by a (class or object) decorator?
class OverWritesNotAllowed:
    def __setitem__(self, k, v):
        if self.__contains__(k):
            raise OverWritesNotAllowedError(
                "key {} already exists and cannot be overwritten. "
                "If you really want to write to that key, delete it before writing".format(k))
        super().__setitem__(k, v)


# Note: Not sure I want to do key validation this way. Perhaps better injected in _id_of_key?
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
        if cls is KeyValidation:
            return _check_methods(C, "is_valid_key", "check_key_is_valid")
        return NotImplemented



