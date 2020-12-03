from functools import wraps, reduce
from dataclasses import dataclass
from typing import Union
import os
from warnings import warn

from py2store.base import Store
from py2store.util import lazyprop
from py2store.trans import store_decorator
from py2store.dig import recursive_get_attr

path_sep = os.path.sep


class PathGetMixin:
    """
    Mixin allows you to access nested stores through a path of keys.
    That is, give you a path_store from a store, such that:
    ```
        path_store['a','b','c'] == store['a']['b']['c']
    ```
    The mixin will check if the key is of the path type (by default `tuple`), and if it is, it will iterate through
    the path, recursively getting the elements.

    Plays well with:
        KeyPath

    >>> class P(PathGetMixin, dict):
    ...     pass
    >>> s = P({'a': {'b': {'c': 42}}})
    >>> s['a']
    {'b': {'c': 42}}
    >>> s['a', 'b']
    {'c': 42}
    >>> s['a', 'b', 'c']
    42
    >>>
    >>> from py2store import kv_wrap
    >>> class P(PathGetMixin, dict): ...
    >>> PP = kv_wrap(KeyPath(path_sep='.'))(P)
    >>>
    >>> s = PP({'a': {'b': {'c': 42}}})
    >>> assert s['a'] == {'b': {'c': 42}}
    >>> assert s['a.b'] == {'c': 42}
    >>> assert s['a.b.c'] == 42
    """

    _path_type: type = tuple

    def __getitem__(self, k):
        if isinstance(k, self._path_type):
            return reduce(lambda store, key: store[key], k, self)
        else:
            return super().__getitem__(k)


@dataclass
class KeyPath:
    """
    A key mapper that converts from an iterable key (default tuple) to a string (given a path-separator str)

    Args:
        path_sep: The path separator (used to make string paths from iterable paths and visa versa
        _path_type: The type of the outcoming (inner) path. But really, any function to convert from a list to
            the outer path type we want.

    Plays well with:
        KeyPath

    >>> kp = KeyPath(path_sep='/')
    >>> kp._key_of_id(('a', 'b', 'c'))
    'a/b/c'
    >>> kp._id_of_key('a/b/c')
    ('a', 'b', 'c')
    >>> kp = KeyPath(path_sep='.')
    >>> kp._key_of_id(('a', 'b', 'c'))
    'a.b.c'
    >>> kp._id_of_key('a.b.c')
    ('a', 'b', 'c')
    >>> kp = KeyPath(path_sep=':::', _path_type=dict.fromkeys)
    >>> _id = dict.fromkeys('abc')
    >>> _id
    {'a': None, 'b': None, 'c': None}
    >>> kp._key_of_id(_id)
    'a:::b:::c'
    >>> kp._id_of_key('a:::b:::c')
    {'a': None, 'b': None, 'c': None}
    """

    path_sep: str = path_sep
    _path_type: Union[type, callable] = tuple

    def _key_of_id(self, _id):
        if not isinstance(_id, str):
            return self.path_sep.join(_id)
        else:
            return _id

    def _id_of_key(self, k):
        return self._path_type(k.split(self.path_sep))


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
    _prefix_attr_name = '_prefix'

    @lazyprop
    def _prefix_length(self):
        return len(getattr(self, self._prefix_attr_name))

    def _id_of_key(self, k):
        return getattr(self, self._prefix_attr_name) + k

    def _key_of_id(self, _id):
        return _id[self._prefix_length:]


