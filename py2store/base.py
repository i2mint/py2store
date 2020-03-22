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

from collections.abc import Collection as CollectionABC
from collections.abc import Mapping, MutableMapping
from typing import Any, Iterable, Tuple

Key = Any
Val = Any
Id = Any
Data = Any
Item = Tuple[Key, Val]
KeyIter = Iterable[Key]
ValIter = Iterable[Val]
ItemIter = Iterable[Item]


class Collection(CollectionABC):

    def __contains__(self, x) -> bool:
        """
        Check if collection of keys contains k.
        Note: This method loops through all contents of collection to see if query element exists.
        Therefore it may not be efficient, and in most cases, a method specific to the case should be used.
        :return: True if k is in the collection, and False if not
        """
        for existing_x in self.__iter__():
            if existing_x == x:
                return True
        return False

    def __len__(self) -> int:
        """
        Number of elements in collection of keys.
        Note: This method iterates over all elements of the collection and counts them.
        Therefore it is not efficient, and in most cases should be overridden with a more efficient version.
        :return: The number (int) of elements in the collection of keys.
        """
        # Note: Found that sum(1 for _ in self.__iter__()) was slower for small, slightly faster for big inputs.
        count = 0
        for _ in self.__iter__():
            count += 1
        return count

    def head(self):
        if hasattr(self, 'items'):
            return next(iter(self.items()))
        else:
            return next(iter(self))


KvCollection = Collection  # alias meant for back-compatibility. Would like to deprecated


# def getitem_based_contains(self, x) -> bool:
#     """
#     Check if collection of keys contains k.
#     Note: This method actually fetches the contents for k, returning False if there's a key error trying to do so
#     Therefore it may not be efficient, and in most cases, a method specific to the case should be used.
#     :return: True if k is in the collection, and False if not
#     """
#
#     try:
#         self.__getitem__(k)
#         return True
#     except KeyError:
#         return False


class KvReader(Collection, Mapping):
    """Acts as a Mapping abc, but with default __len__ (implemented by counting keys)
    and head method to get the first (k, v) item of the store"""

    def head(self):
        for k, v in self.items():
            yield k, v


Reader = KvReader  # alias


# TODO: Wishful thinking: Define store type so the type is defined by it's methods, not by subclassing.
class Persister(Reader, MutableMapping):
    """ Acts as a MutableMapping abc, but disabling the clear method, and computing __len__ by counting keys"""

    def clear(self):
        raise NotImplementedError('''
        The clear method was overridden to make dangerous difficult.
        If you really want to delete all your data, you can do so by doing:
            try:
                while True:
                    self.popitem()
            except KeyError:
                pass''')


KvPersister = Persister  # alias with explict name


# TODO: Make identity_func "identifiable". If we use the following one, we can use == to detect it's use,
# TODO: ... but there may be a way to annotate, register, or type any identity function so it can be detected.
def identity_func(x):
    return x


static_identity_method = staticmethod(identity_func)


class NoSuchItem():
    pass


no_such_item = NoSuchItem()


