from functools import wraps
import types
from py2store.base import has_kv_store_interface, Store


def cache_iter(collection_cls, iter_to_container=list, name=None):
    """Make a class that wraps input class's __iter__ becomes cached.

    Quite often we have a lot of keys, that we get from a remote data source, and don't want to have to ask for
    them again and again, having them be fetched, sent over the network, etc.
    So we need caching.

    But this caching is not the typical read caching, since it's __iter__ we want to cache, and that's a generator.
    So we'll implement a store class decorator specialized for this.

    The following decorator, when applied to a class (that has an __iter__), will perform the __iter__ code, consuming
    all items of the generator and storing them in _iter_cache, and then will yield from there every subsequent call.

    If you need to refresh the cache, you'll need to delete _iter_cache (or set to None). Most of the time though,
    you'll be applying this caching decorator to static data.

    Args:
        collection_cls: The class to wrap (must have an __iter__)
        iter_to_container: The function that will be applied to existing __iter__() and assigned to cache.
            The default is list. Another useful one is the sorted function.
        name: The name of the new class

    The ex
    >>> @cache_iter
    ... class A:
    ...     def __iter__(self):
    ...         yield from [1, 2, 3]
    >>> # Note, could have also used this form: AA = cache_iter(A)
    >>> a = A()
    >>> list(a)
    [1, 2, 3]
    >>> a._iter_cache = ['a', 'b', 'c']  # changing the cache, to prove that subsequent listing will read from there
    >>> list(a)  # proof:
    ['a', 'b', 'c']
    """
    name = name or 'IterCached' + collection_cls.__name__
    cached_cls = type(name, (collection_cls,), {'_iter_cache': None})

    def __iter__(self):
        if getattr(self, '_iter_cache', None) is None:
            self._iter_cache = iter_to_container(super(cached_cls, self).__iter__())
        yield from self._iter_cache

    cached_cls.__iter__ = __iter__

    return cached_cls


def kv_wrap_persister_cls(persister_cls, name=None):
    """Make a class that wraps a persister into a py2store.base.Store,

    Args:
        persister_cls: The persister class to wrap

    Returns: A Store wrapping the persister (see py2store.base)

    >>> A = kv_wrap_persister_cls(dict)
    >>> a = A()
    >>> a['one'] = 1
    >>> a['two'] = 2
    >>> a['three'] = 3
    >>> list(a.items())
    [('one', 1), ('two', 2), ('three', 3)]
    >>> A  # looks like a dict, but is not:
    <class 'abc.Wrappeddict'>
    >>> assert hasattr(a, '_obj_of_data')  # for example, it has this magic method
    >>> # If you overwrite the _obj_of_data method, you'll transform outcomming values with it.
    >>> # For example, say the data you stored were minutes, but you want to get then in secs...
    >>> a._obj_of_data = lambda data: data * 60
    >>> list(a.items())
    [('one', 60), ('two', 120), ('three', 180)]
    >>>
    >>> # And if you want to have class that has this weird "store minutes, retrieve seconds", you can do this:
    >>> class B(kv_wrap_persister_cls(dict)):
    ...     def _obj_of_data(self, data):
    ...         return data * 60
    >>> b = B()
    >>> b.update({'one': 1, 'two': 2, 'three': 3})  # you can write several key-value pairs at once this way!
    >>> list(b.items())
    [('one', 60), ('two', 120), ('three', 180)]
    >>> # Warning! Advanced under-the-hood chat coming up.... Note this:
    >>> print(b)
    {'one': 1, 'two': 2, 'three': 3}
    >>> # What?!? Well, remember, printing an object calls the objects __str__, which usually calls __repr__
    >>> # The wrapper doesn't wrap those methods, since they don't have consistent behaviors.
    >>> # Here you're getting the __repr__ of the underlying dict store, without the key and value transforms.
    >>>
    >>> # Say you wanted to transform the incoming minute-unit data, converting to secs BEFORE they were stored...
    >>> class C(kv_wrap_persister_cls(dict)):
    ...     def _data_of_obj(self, obj):
    ...         return obj * 60
    >>> c = C()
    >>> c.update(one=1, two=2, three=3)  # yet another way you can write multiple key-vals at once
    >>> list(c.items())
    [('one', 60), ('two', 120), ('three', 180)]
    >>> print(c)  # but notice that unlike when we printed b, here the stored data is actually transformed!
    {'one': 60, 'two': 120, 'three': 180}
    >>>
    >>> # Now, just to demonstrate key transformation, let's say that we need internal (stored) keys to be upper case,
    >>> # but external (the keys you see when listed) ones to be lower case, for some reason...
    >>> class D(kv_wrap_persister_cls(dict)):
    ...     _data_of_obj = staticmethod(lambda obj: obj * 60)  # to demonstrated another way of doing this
    ...     _key_of_id = lambda self, _id: _id.lower()  # note if you don't specify staticmethod, 1st arg must be self
    ...     def _id_of_key(self, k):  # a function definition like you're used to
    ...         return k.upper()
    >>> d = D()
    >>> d['oNe'] = 1
    >>> d.update(TwO=2, tHrEE=3)
    >>> list(d.items())  # you see clean lower cased keys at the interface of the store
    [('one', 60), ('two', 120), ('three', 180)]
    >>> # but internally, the keys are all upper case
    >>> print(d)  # equivalent to print(d.store), so keys and values not wrapped (values were transformed before stored)
    {'ONE': 60, 'TWO': 120, 'THREE': 180}
    >>>
    >>> # On the other hand, careful, if you gave the data directly to D, you wouldn't get that.
    >>> d = D({'one': 1, 'two': 2, 'three': 3})
    >>> print(d)
    {'one': 1, 'two': 2, 'three': 3}
    >>> # Thus is because when you construct a D with the dict, it initializes the dicts data with it directly
    >>> # before the key/val transformers are in place to do their jobs.
    """

    name = name or ('Wrapped' + persister_cls.__name__)

    cls = type(name, (Store,), {})

    @wraps(persister_cls.__init__)
    def __init__(self, *args, **kwargs):
        super(cls, self).__init__(persister_cls(*args, **kwargs))

    cls.__init__ = __init__

    return cls


