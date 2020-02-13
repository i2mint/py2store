from functools import wraps
import types
from inspect import signature
from typing import Type, Union, Iterable
from py2store.base import has_kv_store_interface, Store, Collection, KvReader
from py2store.util import lazyprop


def get_class_name(cls, dflt_name=None):
    name = getattr(cls, '__name__', None)
    if name is None:
        name = getattr(getattr(cls, '__class__', object), '__name__', None)
        if name is None:
            if dflt_name is not None:
                return dflt_name
            else:
                raise ValueError(f"{cls} has no name I could extract")
    return name

def num_of_args(func):
    return len(signature(func).parameters)


def transparent_key_method(self, k):
    return k


def mk_kv_reader_from_kv_collection(kv_collection, name=None, getitem=transparent_key_method):
    """Make a KvReader class from a Collection class.

    Args:
        kv_collection: The Collection class
        name: The name to give the KvReader class (by default, it will be kv_collection.__name__ + 'Reader')
        getitem: The method that will be assigned to __getitem__. Should have the (self, k) signature.
            By default, getitem will be transparent_key_method, returning the key as is.
            This default is useful when you want to delegate the actual getting to a _obj_of_data wrapper.

    Returns: A KvReader class that subclasses the input kv_collection
    """

    name = name or kv_collection.__name__ + 'Reader'
    reader_cls = type(name, (kv_collection, KvReader), {'__getitem__': getitem})
    return reader_cls


def raise_disabled_error(functionality):
    def disabled_function(*args, **kwargs):
        raise ValueError(f"{functionality} is disabled")

    return disabled_function


def disable_delitem(o):
    if hasattr(o, '__delitem__'):
        o.__delitem__ = raise_disabled_error('deletion')
    return o


def disable_setitem(o):
    if hasattr(o, '__setitem__'):
        o.__setitem__ = raise_disabled_error('writing')
    return o


def mk_read_only(o):
    return disable_delitem(disable_setitem(o))