@store_decorator
def mk_relative_path_store(
        store_cls=None,
        *,
        name=None,
        with_key_validation=False,
        prefix_attr="_prefix",
):
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
    >>>  # but under the hood, the dict we wrapped actually contains the '/ROOT/' prefix
    >>> dict(s.store)
    {'/ROOT/foo': 'bar'}
    >>>
    >>> # The static way: Make a class that will integrate the _prefix at construction time.
    >>> class MyStore(mk_relative_path_store(dict)):  # Indeed, mk_relative_path_store(dict) is a class you can subclass
    ...     def __init__(self, _prefix, *args, **kwargs):
    ...         self._prefix = _prefix

    You can choose the name you want that prefix to have as an attribute (we'll still make
    a hidden '_prefix' attribute for internal use, but at least you can have an attribute with the
    name you want.

    >>> MyRelStore = mk_relative_path_store(dict, prefix_attr='rootdir')
    >>> s = MyRelStore()
    >>> s.rootdir = '/ROOT/'

    >>> s['foo'] = 'bar'
    >>> dict(s.items())  # gives us what you would expect
    {'foo': 'bar'}
    >>>  # but under the hood, the dict we wrapped actually contains the '/ROOT/' prefix
    >>> dict(s.store)
    {'/ROOT/foo': 'bar'}

    """
    # name = name or ("RelPath" + store_cls.__name__)
    # __module__ = __module__ or getattr(store_cls, "__module__", None)

    if name is not None:
        from warnings import warn
        warn(f"The use of name argumment is deprecated. Use __name__ instead", DeprecationWarning)

    cls = type(store_cls.__name__, (PrefixRelativizationMixin, Store), {})

    @wraps(store_cls.__init__)
    def __init__(self, *args, **kwargs):
        Store.__init__(self, store=store_cls(*args, **kwargs))
        prefix = recursive_get_attr(self.store, prefix_attr, "")
        setattr(
            self, prefix_attr, prefix
        )  # TODO: Might need descriptor to enable assignment

    cls.__init__ = __init__

    if prefix_attr != '_prefix':
        assert not hasattr(store_cls, '_prefix'), f"You already have a _prefix attribute, " \
                                                  f"but want the prefix name to be {prefix_attr}. " \
                                                  f"That's not going to be easy for me."

        # if not hasattr(cls, prefix_attr):
        #     warn(f"You said you wanted prefix_attr='{prefix_attr}', "
        #          f"but {cls} (the wrapped class) doesn't have a '{prefix_attr}'. "
        #          f"I'll let it slide because perhaps the attribute is dynamic. But I'm warning you!!")

        @property
        def _prefix(self):
            return getattr(self, prefix_attr)

        cls._prefix = _prefix

    if with_key_validation:
        assert hasattr(store_cls, 'is_valid_key'), "If you want with_key_validation=True, " \
                                                   "you'll need a method called is_valid_key to do the validation job"

        def _id_of_key(self, k):
            _id = super(cls, self)._id_of_key(k)
            if self.store.is_valid_key(_id):
                return _id
            else:
                raise KeyError(
                    f"Key not valid (usually because does not exist or access not permitted): {k}"
                )

        cls._id_of_key = _id_of_key

    # if __module__ is not None:
    #     cls.__module__ = __module__

    # print(callable(cls))

    return cls


# TODO: Intended to replace the init-less PrefixRelativizationMixin
#  (but should change name if so, since Mixins shouldn't have inits)
class RelativePathKeyMapper:
    def __init__(self, prefix):
        self._prefix = prefix
        self._prefix_length = len(self._prefix)

    def _id_of_key(self, k):
        return self._prefix + k

    def _key_of_id(self, _id):
        return _id[self._prefix_length:]


from py2store.key_mappers.naming import StrTupleDict
from enum import Enum


class PathKeyTypes(Enum):
    str = 'str'
    dict = 'dict'
    tuple = 'tuple'
    namedtuple = 'namedtuple'


_method_names_for_path_type = {
    PathKeyTypes.str: {'_id_of_key': StrTupleDict.simple_str_to_str,
                       '_key_of_id': StrTupleDict.str_to_simple_str},
    PathKeyTypes.dict: {'_id_of_key': StrTupleDict.dict_to_str,
                        '_key_of_id': StrTupleDict.str_to_dict},
    PathKeyTypes.tuple: {'_id_of_key': StrTupleDict.tuple_to_str,
                         '_key_of_id': StrTupleDict.str_to_tuple},
    PathKeyTypes.namedtuple: {'_id_of_key': StrTupleDict.namedtuple_to_str,
                              '_key_of_id': StrTupleDict.str_to_namedtuple},
}


#
# def str_to_simple_str(self, s: str):
#     return self.sep.join(*self.str_to_tuple(s))
#
#
# def simple_str_to_str(self, ss: str):
#     self.tuple_to_str(self.si)

# TODO: Add key and id type validation
def str_template_key_trans(
        template: str,
        key_type: PathKeyTypes,
        format_dict=None,
        process_kwargs=None,
        process_info_dict=None,
        named_tuple_type_name="NamedTuple",
        sep: str = path_sep,
):
    """Make a key trans object that translates from a string _id to a dict, tuple, or namedtuple key (and back)"""

    assert key_type in PathKeyTypes, f"key_type was {key_type}. Needs to be one of these: {', '.join(PathKeyTypes)}"

    class PathKeyMapper(StrTupleDict):
        ...

    setattr(PathKeyMapper, '_id_of_key', _method_names_for_path_type[key_type]['_id_of_key'])
    setattr(PathKeyMapper, '_key_of_id', _method_names_for_path_type[key_type]['_key_of_id'])

    key_trans = PathKeyMapper(template, format_dict, process_kwargs,
                              process_info_dict, named_tuple_type_name, sep)

    return key_trans


str_template_key_trans.method_names_for_path_type = _method_names_for_path_type
str_template_key_trans.key_types = PathKeyTypes


# TODO: Merge with mk_relative_path_store
def rel_path_wrap(o, _prefix):
    """
    Args:
        o: An object to be wrapped
        _prefix: The _prefix to use for key wrapping (will remove it from outcoming keys and add to ingoing keys.

    >>> # The dynamic way (if you try this at home, be aware of the pitfalls of the dynamic way
    >>> # -- but don't just believe the static dogmas).
    >>> d = {'/ROOT/of/every/thing': 42, '/ROOT/of/this/too': 0}
    >>> dd = rel_path_wrap(d, '/ROOT/of/')
    >>> dd['foo'] = 'bar'
    >>> dict(dd.items())  # gives us what you would expect
    {'every/thing': 42, 'this/too': 0, 'foo': 'bar'}
    >>>  # but under the hood, the dict we wrapped actually contains the '/ROOT/' prefix
    >>> dict(dd.store)
    {'/ROOT/of/every/thing': 42, '/ROOT/of/this/too': 0, '/ROOT/of/foo': 'bar'}
    >>>
    >>> # The static way: Make a class that will integrate the _prefix at construction time.
    >>> class MyStore(mk_relative_path_store(dict)):  # Indeed, mk_relative_path_store(dict) is a class you can subclass
    ...     def __init__(self, _prefix, *args, **kwargs):
    ...         self._prefix = _prefix

    """

    from py2store import kv_wrap

    trans_obj = RelativePathKeyMapper(_prefix)
    return kv_wrap(trans_obj)(o)

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
