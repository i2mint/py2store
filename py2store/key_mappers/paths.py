from functools import wraps
from py2store.base import Store
from py2store.util import lazyprop
from py2store.dig import recursive_get_attr


class PrefixRelativizationMixin:
    """
    Mixin that adds a intercepts the _id_of_key an _key_of_id methods, transforming absolute keys to relative ones.
    Designed to work with string keys, where absolute and relative are relative to a _prefix attribute
    (assumed to exist).
    The cannonical use case is when keys are absolute file paths, but we want to identify data through relative paths.
    Instead of referencing files through an absolute path such as
        /A/VERY/LONG/ROOT/FOLDER/the/file/we.want
    we can instead reference the file as
        the/file/we.want

    Note though, that PrefixRelativizationMixin can be used, not only for local paths,
    but when ever a string reference is involved.
    In fact, not only strings, but any key object that has a __len__, __add__, and subscripting.

    When subclassed, should be placed before the class defining _id_of_key an _key_of_id.
    Also, assumes that a (string) _prefix attribute will be available.

    >>> from py2store.base import Store
    >>> from collections import UserDict
    >>>
    >>> class MyStore(PrefixRelativizationMixin, Store):
    ...     def __init__(self, store, _prefix='/root/of/data/'):
    ...         super().__init__(store)
    ...         self._prefix = _prefix
    ...
    >>> s = MyStore(store=dict())  # using a dict as our store
    >>> s['foo'] = 'bar'
    >>> assert s['foo'] == 'bar'
    >>> s['too'] = 'much'
    >>> assert list(s.keys()) == ['foo', 'too']
    >>> # Everything looks normal, but are the actual keys behind the hood?
    >>> s._id_of_key('foo')
    '/root/of/data/foo'
    >>> # see when iterating over s.items(), we get the interface view:
    >>> list(s.items())
    [('foo', 'bar'), ('too', 'much')]
    >>> # but if we ask the store we're actually delegating the storing to, we see what the keys actually are.
    >>> s.store.items()
    dict_items([('/root/of/data/foo', 'bar'), ('/root/of/data/too', 'much')])
    """

    @lazyprop
    def _prefix_length(self):
        return len(self._prefix)

    def _id_of_key(self, k):
        return self._prefix + k

    def _key_of_id(self, _id):
        return _id[self._prefix_length:]


def mk_relative_path_store(store_cls, name=None, with_key_validation=False):
    """

    Args:
        store_cls: The base store to wrap (subclass)
        name: The name of the new store (by default 'RelPath' + store_cls.__name__)
        with_key_validation: Whether keys should be validated upon access (store_cls must have an is_valid_key method

    Returns: A new class that uses relative paths (i.e. where _prefix is automatically added to incoming keys,
        and the len(_prefix) first characters are removed from outgoing keys.

    >>> # The dynamic way (if you try this at home, be aware of the pitfalls of the dynamic way
    >>> # -- but don't just believe the static dogmas).
    >>> MyStore = mk_relative_path_store(dict)  # wrap our favorite store: A dict.
    >>> s = MyStore()  # make such a store
    >>> s._prefix = '/ROOT/'
    >>> s['foo'] = 'bar'
    >>> dict(s.items())  # gives us what you would expect
    {'foo': 'bar'}
    >>>  # but underthe hood, the dict we wrapped actually contains the '/ROOT/' prefix
    >>> dict(s.store)
    {'/ROOT/foo': 'bar'}
    >>>
    >>> # The static way: Make a class that will integrate the _prefix at construction time.
    >>> class MyStore(mk_relative_path_store(dict)):  # Indeed, mk_relative_path_store(dict) is a class you can subclass
    ...     def __init__(self, _prefix, *args, **kwargs):
    ...         self._prefix = _prefix

    """
    name = name or ('RelPath' + store_cls.__name__)

    cls = type(name, (PrefixRelativizationMixin, Store), {})

    @wraps(store_cls.__init__)
    def __init__(self, *args, **kwargs):
        super(cls, self).__init__(store=store_cls(*args, **kwargs))
        self._prefix = recursive_get_attr(self.store, '_prefix', '')  # TODO: Might need descriptor to enable assignment

    cls.__init__ = __init__

    if with_key_validation:
        def _id_of_key(self, k):
            _id = super(cls, self)._id_of_key(k)
            if self.store.is_valid_key(_id):
                return _id
            else:
                raise KeyError(f"Key not valid: {k}")

        cls._id_of_key = _id_of_key

    return cls

# mk_relative_path_store_cls = mk_relative_path_store  # alias

## Alternative to mk_relative_path_store that doesn't make lint complain (but the repr shows MyStore, not name)
# def mk_relative_path_store_alt(store_cls, name=None):
#     if name is None:
#         name = 'RelPath' + store_cls.__name__
#
#     class MyStore(PrefixRelativizationMixin, Store):
#         @wraps(store_cls.__init__)
#         def __init__(self, *args, **kwargs):
#             super().__init__(store=store_cls(*args, **kwargs))
#             self._prefix = self.store._prefix
#     MyStore.__name__ = name
#
#     return MyStore