def cache_iter(store, iter_to_container=list, name=None):
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

    IMPORTANT Warning: This decorator wraps __iter__ only. This will affect consequential methods (such as
    keys, items, values, etc.) only if they use __iter__ to carry out their work. For example, items() won't have
    the desired effect if you wrap dict, but will have the desired effect if you wrap KvStore.

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
    >>>
    >>> # Let's demo the iter_to_container argument. The default is "list", which will just consume the iter in order
    >>> sorted_dict = cache_iter(dict, iter_to_container=list)
    >>> s = sorted_dict({'b': 3, 'a': 2, 'c': 1})
    >>> list(s)  # keys will be in the order they were defined
    ['b', 'a', 'c']
    >>> sorted_dict = cache_iter(dict, iter_to_container=sorted)
    >>> s = sorted_dict({'b': 3, 'a': 2, 'c': 1})
    >>> list(s)  # keys will be sorted
    ['a', 'b', 'c']
    >>> sorted_dict = cache_iter(dict, iter_to_container=lambda x: sorted(x, key=len))
    >>> s = sorted_dict({'bbb': 3, 'aa': 2, 'c': 1})
    >>> list(s)  # keys will be sorted according to their length
    ['c', 'aa', 'bbb']
    """

    if not isinstance(store, type):  # then consider it to be an instance
        store_instance = store
        WrapperStore = cache_iter(Store, iter_to_container=iter_to_container, name=name)
        return WrapperStore(store_instance)
    else:
        store_cls = store
        name = name or 'IterCached' + get_class_name(store_cls)
        cached_cls = type(name, (store_cls,), {'_iter_cache': None})

        @lazyprop
        def _iter_cache(self):
            return iter_to_container(super(cached_cls, self).__iter__())

        def __iter__(self):
            # if getattr(self, '_iter_cache', None) is None:
            #     self._iter_cache = iter_to_container(super(cached_cls, self).__iter__())
            yield from self._iter_cache

        def __len__(self):
            return len(self._iter_cache)

        cached_cls.__iter__ = __iter__
        cached_cls.__len__ = __len__
        cached_cls._iter_cache = _iter_cache

        _define_keys_values_and_items_according_to_iter(cached_cls)

        return cached_cls


# TODO: Factor out the method injection pattern (e.g. __getitem__, __setitem__ and __delitem__ are nearly identical)
def filtered_iter(filt: Union[callable, Iterable], name=None):
    """Make a wrapper that will transform a store (class or instance thereof) into a sub-store (i.e. subset of keys).

    Args:
        filt: A callable or iterable:
            callable: Boolean filter function. A func taking a key and and returns True iff the key should be included.
            iterable: The collection of keys you want to filter "in"
        name: The name to give the wrapped class

    Returns: A wrapper (that then needs to be applied to a store instance or class.

    >>> filtered_dict = filtered_iter(filt=lambda k: (len(k) % 2) == 1)(dict)  # keep only odd length keys
    >>>
    >>> s = filtered_dict({'a': 1, 'bb': object, 'ccc': 'a string', 'dddd': [1, 2]})
    >>>
    >>> list(s)
    ['a', 'ccc']
    >>> 'a' in s  # True because odd (length) key
    True
    >>> 'bb' in s  # False because odd (length) key
    False
    >>> len(s)
    2
    >>> list(s.keys())
    ['a', 'ccc']
    >>> list(s.values())
    [1, 'a string']
    >>> list(s.items())
    [('a', 1), ('ccc', 'a string')]
    >>> s.get('a')
    1
    >>> assert s.get('bb') is None
    >>> s['x'] = 10
    >>> list(s.items())
    [('a', 1), ('ccc', 'a string'), ('x', 10)]
    >>> try:
    ...     s['xx'] = 'not an odd key'
    ...     raise ValueError("This should have failed")
    ... except KeyError:
    ...     pass
    """

    if not callable(filt):  # if filt is not a callable...
        # ... assume it's the collection of keys you want and make a filter function to filter those "in".
        assert next(iter(filt)), "filt should be a callable, or an iterable"
        keys_that_should_be_filtered_in = filt

        def filt(k):
            return k in keys_that_should_be_filtered_in

    def wrap(store, name=name):
        if not isinstance(store, type):  # then consider it to be an instance
            store_instance = store
            WrapperStore = filtered_iter(filt, name=name)(Store)
            return WrapperStore(store_instance)
        else:  # it's a class we're wrapping
            collection_cls = store
            name = name or 'Filtered' + get_class_name(collection_cls)
            wrapped_cls = type(name, (collection_cls,), {})

            def __iter__(self):
                yield from filter(filt, super(wrapped_cls, self).__iter__())

            wrapped_cls.__iter__ = __iter__

            _define_keys_values_and_items_according_to_iter(wrapped_cls)

            def __len__(self):
                c = 0
                for _ in self.__iter__():
                    c += 1
                return c

            wrapped_cls.__len__ = __len__

            def __contains__(self, k):
                if filt(k):
                    return super(wrapped_cls, self).__contains__(k)
                else:
                    return False

            wrapped_cls.__contains__ = __contains__

            if hasattr(wrapped_cls, '__getitem__'):
                def __getitem__(self, k):
                    if filt(k):
                        return super(wrapped_cls, self).__getitem__(k)
                    else:
                        raise KeyError(f"Key not in store: {k}")

                wrapped_cls.__getitem__ = __getitem__

            if hasattr(wrapped_cls, 'get'):
                def get(self, k, default=None):
                    if filt(k):
                        return super(wrapped_cls, self).get(k, default)
                    else:
                        return default

                wrapped_cls.get = get

            if hasattr(wrapped_cls, '__setitem__'):
                def __setitem__(self, k, v):
                    if filt(k):
                        return super(wrapped_cls, self).__setitem__(k, v)
                    else:
                        raise KeyError(f"Key not in store: {k}")

                wrapped_cls.__setitem__ = __setitem__

            if hasattr(wrapped_cls, '__delitem__'):
                def __delitem__(self, k):
                    if filt(k):
                        return super(wrapped_cls, self).__delitem__(k)
                    else:
                        raise KeyError(f"Key not in store: {k}")

                wrapped_cls.__delitem__ = __delitem__

            return wrapped_cls

    return wrap


def _define_keys_values_and_items_according_to_iter(cls):
    if hasattr(cls, 'keys'):
        def keys(self):
            return self.__iter__()

        cls.keys = keys

    if hasattr(cls, 'values'):
        def values(self):
            yield from (self[k] for k in self)

        cls.values = values

    if hasattr(cls, 'items'):
        def items(self):
            yield from ((k, self[k]) for k in self)

        cls.items = items


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

    name = name or ('PWrapped' + persister_cls.__name__)

    cls = type(name, (Store,), {})

    @wraps(persister_cls.__init__)
    def __init__(self, *args, **kwargs):
        super(cls, self).__init__(persister_cls(*args, **kwargs))

    cls.__init__ = __init__

    return cls


def wrap_kvs(store, name=None, *,
             key_of_id=None, id_of_key=None, obj_of_data=None, data_of_obj=None, postget=None
             ):
    """Make a Store that is wrapped with the given key/val transformers.

    Args:
        store: Store class or instance
        name: Name to give the wrapper class
        key_of_id: To be the external _key_of_id
        id_of_key: To be the external _id_of_key
        obj_of_data: To be the external _obj_of_data
        data_of_obj: To be the external _data_of_obj
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
    >>> A = wrap_kvs(dict, 'A',
    ...             key_of_id=key_of_id, id_of_key=id_of_key, obj_of_data=obj_of_data, data_of_obj=data_of_obj)
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
    >>> B = wrap_kvs(dict, 'B', postget=lambda k, v: f'upper {v}' if k[0].isupper() else f'lower {v}')
    >>> b = B()
    >>> b['BIG'] = 'letters'
    >>> b['small'] = 'text'
    >>> list(b.items())
    [('BIG', 'upper letters'), ('small', 'lower text')]
    """
    if not isinstance(store, type):  # then consider it to be an instance
        store_instance = store
        WrapperStore = wrap_kvs(Store, name=name,
                                key_of_id=key_of_id, id_of_key=id_of_key,
                                obj_of_data=obj_of_data, data_of_obj=data_of_obj,
                                postget=postget)
        return WrapperStore(store_instance)
    else:  # it's a class we're wrapping
        store_cls = store
        if not has_kv_store_interface(store_cls):
            store_cls = kv_wrap_persister_cls(store_cls, name=name)
        else:
            if name is None:
                # from warnings import warn
                # warn("The use of wraps_fv without an explicit name will be discontinued soon.")
                name = 'Wrapped' + store_cls.__name__
                # TODO: This is not the best way to handle this. Investigate another way. ######################
                global_names = set(globals()).union(locals())
                if name in global_names:
                    raise NameError("That name is already in use")
                # TODO: ########################################################################################
            _store_cls = store_cls
            store_cls = type(name, (_store_cls,), {})  # make a "copy"

        if key_of_id is not None:
            if num_of_args(key_of_id) == 1:
                def _key_of_id(self, _id):
                    return key_of_id(super(store_cls, self)._key_of_id(_id))
            else:
                def _key_of_id(self, _id):
                    return key_of_id(self, super(store_cls, self)._key_of_id(_id))

            store_cls._key_of_id = _key_of_id

        if id_of_key is not None:
            if num_of_args(id_of_key) == 1:
                def _id_of_key(self, k):
                    return super(store_cls, self)._id_of_key(id_of_key(k))
            else:
                def _id_of_key(self, k):
                    return super(store_cls, self)._id_of_key(id_of_key(self, k))

            store_cls._id_of_key = _id_of_key

        if obj_of_data is not None:
            if num_of_args(obj_of_data) == 1:
                def _obj_of_data(self, _id):
                    return obj_of_data(super(store_cls, self)._obj_of_data(_id))
            else:
                def _obj_of_data(self, _id):
                    return obj_of_data(self, super(store_cls, self)._obj_of_data(_id))

            store_cls._obj_of_data = _obj_of_data

        if data_of_obj is not None:
            if num_of_args(data_of_obj) == 1:
                def _data_of_obj(self, obj):
                    return super(store_cls, self)._data_of_obj(data_of_obj(obj))
            else:
                def _data_of_obj(self, obj):
                    return super(store_cls, self)._data_of_obj(data_of_obj(self, obj))

            store_cls._data_of_obj = _data_of_obj

        if postget is not None:
            if num_of_args(postget) == 2:
                def __getitem__(self, k):
                    return postget(k, super(store_cls, self).__getitem__(k))
            else:
                def __getitem__(self, k):
                    return postget(self, k, super(store_cls, self).__getitem__(k))

            store_cls.__getitem__ = __getitem__

        return store_cls


def _kv_wrap_outcoming_keys(trans_func):
    """Transform 'out-coming' keys, that is, the keys you see when you ask for them,
    say, through __iter__(), keys(), or first element of the items() pairs.

    Use this when you wouldn't use the keys in their original format,
    or when you want to extract information from it.

    Warning: If you haven't also wrapped incoming keys with a corresponding inverse transformation,
    you won't be able to use the outcoming keys to fetch data.

    >>> from collections import UserDict
    >>> S = kv_wrap.outcoming_keys(lambda x: x[5:])(UserDict)
    >>> s = S({'root/foo': 10, 'root/bar': 'xo'})
    >>> list(s)
    ['foo', 'bar']
    >>> list(s.keys())
    ['foo', 'bar']
    >>> list(s.items())
    [('foo', 10), ('bar', 'xo')]
    """

    def wrapper(o, name=None):
        name = name or getattr(o, '__name__', getattr(o.__class__, '__name__')) + '_kr'
        return wrap_kvs(o, name, key_of_id=trans_func)

    return wrapper


def _kv_wrap_ingoing_keys(trans_func):
    """Transform 'in-going' keys, that is, the keys you see when you ask for them,
    say, through __iter__(), keys(), or first element of the items() pairs.

    Use this when your context holds objects themselves holding key information, but you don't want to
    (because you shouldn't) 'manually' extract that information and construct the key manually every time you need
    to write something or fetch some existing data.

    Warning: If you haven't also wrapped outcoming keys with a corresponding inverse transformation,
    you won't be able to use the incoming keys to fetch data.

    >>> from collections import UserDict
    >>> S = kv_wrap.ingoing_keys(lambda x: 'root/' + x)(UserDict)
    >>> s = S()
    >>> s['foo'] = 10
    >>> s['bar'] = 'xo'
    >>> list(s)
    ['root/foo', 'root/bar']
    >>> list(s.keys())
    ['root/foo', 'root/bar']
    >>> list(s.items())
    [('root/foo', 10), ('root/bar', 'xo')]
    """

    def wrapper(o, name=None):
        name = name or getattr(o, '__name__', getattr(o.__class__, '__name__')) + '_kw'
        return wrap_kvs(o, name, id_of_key=trans_func)

    return wrapper


def _kv_wrap_outcoming_vals(trans_func):
    """Transform 'out-coming' values, that is, the values you see when you ask for them,
    say, through the values() or the second element of items() pairs.
    This can be seen as adding a de-serialization layer: trans_func being the de-serialization function.

    For example, say your store gives you values of the bytes type, but you want to use text, or gives you text,
    but you want it to be interpreted as a JSON formatted text and get a dict instead. Both of these are
    de-serialization layers, or out-coming value transformations.

    Warning: If it matters, make sure you also wrapped with a corresponding inverse serialization.

    >>> from collections import UserDict
    >>> S = kv_wrap.outcoming_vals(lambda x: x * 2)(UserDict)
    >>> s = S(foo=10, bar='xo')
    >>> list(s.values())
    [20, 'xoxo']
    >>> list(s.items())
    [('foo', 20), ('bar', 'xoxo')]
    """

    def wrapper(o, name=None):
        name = name or getattr(o, '__name__', getattr(o.__class__, '__name__')) + '_vr'
        return wrap_kvs(o, name, obj_of_data=trans_func)

    return wrapper


def _kv_wrap_ingoing_vals(trans_func):
    """Transform 'in-going' values, that is, the values at the level of the store's interface are transformed
    to a different value before writing to the wrapped store.
    This can be seen as adding a serialization layer: trans_func being the serialization function.

    For example, say you have a list of audio samples, and you want to save these in a WAV format.

    Warning: If it matters, make sure you also wrapped with a corresponding inverse de-serialization.

    >>> from collections import UserDict
    >>> S = kv_wrap.ingoing_vals(lambda x: x * 2)(UserDict)
    >>> s = S()
    >>> s['foo'] = 10
    >>> s['bar'] = 'xo'
    >>> list(s.values())
    [20, 'xoxo']
    >>> list(s.items())
    [('foo', 20), ('bar', 'xoxo')]
    """

    def wrapper(o, name=None):
        name = name or getattr(o, '__name__', getattr(o.__class__, '__name__')) + '_vw'
        return wrap_kvs(o, name, data_of_obj=trans_func)

    return wrapper


def _kv_wrap_val_reads_wrt_to_keys(trans_func):
    def wrapper(o, name=None):
        name = name or getattr(o, '__name__', getattr(o.__class__, '__name__')) + '_vrk'
        return wrap_kvs(o, name, postget=trans_func)

    return wrapper


def kv_wrap(trans_obj):
    """
    kv_wrap: A function that makes a wrapper (a decorator) that will get the wrappers from methods of the input object.

    kv_wrap also has attributes:
        outcoming_keys, ingoing_keys, outcoming_vals, ingoing_vals, and val_reads_wrt_to_keys
    which will only add a single specific wrapper (specified as a function), when that's what you need.

    """
    key_of_id = getattr(trans_obj, '_key_of_id', None)
    id_of_key = getattr(trans_obj, '_id_of_key', None)
    obj_of_data = getattr(trans_obj, '_obj_of_data', None)
    data_of_obj = getattr(trans_obj, '_data_of_obj', None)
    postget = getattr(trans_obj, '_postget', None)

    def wrapper(o, name=None):
        name = name or getattr(o, '__name__', getattr(o.__class__, '__name__')) + '_kr'
        return wrap_kvs(o, name, key_of_id=key_of_id, id_of_key=id_of_key, obj_of_data=obj_of_data,
                        data_of_obj=data_of_obj, postget=postget)

    return wrapper


kv_wrap.outcoming_keys = _kv_wrap_outcoming_keys
kv_wrap.ingoing_keys = _kv_wrap_ingoing_keys
kv_wrap.outcoming_vals = _kv_wrap_outcoming_vals
kv_wrap.ingoing_vals = _kv_wrap_ingoing_vals
kv_wrap.val_reads_wrt_to_keys = _kv_wrap_val_reads_wrt_to_keys

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