def wrap_kvs(store_cls, name=None, *,
             key_of_id=None, id_of_key=None, obj_of_data=None, data_of_obj=None, postget=None
             ):
    """Make a Store that is wrapped with the given key/val transformers

    Args:
        store_cls:
        name:
        key_of_id:
        id_of_key:
        obj_of_data:
        data_of_obj:
        postget: postget(k, v) function that is called (and output returned) after retrieving the v for k

    Returns:

    >>> def key_of_id(_id):
    ...     return _id.upper()
    >>> def id_of_key(k):
    ...     return k.lower()
    >>> def obj_of_data(data):
    ...     return data - 100
    >>> def data_of_obj(obj):
    ...     return obj + 100
    >>>
    >>> A = wrap_kvs(dict, key_of_id=key_of_id, id_of_key=id_of_key, obj_of_data=obj_of_data, data_of_obj=data_of_obj)
    >>> a = A()
    >>> a['KEY'] = 1
    >>> a  # repr is just the base class (dict) repr, so shows "inside" the store (lower case keys and +100)
    {'key': 101}
    >>> a['key'] = 2
    >>> print(a)  # repr is just the base class (dict) repr, so shows "inside" the store (lower case keys and +100)
    {'key': 102}
    >>> a['kEy'] = 3
    >>> a  # repr is just the base class (dict) repr, so shows "inside" the store (lower case keys and +100)
    {'key': 103}
    >>> list(a)  # but from the point of view of the interface the keys are all upper case
    ['KEY']
    >>> list(a.items())  # and the values are those we put there.
    [('KEY', 3)]
    >>>
    >>> # And now this: Showing how to condition the value transform (like obj_of_data), but conditioned on key.
    >>> B = wrap_kvs(dict, postget=lambda k, v: f'upper {v}' if k[0].isupper() else f'lower {v}')
    >>> b = B()
    >>> b['BIG'] = 'letters'
    >>> b['small'] = 'text'
    >>> list(b.items())
    [('BIG', 'upper letters'), ('small', 'lower text')]
    """
    if not has_kv_store_interface(store_cls):
        store_cls = kv_wrap_persister_cls(store_cls, name=name)
    elif name is not None:
        _store_cls = store_cls
        store_cls = type(name, (_store_cls,), {})  # make a "copy"

    if key_of_id is not None:
        def _key_of_id(self, _id):
            return key_of_id(super(store_cls, self)._key_of_id(_id))

        store_cls._key_of_id = _key_of_id

    if id_of_key is not None:
        def _id_of_key(self, k):
            return super(store_cls, self)._id_of_key(id_of_key(k))

        store_cls._id_of_key = _id_of_key

    if obj_of_data is not None:
        def _obj_of_data(self, _id):
            return obj_of_data(super(store_cls, self)._obj_of_data(_id))

        store_cls._obj_of_data = _obj_of_data

    if data_of_obj is not None:
        def _data_of_obj(self, obj):
            return super(store_cls, self)._data_of_obj(data_of_obj(obj))

        store_cls._data_of_obj = _data_of_obj

    if postget is not None:
        def __getitem__(self, k):
            return postget(k, super(store_cls, self).__getitem__(k))

        store_cls.__getitem__ = __getitem__

    return store_cls

    #
    # class MyStore(Store):
    #     @wraps(persister_cls.__init__)
    #     def __init__(self, *args, **kwargs):
    #         persister = persister_cls(*args, **kwargs)
    #         super().__init__(persister)
    #
    # name = name or ('Wrapped' + persister_cls.__name__)
    # MyStore.__name__ = name
    #
    # return MyStore


