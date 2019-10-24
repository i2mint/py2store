from functools import wraps
from py2store.base import has_kv_store_interface, Store


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


def wrap_kvs(store_cls, name=None, *, key_of_id=None, id_of_key=None, obj_of_data=None, data_of_obj=None):
    """

    Args:
        store_cls:
        name:
        key_of_id:
        id_of_key:
        obj_of_data:
        data_of_obj:

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


def insert_aliases(store, write=None, read=None, delete=None, list=None, count=None):
    for alias, method_name in _method_name_for.items():
        _insert_alias(store, method_name, alias=locals().get(alias))
    return store


def _insert_alias(store, method_name, alias=None):
    if isinstance(alias, str) and hasattr(store, method_name):
        setattr(store, alias, getattr(store, method_name))