class Store(Persister):
    """
    By store we mean key-value store. This could be files in a filesystem, objects in s3, or a database. Where and
    how the content is stored should be specified, but StoreInterface offers a dict-like interface to this.
    ::
        __getitem__ calls: _id_of_key			                    _obj_of_data
        __setitem__ calls: _id_of_key		        _data_of_obj
        __delitem__ calls: _id_of_key
        __iter__    calls:	            _key_of_id


    >>> # Default store: no key or value conversion ################################################
    >>> s = Store()
    >>> s['foo'] = 33
    >>> s['bar'] = 65
    >>> assert list(s.items()) == [('foo', 33), ('bar', 65)]
    >>> assert list(s.store.items()) == [('foo', 33), ('bar', 65)]  # see that the store contains the same thing
    >>>
    >>> ################################################################################################
    >>> # Now let's make stores that have a key and value conversion layer #############################
    >>> # input keys will be upper cased, and output keys lower cased ##################################
    >>> # input values (assumed int) will be converted to ascii string, and visa versa #################
    >>> ################################################################################################
    >>>
    >>> def test_store(s):
    ...     s['foo'] = 33  # write 33 to 'foo'
    ...     assert 'foo' in s  # __contains__ works
    ...     assert 'no_such_key' not in s  # __nin__ works
    ...     s['bar'] = 65  # write 65 to 'bar'
    ...     assert len(s) == 2  # there are indeed two elements
    ...     assert list(s) == ['foo', 'bar']  # these are the keys
    ...     assert list(s.keys()) == ['foo', 'bar']  # the keys() method works!
    ...     assert list(s.values()) == [33, 65]  # the values() method works!
    ...     assert list(s.items()) == [('foo', 33), ('bar', 65)]  # these are the items
    ...     assert list(s.store.items()) == [('FOO', '!'), ('BAR', 'A')]  # but note the internal representation
    ...     assert s.get('foo') == 33  # the get method works
    ...     assert s.get('no_such_key', 'something') == 'something'  # return a default value
    ...     del(s['foo'])  # you can delete an item given its key
    ...     assert len(s) == 1  # see, only one item left!
    ...     assert list(s.items()) == [('bar', 65)]  # here it is
    >>>
    >>> # We can introduce this conversion layer in several ways. Here's a few... ######################
    >>> # by subclassing ###############################################################################
    >>> class MyStore(Store):
    ...     def _id_of_key(self, k):
    ...         return k.upper()
    ...     def _key_of_id(self, _id):
    ...         return _id.lower()
    ...     def _data_of_obj(self, obj):
    ...         return chr(obj)
    ...     def _obj_of_data(self, data):
    ...         return ord(data)
    >>> s = MyStore(store=dict())  # note that you don't need to specify dict(), since it's the default
    >>> test_store(s)
    >>>
    >>> # by assigning functions to converters ##########################################################
    >>> class MyStore(Store):
    ...     def __init__(self, store, _id_of_key, _key_of_id, _data_of_obj, _obj_of_data):
    ...         super().__init__(store)
    ...         self._id_of_key = _id_of_key
    ...         self._key_of_id = _key_of_id
    ...         self._data_of_obj = _data_of_obj
    ...         self._obj_of_data = _obj_of_data
    ...
    >>> s = MyStore(dict(),
    ...             _id_of_key=lambda k: k.upper(),
    ...             _key_of_id=lambda _id: _id.lower(),
    ...             _data_of_obj=lambda obj: chr(obj),
    ...             _obj_of_data=lambda data: ord(data))
    >>> test_store(s)
    >>>
    >>> # using a Mixin class #############################################################################
    >>> class Mixin:
    ...     def _id_of_key(self, k):
    ...         return k.upper()
    ...     def _key_of_id(self, _id):
    ...         return _id.lower()
    ...     def _data_of_obj(self, obj):
    ...         return chr(obj)
    ...     def _obj_of_data(self, data):
    ...         return ord(data)
    ...
    >>> class MyStore(Mixin, Store):  # note that the Mixin must come before Store in the mro
    ...     pass
    ...
    >>> s = MyStore()  # no dict()? No, because default anyway
    >>> test_store(s)
    >>>
    >>> # adding wrapper methods to an already made Store instance #########################################
    >>> s = Store(dict())
    >>> s._id_of_key=lambda k: k.upper()
    >>> s._key_of_id=lambda _id: _id.lower()
    >>> s._data_of_obj=lambda obj: chr(obj)
    >>> s._obj_of_data=lambda data: ord(data)
    >>> test_store(s)
    """

    # __slots__ = ('_id_of_key', '_key_of_id', '_data_of_obj', '_obj_of_data')

    def __init__(self, store=dict):
        if isinstance(store, type):
            store = store()
        self.store = store

    _id_of_key = static_identity_method
    _key_of_id = static_identity_method
    _data_of_obj = static_identity_method
    _obj_of_data = static_identity_method

    # Read ####################################################################
    def __getitem__(self, k: Key) -> Val:
        return self._obj_of_data(self.store.__getitem__(self._id_of_key(k)))

    def get(self, k: Key, default=None) -> Val:
        if hasattr(self.store, 'get'):  # if store has a get method, use it
            data = self.store.get(self._id_of_key(k), no_such_item)
            if data is not no_such_item:
                return self._obj_of_data(data)
            else:
                return default
        else:  # if not, do the get function otherwise
            if k in self:
                return self._obj_of_data(self[k])
            else:
                return default

    # Explore ####################################################################
    def __iter__(self) -> KeyIter:
        return map(self._key_of_id, self.store.__iter__())

    # def items(self) -> ItemIter:
    #     if hasattr(self.store, 'items'):
    #         yield from ((self._key_of_id(k), self._obj_of_data(v)) for k, v in self.store.items())
    #     else:
    #         yield from ((self._key_of_id(k), self._obj_of_data(self.store[k])) for k in self.store.__iter__())

    def __len__(self) -> int:
        return self.store.__len__()

    def __contains__(self, k) -> bool:
        return self.store.__contains__(self._id_of_key(k))

    def head(self) -> Item:
        try:
            for k in self:
                return k, self[k]
        except Exception as e:

            from warnings import warn
            msg = f"Couldn't get data for the key {k}. This could be be...\n"
            msg += "... because it's not a store (just a collection, that doesn't have a __getitem__)\n"
            msg += "... because there's a layer transforming outcoming keys that are not the ones the store actually " \
                   "uses? If you didn't wrap the store with the inverse ingoing keys transformation, " \
                   "that would happen.\n"
            msg += "I'll ask the inner-layer what it's head is, but IT MAY NOT REFLECT the reality of your store " \
                   "if you have some filtering, caching etc."
            msg += f"The error messages was: \n{e}"
            warn(msg)

            for _id in self.store:
                return self._key_of_id(_id), self._obj_of_data(self.store[_id])
        # NOTE: Old version didn't work when key mapping was asymmetrical
        # for k, v in self.items():
        #     return k, v

    # Write ####################################################################
    def __setitem__(self, k: Key, v: Val):
        return self.store.__setitem__(self._id_of_key(k), self._data_of_obj(v))

    # def update(self, *args, **kwargs):
    #     return self.store.update(*args, **kwargs)

    # Delete ####################################################################
    def __delitem__(self, k: Key):
        return self.store.__delitem__(self._id_of_key(k))

    def clear(self):
        raise NotImplementedError('''
        The clear method was overridden to make dangerous difficult.
        If you really want to delete all your data, you can do so by doing:
            try:
                while True:
                    self.popitem()
            except KeyError:
                pass''')

    # Misc ####################################################################
    def __repr__(self):
        return self.store.__repr__()


KvStore = Store  # alias with explict name


def has_kv_store_interface(o):
    """Check if object has the KvStore interface (that is, has the kv wrapper methods

    Args:
        o: object (class or instance)

    Returns: True if kv has the four key (in/out) and value (in/out) transformation methods

    """
    return hasattr(o, '_id_of_key') and hasattr(o, '_key_of_id') \
           and hasattr(o, '_data_of_obj') and hasattr(o, '_obj_of_data')


from abc import ABCMeta, abstractmethod
from py2store.errors import KeyValidationError


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


# Note: Not sure I want to do key validation this way. Perhaps better injected in _id_of_key?
class KeyValidationABC(metaclass=ABCMeta):
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
        if cls is KeyValidationABC:
            return _check_methods(C, "is_valid_key", "check_key_is_valid")
        return NotImplemented

########################################################################################################################
# Mixins to insert specific collection methods in stores


########################################################################################################################
# TODO: Delete when over with refactor

#
# class StoreMapping(Mapping):
#     pass
#
#
# class StoreMutableMapping(MutableMapping):
#     def clear(self):
#         raise DeletionsNotAllowed("Bulk deletes not allowed.")