_method_name_for = {
    'write': '__setitem__',
    'read': '__getitem__',
    'delete': '__delitem__',
    'list': '__iter__',
    'count': '__len__'
}


def _insert_alias(store, method_name, alias=None):
    if isinstance(alias, str) and hasattr(store, method_name):
        setattr(store, alias, getattr(store, method_name))


def insert_aliases(store, *, write=None, read=None, delete=None, list=None, count=None):
    """Insert method aliases of CRUD operations of a store (class or instance).
    If store is a class, you'll get a copy of the class with those methods added.
    If store is an instance, the methods will be added in place (no copy will be made).

    Note: If an operation (write, read, delete, list, count) is not specified, no alias will be created for
    that operation.

    IMPORTANT NOTE: The signatures of the methods the aliases will point to will not change.
    We say this because, you can call the write method "dump", but you'll have to use it as
    `store.dump(key, val)`, not `store.dump(val, key)`, which is the signature you're probably used to
    (it's the one used by json.dump or pickle.dump for example). If you want that familiar interface,
    using the insert_load_dump_aliases function.

    Args:
        store: The store to extend with aliases.
        write: Desired method name for __setitem__
        read: Desired method name for __getitem__
        delete: Desired method name for __delitem__
        list: Desired method name for __iter__
        count: Desired method name for __len__

    Returns: A store with the desired aliases.

    >>> # Example of extending a class
    >>> mydict = insert_aliases(dict, write='dump', read='load', delete='rm', list='peek', count='size')
    >>> s = mydict(true='love')
    >>> s.dump('friends', 'forever')
    >>> s
    {'true': 'love', 'friends': 'forever'}
    >>> s.load('true')
    'love'
    >>> list(s.peek())
    ['true', 'friends']
    >>> s.size()
    2
    >>> s.rm('true')
    >>> s
    {'friends': 'forever'}
    >>>
    >>> # Example of extending an instance
    >>> from collections import UserDict
    >>> s = UserDict(true='love')  # make (and instance) of a UserDict (can't modify a dict instance)
    >>> # make aliases of note that you don't need
    >>> s = insert_aliases(s, write='put', read='retrieve', count='num_of_items')
    >>> s.put('friends', 'forever')
    >>> s
    {'true': 'love', 'friends': 'forever'}
    >>> s.retrieve('true')
    'love'
    >>> s.num_of_items()
    2
    """
    if isinstance(store, type):
        store = type(store.__name__, (store,), {})
    for alias, method_name in _method_name_for.items():
        _insert_alias(store, method_name, alias=locals().get(alias))
    return store


def insert_load_dump_aliases(store, delete=None, list=None, count=None):
    """Insert load and dump methods, with familiar dump(obj, location) signature.

    Args:
        store: The store to extend with aliases.
        delete: Desired method name for __delitem__
        list: Desired method name for __iter__
        count: Desired method name for __len__

    Returns: A store with the desired aliases.

    >>> mydict = insert_load_dump_aliases(dict)
    >>> s = mydict()
    >>> s.dump(obj='love', key='true')
    >>> s
    {'true': 'love'}
    """
    store = insert_aliases(store, read='load', delete=delete, list=list, count=count)

    def dump(self, obj, key):
        return self.__setitem__(key, obj)

    if isinstance(store, type):
        store.dump = dump
    else:
        store.dump = types.MethodType(dump, store)

    return store
