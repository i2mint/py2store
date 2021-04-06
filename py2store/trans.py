from functools import wraps, partial, reduce
import types
from inspect import signature, Parameter
from typing import Union, Iterable, Optional, Collection
from py2store.base import Store, KvReader, AttrNames
from py2store.util import lazyprop, num_of_args, attrs_of, wraps
from py2store.utils.signatures import Sig, KO
from warnings import warn
from collections.abc import Iterable, KeysView, ValuesView, ItemsView


########################################################################################################################
# Internal Utils

def double_up_as_factory(decorator_func):
    """Repurpose a decorator both as it's original form, and as a decorator factory.
    That is, from a decorator that is defined do ``wrapped_func = decorator(func, **params)``,
    make it also be able to do ``wrapped_func = decorator(**params)(func)``.

    Note: You'll only be able to do this if all but the first argument are keyword-only,
    and the first argument (the function to decorate) has a default of ``None`` (this is for your own good).
    This is validated before making the "double up as factory" decorator.

    >>> @double_up_as_factory
    ... def decorator(func=None, *, multiplier=2):
    ...     def _func(x):
    ...         return func(x) * multiplier
    ...     return _func
    ...
    >>> def foo(x):
    ...     return x + 1
    ...
    >>> foo(2)
    3
    >>> wrapped_foo = decorator(foo, multiplier=10)
    >>> wrapped_foo(2)
    30
    >>>
    >>> multiply_by_3 = decorator(multiplier=3)
    >>> wrapped_foo = multiply_by_3(foo)
    >>> wrapped_foo(2)
    9
    >>>
    >>> @decorator(multiplier=3)
    ... def foo(x):
    ...     return x + 1
    ...
    >>> foo(2)
    9

    Note that to be able to use double_up_as_factory, your first argument (the object to be wrapped) needs to default
    to None and be the only argument that is not keyword-only (i.e. all other arguments need to be keyword only).

    >>> @double_up_as_factory
    ... def decorator_2(func, *, multiplier=2):
    ...     '''Should not be able to be transformed with double_up_as_factory'''
    Traceback (most recent call last):
      ...
    AssertionError: First argument of the decorator function needs to default to None. Was <class 'inspect._empty'>
    >>> @double_up_as_factory
    ... def decorator_3(func=None, multiplier=2):
    ...     '''Should not be able to be transformed with double_up_as_factory'''
    Traceback (most recent call last):
      ...
    AssertionError: All arguments (besides the first) need to be keyword-only

    """

    def validate_decorator_func(decorator_func):
        first_param, *other_params = signature(decorator_func).parameters.values()
        assert first_param.default is None, \
            f"First argument of the decorator function needs to default to None. Was {first_param.default}"
        assert all(p.kind == p.KEYWORD_ONLY for p in other_params), \
            f"All arguments (besides the first) need to be keyword-only"
        return True

    validate_decorator_func(decorator_func)

    @wraps(decorator_func)
    def _double_up_as_factory(wrapped=None, **kwargs):
        if wrapped is None:  # then we want a factory
            return partial(decorator_func, **kwargs)
        else:
            return decorator_func(wrapped, **kwargs)

    return _double_up_as_factory


def _all_but_first_arg_are_keyword_only(func):
    """
    >>> def foo(a, *, b, c=2): ...
    >>> _all_but_first_arg_are_keyword_only(foo)
    True
    >>> def bar(a, b, *, c=2): ...
    >>> _all_but_first_arg_are_keyword_only(bar)
    False
    """
    kinds = (p.kind for p in signature(func).parameters.values())
    _ = next(kinds)  # consume first item, and all remaining should be KEYWORD_ONLY
    return all(kind == Parameter.KEYWORD_ONLY for kind in kinds)


# TODO: Separate the wrapper_assignments injection (and possibly make these not show up at the interface?)
# FIXME: doctest line numbers not shown correctly when wrapped by store_decorator!
def store_decorator(func):
    """Helper to make store decorators.

    You provide a class-decorating function ``func`` that takes a store type (and possibly additional params)
    and returns another decorated store type.

    ``store_decorator`` takes that ``func`` and provides an enhanced class decorator specialized for stores.
    Namely it will:
    - Add ``__module__``, ``__qualname__``, ``__name__`` and ``__doc__`` arguments to it
    - Copy the aforementioned arguments to the decorated class, or copy the attributes of the original if not specified.
    - Output a decorator that can be used in four different ways: a class/instance decorator/factory.

    By class/instance decorator/factory we mean that if ``A`` is a class, ``a`` an instance of it,
    and ``deco`` a decorator obtained with ``store_decorator(func)``,
    we can use ``deco`` to
    - class decorator: decorate a class
    - class decorator factory: make a function that decorates classes
    - instance decorator: decorate an instance of a store
    - instancce decorator factor: make a function that decorates instances of stores

    For example, say we have the following ``deco`` that we made with ``store_decorator``:

    >>> @store_decorator
    ... def deco(cls=None, *, x=1):
    ...     # do stuff to cls, or a copy of it...
    ...     cls.x = x  # like this for example
    ...     return cls

    And a class that has nothing to it:

    >>> class A: ...

    Nammely, it doesn't have an ``x``

    >>> hasattr(A, 'x')
    False

    We make a ``decorated_A`` with ``deco`` (class decorator example)

    >>> deco(A, x=42)
    <class 'trans.A'>

    and we see that we now have an ``x`` and it's 42

    >>> hasattr(A, 'x')
    True
    >>> A.x
    42

    But we could have also made a factory to decorate ``A`` and anything else that comes our way.

    >>> paint_it_42 = deco(x=42)
    >>> decorated_A = paint_it_42(A)
    >>> assert decorated_A.x == 42
    >>> class B:
    ...     x = 'destined to disappear'
    >>> assert paint_it_42(B).x == 42

    To be fair though, you'll probably see the factory usage appear in the following form,
    where the class is decorated at definition time.

    >>> @deco(x=42)
    ... class B:
    ...     pass
    >>> assert B.x == 42

    If your exists already, and you want to keep it as is (with the same name), you can
    use subclassing to transform a copy of ``A`` instead, as below.
    Also note in the following example, that ``deco`` was used without parentheses,
    which is equivalent to ``@deco()``,
    and yes, store_decorator makes that possible to, as long as your params have defaults

    >>> @deco
    ... class decorated_A(A):
    ...     pass
    >>> assert decorated_A.x == 1
    >>> assert A.x == 42

    Finally, you can also decorate instances:

    >>> class A: ...
    >>> a = A()
    >>> hasattr(a, 'x')
    False
    >>> b = deco(a); assert b.x == 1; # b has an x and it's 1
    >>> b = deco()(a); assert b.x == 1; # b has an x and it's 1
    >>> b = deco(a, x=42); assert b.x == 42  # b has an x and it's 42
    >>> b = deco(x=42)(a); assert b.x == 42; # b has an x and it's 42

    WARNING: Note though that the type of ``b`` is not the same type as ``a``
    >>> isinstance(b, a.__class__)
    False

    No, ``b`` is an instance of a ``py2store.base.Store``, which is a class containing an
    instance of a store (here, ``a``).

    >>> type(b)
    <class 'py2store.base.Store'>
    >>> b.store == a
    True

    Now, here's some more example, slightly closer to real usage

    >>> from py2store.trans import store_decorator
    >>> from inspect import signature
    >>>
    >>> def rm_deletion(store=None, *, msg='Deletions not allowed.'):
    ...     name = getattr(store, '__name__', 'Something') + '_w_sommething'
    ...     assert isinstance(store, type), f"Should be a type, was {type(store)}: {store}"
    ...     wrapped_store = type(name, (store,), {})
    ...     wrapped_store.__delitem__ = lambda self, k: msg
    ...     return wrapped_store
    ...
    >>> remove_deletion = store_decorator(rm_deletion)

    See how the signature of the wrapper has some extra inputs that were injected (__module__, __qualname__, etc.):

    >>> print(str(signature(remove_deletion)))
    (store=None, *, msg='Deletions not allowed.', __module__=None, __name__=None, __qualname__=None, __doc__=None, __annotations__=None, __defaults__=None, __kwdefaults__=None)

    Using it as a class decorator factory (the most common way):

    As a class decorator "factory", without parameters (and without ()):

    >>> from collections import UserDict
    >>> @remove_deletion
    ... class WD(UserDict):
    ...     "Here's the doc"
    ...     pass
    >>> wd = WD(x=5, y=7)
    >>> assert wd == UserDict(x=5, y=7)  # same as far as dict comparison goes
    >>> assert wd.__delitem__('x') == 'Deletions not allowed.'
    >>> assert wd.__doc__ == "Here's the doc"

    As a class decorator "factory", with parameters:

    >>> @remove_deletion(msg='No way. I do not trust you!!')
    ... class WD(UserDict): ...
    >>> wd = WD(x=5, y=7)
    >>> assert wd == UserDict(x=5, y=7)  # same as far as dict comparison goes
    >>> assert wd.__delitem__('x') == 'No way. I do not trust you!!'

    The __doc__ is empty:

    >>> assert WD.__doc__ == None

    But we could specify a doc if we wanted to:

    >>> @remove_deletion(__doc__="Hi, I'm a doc.")
    ... class WD(UserDict):
    ...     "This is the original doc, that will be overritten"
    >>> assert WD.__doc__ == "Hi, I'm a doc."


    The class decorations above are equivalent to the two following:

    >>> WD = remove_deletion(UserDict)
    >>> wd = WD(x=5, y=7)
    >>> assert wd == UserDict(x=5, y=7)  # same as far as dict comparison goes
    >>> assert wd.__delitem__('x') == 'Deletions not allowed.'
    >>>
    >>> WD = remove_deletion(UserDict, msg='No way. I do not trust you!!')
    >>> wd = WD(x=5, y=7)
    >>> assert wd == UserDict(x=5, y=7)  # same as far as dict comparison goes
    >>> assert wd.__delitem__('x') == 'No way. I do not trust you!!'

    But we can also decorate instances. In this case they will be wrapped in a Store class
    before being passed on to the actual decorator.

    >>> d = UserDict(x=5, y=7)
    >>> wd = remove_deletion(d)
    >>> assert wd == d  # same as far as dict comparison goes
    >>> assert wd.__delitem__('x') == 'Deletions not allowed.'
    >>>
    >>> d = UserDict(x=5, y=7)
    >>> wd = remove_deletion(d, msg='No way. I do not trust you!!')
    >>> assert wd == d  # same as far as dict comparison goes
    >>> assert wd.__delitem__('x') == 'No way. I do not trust you!!'

    """

    # wrapper_assignments = ('__module__', '__qualname__', '__name__', '__doc__', '__annotations__')
    wrapper_assignments = (
        '__module__', '__name__', '__qualname__', '__doc__',
        '__annotations__', '__defaults__', '__kwdefaults__')

    @wraps(func)
    def _func_wrapping_store_in_cls_if_not_type(store, **kwargs):

        specials = dict()
        for a in wrapper_assignments:
            v = kwargs.pop(a, getattr(store, a, None))
            if v is not None:
                specials[a] = v

        if not isinstance(store, type):
            store_instance = store
            WrapperStore = func(Store, **kwargs)
            r = WrapperStore(store_instance)
        else:
            assert _all_but_first_arg_are_keyword_only(func), (
                "To use decorating_store_cls, all but the first of your function's arguments need to be all keyword only. "
                f"The signature was {func.__qualname__}{signature(func)}")
            r = func(store, **kwargs)

        for k, v in specials.items():
            if v is not None:
                setattr(r, k, v)

        return r

    _func_wrapping_store_in_cls_if_not_type.func = func  # TODO: look for usages, and if not, use __wrapped__

    # @wraps(func)
    wrapper_sig = Sig(func).merge_with_sig(
        [dict(name=a, default=None, kind=KO) for a in wrapper_assignments],
        ch_to_all_pk=False
    )

    # TODO: Re-use double_up_as_factory here
    @wrapper_sig
    def wrapper(store=None, **kwargs):
        if store is None:  # then we want a factory
            return partial(_func_wrapping_store_in_cls_if_not_type, **kwargs)
        else:
            wrapped_store_cls = _func_wrapping_store_in_cls_if_not_type(store, **kwargs)

            return wrapped_store_cls

    # Make sure the wrapper (yes, also the wrapper) has the same key dunders as the func
    for a in wrapper_assignments:
        v = getattr(func, a, None)
        if v is not None:
            setattr(wrapper, a, v)

    return wrapper


def ensure_set(x):
    if isinstance(x, str):
        x = [x]
    return set(x)


def get_class_name(cls, dflt_name=None):
    name = getattr(cls, "__qualname__", None)
    if name is None:
        name = getattr(getattr(cls, "__class__", object), "__qualname__", None)
        if name is None:
            if dflt_name is not None:
                return dflt_name
            else:
                raise ValueError(f"{cls} has no name I could extract")
    return name


def store_wrap(obj):
    if isinstance(obj, type):
        @wraps(type(obj), updated=())  # added this: test
        class StoreWrap(Store):
            @wraps(obj.__init__)
            def __init__(self, *args, **kwargs):
                persister = obj(*args, **kwargs)
                super().__init__(persister)

        return StoreWrap
    else:
        return Store(obj)


# # Older version, kept around for awhile, for review:
# def store_wrap(obj, name=None):
#     if isinstance(obj, type):
#         name = name or f"{get_class_name(obj, 'StoreWrap')}Store"
#
#         class StoreWrap(Store):
#             @wraps(obj.__init__)
#             def __init__(self, *args, **kwargs):
#                 persister = obj(*args, **kwargs)
#                 super().__init__(persister)
#
#         StoreWrap.__qualname__ = name
#         # if hasattr(obj, '_cls_trans'):
#         #     StoreWrap._cls_trans = obj._cls_trans
#         return StoreWrap
#     else:
#         return Store(obj)


def _is_bound(method):
    return hasattr(method, "__self__")


def _first_param_is_an_instance_param(params):
    return len(params) > 0 and list(params)[0] in self_names


# TODO: Add validation of func: That all but perhaps 1 argument (not counting self) has a default
def _has_unbound_self(func):
    """

    Args:
        func:

    Returns:

    >>> def f1(x): ...
    >>> assert _has_unbound_self(f1) == 0
    >>>
    >>> def f2(self, x): ...
    >>> assert _has_unbound_self(f2) == 1
    >>>
    >>> f3 = lambda self, x: True
    >>> assert _has_unbound_self(f3) == 1
    >>>
    >>> class A:
    ...     def bar(self, x): ...
    ...     def foo(dacc, x): ...
    >>> a = A()
    >>>
    >>> _has_unbound_self(a.bar)
    0
    >>> _has_unbound_self(a.foo)
    0
    >>> _has_unbound_self(A.bar)
    1
    >>> _has_unbound_self(A.foo)
    0
    >>>
    """
    try:
        params = signature(func).parameters
    except ValueError:
        # If there was a problem getting the signature, assume it's a signature-less builtin (so not a bound method)
        return False
    if len(params) == 0:
        # no argument, so we can't be wrapping anything!!!
        raise ValueError(
            "The function has no parameters, so I can't guess which one you want to wrap"
        )
    elif not _is_bound(func) and _first_param_is_an_instance_param(params):
        return True
    else:
        return False


def transparent_key_method(self, k):
    return k


def mk_kv_reader_from_kv_collection(
        kv_collection, name=None, getitem=transparent_key_method
):
    """Make a KvReader class from a Collection class.

    Args:
        kv_collection: The Collection class
        name: The name to give the KvReader class (by default, it will be kv_collection.__qualname__ + 'Reader')
        getitem: The method that will be assigned to __getitem__. Should have the (self, k) signature.
            By default, getitem will be transparent_key_method, returning the key as is.
            This default is useful when you want to delegate the actual getting to a _obj_of_data wrapper.

    Returns: A KvReader class that subclasses the input kv_collection
    """

    name = name or kv_collection.__qualname__ + "Reader"
    reader_cls = type(
        name, (kv_collection, KvReader), {"__getitem__": getitem}
    )
    return reader_cls


def raise_disabled_error(functionality):
    def disabled_function(*args, **kwargs):
        raise ValueError(f"{functionality} is disabled")

    return disabled_function


def disable_delitem(o):
    if hasattr(o, "__delitem__"):
        o.__delitem__ = raise_disabled_error("deletion")
    return o


def disable_setitem(o):
    if hasattr(o, "__setitem__"):
        o.__setitem__ = raise_disabled_error("writing")
    return o


def mk_read_only(o):
    return disable_delitem(disable_setitem(o))


def is_iterable(x):
    return isinstance(x, Iterable)


def add_ipython_key_completions(store):
    """Add tab completion that shows you the keys of the store.
    Note: ipython already adds local path listing automatically,
     so you'll still get those along with your valid store keys.
    """

    def _ipython_key_completions_(self):
        return self.keys()

    if isinstance(store, type):
        store._ipython_key_completions_ = _ipython_key_completions_
    else:
        setattr(
            store,
            "_ipython_key_completions_",
            types.MethodType(_ipython_key_completions_, store),
        )
    return store


from py2store.util import copy_attrs
from py2store.errors import OverWritesNotAllowedError


def disallow_overwrites(store, *, error_msg=None, disable_deletes=True):
    assert isinstance(store, type), "store needs to be a type"
    if hasattr(store, "__setitem__"):

        def __setitem__(self, k, v):
            if k in self:
                raise OverWritesNotAllowedError(
                    "key {} already exists and cannot be overwritten. "
                    "If you really want to write to that key, delete it before writing".format(
                        k
                    )
                )
            return super().__setitem__(k, v)


class OverWritesNotAllowedMixin:
    """Mixin for only allowing a write to a key if they key doesn't already exist.
    Note: Should be before the persister in the MRO.

    >>> class TestPersister(OverWritesNotAllowedMixin, dict):
    ...     pass
    >>> p = TestPersister()
    >>> p['foo'] = 'bar'
    >>> #p['foo'] = 'bar2'  # will raise error
    >>> p['foo'] = 'this value should not be stored' # doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
      ...
    py2store.errors.OverWritesNotAllowedError: key foo already exists and cannot be overwritten.
        If you really want to write to that key, delete it before writing
    >>> p['foo']  # foo is still bar
    'bar'
    >>> del p['foo']
    >>> p['foo'] = 'this value WILL be stored'
    >>> p['foo']
    'this value WILL be stored'
    """

    @staticmethod
    def wrap(cls):
        # TODO: Consider moving to trans and making instances wrappable too
        class NoOverWritesClass(OverWritesNotAllowedMixin, cls):
            ...

        copy_attrs(
            NoOverWritesClass, cls, ("__name__", "__qualname__", "__module__")
        )
        return NoOverWritesClass

    def __setitem__(self, k, v):
        if self.__contains__(k):
            raise OverWritesNotAllowedError(
                "key {} already exists and cannot be overwritten. "
                "If you really want to write to that key, delete it before writing".format(
                    k
                )
            )
        return super().__setitem__(k, v)


########################################################################################################################
# Caching keys

# TODO: If a read-one-by-one (vs the current read all implementation) is necessary one day,
#   see https://github.com/zahlman/indexify/blob/master/src/indexify.py for ideas
#   but probably buffered (read by chunks) version of the later is better.
@store_decorator
def cached_keys(
        store=None,
        *,
        keys_cache: Union[callable, Collection] = list,
        iter_to_container=None,  # deprecated: use keys_cache instead
        cache_update_method="update",
        name: str = None,  # TODO: might be able to be deprecated since included in store_decorator
        __module__=None,  # TODO: might be able to be deprecated since included in store_decorator
) -> Union[callable, KvReader]:
    """Make a class that wraps input class's __iter__ becomes cached.

    Quite often we have a lot of keys, that we get from a remote data source, and don't want to have to ask for
    them again and again, having them be fetched, sent over the network, etc.
    So we need caching.

    But this caching is not the typical read caching, since it's __iter__ we want to cache, and that's a generator.
    So we'll implement a store class decorator specialized for this.

    The following decorator, when applied to a class (that has an __iter__), will perform the __iter__ code, consuming
    all items of the generator and storing them in _keys_cache, and then will yield from there every subsequent call.

    It is assumed, if you're using the cached_keys transformation, that you're dealing with static data
    (or data that can be considered static for the life of the store -- for example, when conducting analytics).
    If you ever need to refresh the cache during the life of the store, you can to delete _keys_cache like this:
    ```
    del your_store._keys_cache
    ```
    Once you do that, the next time you try to ask something about the contents of the store, it will actually do
    a live query again, as for the first time.

    Note: The default keys_cache is list though in many cases, you'd probably should use set, or an explicitly
    computer set instead. The reason list is used as the default is because (1) we didn't want to assume that
    order did not matter (maybe it does to you) and (2) we didn't want to assume that your keys were hashable.
    That said, if you're keys are hashable, and order does not matter, use set. That'll give you two things:
    (a) your `key in store` checks will be faster (O(1) instead of O(n)) and (b) you'll enforce unicity of keys.

    Know also that if you precompute the keys you want to cache with a container that has an update
    method (by default `update`) your cache updates will be faster and if the container you use has
    a `remove` method, you'll be able to delete as well.

    Args:
        store: The store instance or class to wrap (must have an __iter__), or None if you want a decorator.
        keys_cache: An explicit collection of keys
        iter_to_container: The function that will be applied to existing __iter__() and assigned to cache.
            The default is list. Another useful one is the sorted function.
        cache_update_method: Name of the keys_cache update method to use, if it is an attribute of keys_cache.
            Note that this cache_update_method will be used only
                if keys_cache is an explicit iterable and has that attribute
                if keys_cache is a callable and has that attribute.
            The default None
        name: The name of the new class

    Returns:
        If store is:
            None: Will return a decorator that can be applied to a store
            a store class: Will return a wrapped class that caches it's keys
            a store instance: Will return a wrapped instance that caches it's keys

        The instances of such key-cached classes have some extra attributes:
            _explicit_keys: The actual cache. An iterable container
            update_keys_cache: Is called if a user uses the instance to mutate the store (i.e. write or delete).

    You have two ways of caching keys:
    - By providing the explicit list of keys you want cache (and use)
    - By providing a callable that will iterate through your store and collect an explicit list of keys

    Let's take a simple dict as our original store.
    >>> source = dict(c=3, b=2, a=1)

    Specify an iterable, and it will be used as the cached keys
    >>> cached = cached_keys(source, keys_cache='bc')
    >>> list(cached.items())  # notice that the order you get things is also ruled by the cache
    [('b', 2), ('c', 3)]

    Specify a callable, and it will apply it to the existing keys to make your cache
    >>> list(cached_keys(source, keys_cache=sorted))
    ['a', 'b', 'c']

    You can use the callable keys_cache specification to filter as well!
    Oh, and let's demo the fact that if you don't specify the store, it will make a store decorator for you:
    >>> cache_my_keys = cached_keys(keys_cache=lambda keys: list(filter(lambda k: k >= 'b', keys)))
    >>> d = cache_my_keys(source)  # used as to transform an instance
    >>> list(d)
    ['c', 'b']

    Let's use that same `cache_my_keys` to decorate a class instead:
    >>> cached_dict = cache_my_keys(dict)
    >>> d = cached_dict(c=3, b=2, a=1)
    >>> list(d)
    ['c', 'b']

    Note that there's still an underlying store (dict) that has the data:
    >>> repr(d)  # repr isn't wrapped, so you can still see your underlying dict
    "{'c': 3, 'b': 2, 'a': 1}"

    And yes, you can still add elements,
    >>> d['z'] = 26
    >>> list(d.items())
    [('c', 3), ('b', 2), ('z', 26)]

    do bulk updates,
    >>> d.update({'more': 'of this'}, more_of='that')
    >>> list(d.items())
    [('c', 3), ('b', 2), ('z', 26), ('more', 'of this'), ('more_of', 'that')]

    and delete...
    >>> del d['more']
    >>> list(d.items())
    [('c', 3), ('b', 2), ('z', 26), ('more_of', 'that')]

    But careful! Know what you're doing if you try to get creative. Have a look at this:
    >>> d['a'] = 100  # add an 'a' item
    >>> d.update(and_more='of that')  # update to add yet another item
    >>> list(d.items())
    [('c', 3), ('b', 2), ('z', 26), ('more_of', 'that')]

    Indeed: No 'a' or 'and_more'.

    Now... they were indeed added. Or to be more precise, the value of the already existing a was changed,
    and a new ('and_more', 'of that') item was indeed added in the underlying store:
    >>> repr(d)
    "{'c': 3, 'b': 2, 'a': 100, 'z': 26, 'more_of': 'that', 'and_more': 'of that'}"

    But you're not seeing it.

    Why?

    Because you chose to use a callable keys_cache that doesn't have an 'update' method.
    When your _keys_cache attribute (the iterable cache) is not updatable itself, the
    way updates work is that we iterate through the underlying store (where the updates actually took place),
    and apply the keys_cache (callable) to that iterable.

    So what happened here was that you have your new 'a' and 'and_more' items, but your cached version of the
    store doesn't see it because it's filtered out. On the other hand, check out what happens if you have
    an updateable cache.

    Using `set` instead of `list`, after the `filter`.

    >>> cache_my_keys = cached_keys(keys_cache=set)
    >>> d = cache_my_keys(source)  # used as to transform an instance
    >>> sorted(d)  # using sorted because a set's order is not always the same
    ['a', 'b', 'c']
    >>> d['a'] = 100
    >>> d.update(and_more='of that')  # update to add yet another item
    >>> sorted(d.items())
    [('a', 100), ('and_more', 'of that'), ('b', 2), ('c', 3)]

    This example was to illustrate a more subtle aspect of cached_keys. You would probably deal with
    the filter concern in a different way in this case. But the rope is there -- it's your choice on how
    to use it.

    And here's some more examples if that wasn't enough!

    >>> # Lets cache the keys of a dict.
    >>> cached_dict = cached_keys(dict)
    >>> d = cached_dict(a=1, b=2, c=3)
    >>> # And you get a store that behaves as expected (but more speed and RAM)
    >>> list(d)
    ['a', 'b', 'c']
    >>> list(d.items())  # whether you iterate with .keys(), .values(), or .items()
    [('a', 1), ('b', 2), ('c', 3)]

    This is where the keys are stored:
    >>> d._keys_cache
    ['a', 'b', 'c']

    >>> # Let's demo the iter_to_container argument. The default is "list", which will just consume the iter in order
    >>> sorted_dict = cached_keys(dict, keys_cache=list)
    >>> s = sorted_dict({'b': 3, 'a': 2, 'c': 1})
    >>> list(s)  # keys will be in the order they were defined
    ['b', 'a', 'c']
    >>> sorted_dict = cached_keys(dict, keys_cache=sorted)
    >>> s = sorted_dict({'b': 3, 'a': 2, 'c': 1})
    >>> list(s)  # keys will be sorted
    ['a', 'b', 'c']
    >>> sorted_dict = cached_keys(dict, keys_cache=lambda x: sorted(x, key=len))
    >>> s = sorted_dict({'bbb': 3, 'aa': 2, 'c': 1})
    >>> list(s)  # keys will be sorted according to their length
    ['c', 'aa', 'bbb']

    If you change the keys (adding new ones with __setitem__ or update, or removing with pop or popitem)
    then the cache is recomputed (the first time you use an operation that iterates over keys)
    >>> d.update(d=4)  # let's add an element (try d['d'] = 4 as well)
    >>> list(d)
    ['a', 'b', 'c', 'd']
    >>> d['e'] = 5
    >>> list(d.items())  # whether you iterate with .keys(), .values(), or .items()
    [('a', 1), ('b', 2), ('c', 3), ('d', 4), ('e', 5)]

    >>> @cached_keys
    ... class A:
    ...     def __iter__(self):
    ...         yield from [1, 2, 3]
    >>> # Note, could have also used this form: AA = cached_keys(A)
    >>> a = A()
    >>> list(a)
    [1, 2, 3]
    >>> a._keys_cache = ['a', 'b', 'c']  # changing the cache, to prove that subsequent listing will read from there
    >>> list(a)  # proof:
    ['a', 'b', 'c']
    >>>

    >>> # Let's demo the iter_to_container argument. The default is "list", which will just consume the iter in order
    >>> sorted_dict = cached_keys(dict, keys_cache=list)
    >>> s = sorted_dict({'b': 3, 'a': 2, 'c': 1})
    >>> list(s)  # keys will be in the order they were defined
    ['b', 'a', 'c']
    >>> sorted_dict = cached_keys(dict, keys_cache=sorted)
    >>> s = sorted_dict({'b': 3, 'a': 2, 'c': 1})
    >>> list(s)  # keys will be sorted
    ['a', 'b', 'c']
    >>> sorted_dict = cached_keys(dict, keys_cache=lambda x: sorted(x, key=len))
    >>> s = sorted_dict({'bbb': 3, 'aa': 2, 'c': 1})
    >>> list(s)  # keys will be sorted according to their length
    ['c', 'aa', 'bbb']
    """
    if iter_to_container is not None:
        assert callable(iter_to_container)
        warn(
            "The argument name 'iter_to_container' is being deprecated in favor of the more general 'keys_cache'"
        )
        # assert keys_cache == iter_to_container

    assert isinstance(store, type), f"store_cls must be a type, was a {type(store)}: {store}"

    # name = name or 'IterCached' + get_class_name(store_cls)
    name = name or get_class_name(store)
    __module__ = __module__ or getattr(store, "__module__", None)

    class cached_cls(store):
        _keys_cache = None

    cached_cls.__name__ = name

    # cached_cls = type(name, (store_cls,), {"_keys_cache": None})

    # The following class is not the class that will be returned, but the class from which we'll take the methods
    #   that will be copied in the class that will be returned.
    @_define_keys_values_and_items_according_to_iter
    class CachedIterMethods:
        _explicit_keys = False
        _updatable_cache = False
        _iter_to_container = None
        if hasattr(keys_cache, cache_update_method):
            _updatable_cache = True
        if is_iterable(
                keys_cache
        ):  # if keys_cache is iterable, it is the cache instance itself.
            _keys_cache = keys_cache
            _explicit_keys = True
        elif callable(keys_cache):
            # if keys_cache is not iterable, but callable, we'll use it to make the keys_cache from __iter__
            _iter_to_container = keys_cache

            @lazyprop
            def _keys_cache(self):
                # print(iter_to_container)
                return keys_cache(
                    super(cached_cls, self).__iter__()
                )  # TODO: Should it be iter(super(...)?

        # if not callable(_explicit_keys):

        # If keys_cache_update is None (the default), the method 'update' will be searched for as above,
        #   and if not found, will fall back to None.
        # if isinstance(keys_cache_update, str):
        #     if (_explicit_keys and hasattr(_explicit_keys, '__class__')
        #             and hasattr(_explicit_keys.__class__, keys_cache_update)):
        #         keys_cache_update = getattr(_explicit_keys.__class__, keys_cache_update)

        # if (_explicit_keys and hasattr(_explicit_keys, '__class__')
        #         and hasattr(_explicit_keys.__class__, 'update')):
        #     keys_cache_update = _explicit_keys.__class__.update
        #

        @property
        def _iter_cache(self):  # for back-compatibility
            warn(
                "The new name for `_iter_cache` is `_keys_cache`. Start using that!",
                DeprecationWarning,
            )
            return self._keys_cache

        def __iter__(self):
            # if getattr(self, '_keys_cache', None) is None:
            #     self._keys_cache = iter_to_container(super(cached_cls, self).__iter__())
            yield from self._keys_cache

        def __len__(self):
            return len(self._keys_cache)

        def items(self):
            for k in self._keys_cache:
                yield k, self[k]

        def __contains__(self, k):
            return k in self._keys_cache

        # The write and update stuff ###################################################################

        if _updatable_cache:

            def update_keys_cache(self, keys):
                """updates the keys by calling the
                """
                update_func = getattr(
                    self._keys_cache, cache_update_method
                )
                update_func(self._keys_cache, keys)

            update_keys_cache.__doc__ = (
                "Updates the _keys_cache by calling its {} method"
            )
        else:

            def update_keys_cache(self, keys):
                """Updates the _keys_cache by deleting the attribute
                """
                try:
                    del self._keys_cache
                    # print('deleted _keys_cache')
                except AttributeError:
                    pass

        def __setitem__(self, k, v):
            super(cached_cls, self).__setitem__(k, v)
            # self.store[k] = v
            if (
                    k not in self
            ):  # just to avoid deleting the cache if we already had the key
                self.update_keys_cache((k,))
                # Note: different construction performances: (k,)->10ns, [k]->38ns, {k}->50ns

        def update(self, other=(), **kwds):
            # print(other, kwds)
            # super(cached_cls, self).update(other, **kwds)
            super_setitem = super(cached_cls, self).__setitem__
            for k in other:
                # print(k, other[k])
                super_setitem(k, other[k])
                # self.store[k] = other[k]
            self.update_keys_cache(other)

            for k, v in kwds.items():
                # print(k, v)
                super_setitem(k, v)
                # self.store[k] = v
            self.update_keys_cache(kwds)

        def __delitem__(self, k):
            self._keys_cache.remove(k)
            super(cached_cls, self).__delitem__(k)

    # And this is where we add all the needed methods (for example, no __setitem__ won't be added if the original
    #   class didn't have one in the first place.
    special_attrs = {
        "update_keys_cache",
        "_keys_cache",
        "_explicit_keys",
        "_updatable_cache",
    }
    for attr in special_attrs | (
            AttrNames.KvPersister
            & attrs_of(cached_cls)
            & attrs_of(CachedIterMethods)
    ):
        setattr(cached_cls, attr, getattr(CachedIterMethods, attr))

    if __module__ is not None:
        cached_cls.__module__ = __module__

    if hasattr(store, '__doc__'):
        cached_cls.__doc__ = store.__doc__

    return cached_cls


cache_iter = cached_keys  # TODO: Alias, partial it and make it more like the original, for back compatibility.


@store_decorator
def catch_and_cache_error_keys(
        store=None,
        *,
        errors_caught=Exception,
        error_callback=None,
        use_cached_keys_after_completed_iter=True,
):
    """Store that will cache keys as they're accessed, separating those that raised errors and those that didn't.
    Getting a key will still through an error, but the access attempts will be collected in an ._error_keys attribute.
    Successfful attemps will be stored in _keys_cache.
    Retrieval iteration (items() or values()) will on the other hand, skip the error (while still caching it).
    If the iteration completes (and use_cached_keys_after_completed_iter), the use_cached_keys flag is turned on,
    which will result in the store now getting it's keys from the _keys_cache.

    >>> @catch_and_cache_error_keys(
    ...     error_callback=lambda store, key, err: print(f"Error with {key} key: {err}"))
    ... class Blacklist(dict):
    ...     _black_list = {'black', 'list'}
    ...
    ...     def __getitem__(self, k):
    ...         if k not in self._black_list:
    ...             return super().__getitem__(k)
    ...         else:
    ...             raise KeyError(f"Nope, that's from the black list!")
    >>>
    >>> s = Blacklist(black=7,  friday=20, frenzy=13)
    >>> list(s)
    ['black', 'friday', 'frenzy']
    >>> list(s.items())
    Error with black key: "Nope, that's from the black list!"
    [('friday', 20), ('frenzy', 13)]
    >>> sorted(s)  # sorting to get consistent output
    ['frenzy', 'friday']


    See that? First we had three keys, then we iterated and got only 2 items (fortunately,
    we specified an ``error_callback`` so we ccould see that the iteration actually dropped a key).
    That's strange. And even stranger is the fact that when we list our keys again, we get only two.

    You don't like it? Neither do I. But
    - It's not a completely outrageous behavior -- if you're talking to live data, it
        often happens that you get more, or less, from one second to another.
    - This store isn't meant to be long living, but rather meant to solve the problem of skiping
        items that are problematic (for example, malformatted files), with a trace of
        what was skipped and what's valid (in case we need to iterate again and don't want to
        bear the hit of requesting values for keys we already know are problematic.

    Here's a little peep of what is happening under the hood.
    Meet ``_keys_cache`` and ``_error_keys`` sets (yes, unordered -- so know it) that are meant
    to acccumulate valid and problematic keys respectively.

    >>> s = Blacklist(black=7,  friday=20, frenzy=13)
    >>> list(s)
    ['black', 'friday', 'frenzy']
    >>> s._keys_cache, s._error_keys
    (set(), set())
    >>> s['friday']
    20
    >>> s._keys_cache, s._error_keys
    ({'friday'}, set())
    >>> s['black']
    Traceback (most recent call last):
      ...
    KeyError: "Nope, that's from the black list!"
    >>> s._keys_cache, s._error_keys
    ({'friday'}, {'black'})

    But see that we still have the full list:

    >>> list(s)
    ['black', 'friday', 'frenzy']

    Meet ``use_cached_keys``: He's the culprit. It's a flag that indicates whether we should be
    using the cached keys or not. Obviously, it'll start off being ``False``:

    >>> s.use_cached_keys
    False

    Now we could set it to ``True`` manually to change the mode.
    But know that this switch happens automatically (UNLESS you specify otherwise by saying:
    ``use_cached_keys_after_completed_iter=False``) when ever you got through a
    VALUE-PRODUCING iteration (i.e. entirely consuming `items()` or `values()`).

    >>> sorted(s.values())  # sorting to get consistent output
    Error with black key: "Nope, that's from the black list!"
    [13, 20]

    """

    assert isinstance(store, type), f"store_cls must be a type, was a {type(store)}: {store}"

    # assert isinstance(store, Mapping), f"store_cls must be a Mapping. Was not. mro is {store.mro()}: {store}"

    # class cached_cls(store):
    #     _keys_cache = None
    #     _error_keys = None

    # The following class is not the class that will be returned, but the class from which we'll take the methods
    #   that will be copied in the class that will be returned.
    # @_define_keys_values_and_items_according_to_iter
    class CachedKeyErrorsStore(store):

        @wraps(store.__init__)
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._error_keys = set()
            self._keys_cache = set()
            self.use_cached_keys = False
            self.use_cached_keys_after_completed_iter = use_cached_keys_after_completed_iter
            self.errors_caught = errors_caught
            self.error_callback = error_callback

        def __getitem__(self, k):
            if self.use_cached_keys:
                return super().__getitem__(k)
            else:
                try:
                    v = super().__getitem__(k)
                    self._keys_cache.add(k)
                    return v
                except self.errors_caught:
                    self._error_keys.add(k)
                    raise

        def __iter__(self):
            # if getattr(self, '_keys_cache', None) is None:
            #     self._keys_cache = iter_to_container(super(cached_cls, self).__iter__())
            if self.use_cached_keys:
                yield from self._keys_cache
            else:
                yield from super().__iter__()

        def __len__(self):
            if self.use_cached_keys:
                return len(self._keys_cache)
            else:
                return super().__len__()

        def items(self):
            if self.use_cached_keys:
                for k in self._keys_cache:
                    yield k, self[k]
            else:
                for k in self:
                    try:
                        yield k, self[k]
                    except self.errors_caught as err:
                        if self.error_callback is not None:
                            self.error_callback(store, k, err)
            if self.use_cached_keys_after_completed_iter:
                self.use_cached_keys = True

        def values(self):
            if self.use_cached_keys:
                yield from (self[k] for k in self._keys_cache)
            else:
                yield from (v for k, v in self.items())

        def __contains__(self, k):
            if self.use_cached_keys:
                return k in self._keys_cache
            else:
                return super().__contains__(k)

    return CachedKeyErrorsStore


def iterate_values_and_accumulate_non_error_keys(
        store,
        cache_keys_here: list,
        errors_caught=Exception,
        error_callback=None
):
    for k in store:
        try:
            v = store[k]
            cache_keys_here.append(k)
            yield v
        except errors_caught as err:
            if error_callback is not None:
                error_callback(store, k, err)


########################################################################################################################
# Filtering iteration


def take_everything(key):
    return True


# TODO: Factor out the method injection pattern (e.g. __getitem__, __setitem__ and __delitem__ are nearly identical)
@store_decorator
def filt_iter(
        store=None, *,
        filt: Union[callable, Iterable] = take_everything,
        name=None, __module__=None  # TODO: might be able to be deprecated since included in store_decorator
):
    """Make a wrapper that will transform a store (class or instance thereof) into a sub-store (i.e. subset of keys).

    Args:
        filt: A callable or iterable:
            callable: Boolean filter function. A func taking a key and and returns True iff the key should be included.
            iterable: The collection of keys you want to filter "in"
        name: The name to give the wrapped class

    Returns: A wrapper (that then needs to be applied to a store instance or class.

    >>> filtered_dict = filt_iter(filt=lambda k: (len(k) % 2) == 1)(dict)  # keep only odd length keys
    >>>
    >>> s = filtered_dict({'a': 1, 'bb': object, 'ccc': 'a string', 'dddd': [1, 2]})
    >>>
    >>> list(s)
    ['a', 'ccc']
    >>> 'a' in s  # True because odd (length) key
    True
    >>> 'bb' in s  # False because odd (length) key
    False
    >>> assert s.get('bb', None) == None
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

    # if store is None:
    if not callable(filt):  # if filt is not a callable...
        # ... assume it's the collection of keys you want and make a filter function to filter those "in".
        assert next(
            iter(filt)
        ), "filt should be a callable, or an iterable"
        keys_that_should_be_filtered_in = set(filt)

        def filt(k):
            return k in keys_that_should_be_filtered_in

    __module__ = __module__ or getattr(store, "__module__", None)

    name = name or "Filtered" + get_class_name(store)
    wrapped_cls = type(name, (store,), {})

    def __iter__(self):
        yield from filter(
            filt, super(wrapped_cls, self).__iter__()
        )

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

    if hasattr(wrapped_cls, "__getitem__"):

        def __getitem__(self, k):
            if filt(k):
                return super(wrapped_cls, self).__getitem__(k)
            else:
                raise KeyError(f"Key not in store: {k}")

        wrapped_cls.__getitem__ = __getitem__

    if hasattr(wrapped_cls, "get"):

        def get(self, k, default=None):
            if filt(k):
                return super(wrapped_cls, self).get(k, default)
            else:
                return default

        wrapped_cls.get = get

    if hasattr(wrapped_cls, "__setitem__"):

        def __setitem__(self, k, v):
            if filt(k):
                return super(wrapped_cls, self).__setitem__(k, v)
            else:
                raise KeyError(f"Key not in store: {k}")

        wrapped_cls.__setitem__ = __setitem__

    if hasattr(wrapped_cls, "__delitem__"):

        def __delitem__(self, k):
            if filt(k):
                return super(wrapped_cls, self).__delitem__(k)
            else:
                raise KeyError(f"Key not in store: {k}")

        wrapped_cls.__delitem__ = __delitem__

    # if __module__ is not None:
    #     wrapped_cls.__module__ = __module__
    #
    # if hasattr(collection_cls, '__doc__'):
    #     wrapped_cls.__doc__ = store.__doc__

    return wrapped_cls


########################################################################################################################
# Wrapping keys and values

self_names = frozenset(["self", "store"])


def _define_keys_values_and_items_according_to_iter(cls):
    if hasattr(cls, "keys"):
        def keys(self):
            # yield from self.__iter__()  # TODO: Should it be iter(self)?
            return KeysView(self)

        cls.keys = keys

    if hasattr(cls, "values"):
        def values(self):
            # yield from (self[k] for k in self)
            return ValuesView(self)

        cls.values = values

    if hasattr(cls, "items"):
        def items(self):
            # yield from ((k, self[k]) for k in self)
            return ItemsView(self)

        cls.items = items

    return cls


# TODO: would like to keep dict_keys methods (like __sub__, isdisjoint). How do I do so?
class _DefineKeysValuesAndItemsAccordingToIter:
    def keys(self):
        yield from self.__iter__()  # TODO: Should it be iter(self)?

    def values(self):
        yield from (self[k] for k in self)

    def items(self):
        yield from ((k, self[k]) for k in self)


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
    <class 'abc.dictPWrapped'>
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

    name = name or (persister_cls.__qualname__ + "PWrapped")

    cls = type(name, (Store,), {})

    # TODO: Investigate sanity and alternatives (cls = type(name, (Store, persister_cls), {}) leads to MRO problems)
    for attr in set(dir(persister_cls)) - set(dir(Store)):
        persister_cls_attribute = getattr(persister_cls, attr)
        setattr(cls, attr, persister_cls_attribute)  # copy the attribute over to cls

    if hasattr(persister_cls, '__doc__'):
        cls.__doc__ = persister_cls.__doc__

    @wraps(persister_cls.__init__)
    def __init__(self, *args, **kwargs):
        super(cls, self).__init__(persister_cls(*args, **kwargs))

    cls.__init__ = __init__

    return cls


def _wrap_outcoming(
        store_cls: type, wrapped_method: str, trans_func: Optional[callable] = None
):
    """Output-transforming wrapping of the wrapped_method of store_cls.
    The transformation is given by trans_func, which could be a one (trans_func(x)
    or two (trans_func(self, x)) argument function.

    Args:
        store_cls: The class that will be transformed
        wrapped_method: The method (name) that will be transformed.
        trans_func: The transformation function.
        wrap_arg_idx: The index of the

    Returns: Nothing. It transforms the class in-place

    >>> from py2store.trans import store_wrap
    >>> S = store_wrap(dict)
    >>> _wrap_outcoming(S, '_key_of_id', lambda x: f'wrapped_{x}')
    >>> s = S({'a': 1, 'b': 2})
    >>> list(s)
    ['wrapped_a', 'wrapped_b']
    >>> _wrap_outcoming(S, '_key_of_id', lambda self, x: f'wrapped_{x}')
    >>> s = S({'a': 1, 'b': 2}); assert list(s) == ['wrapped_a', 'wrapped_b']
    >>> class A:
    ...     def __init__(self, prefix='wrapped_'):
    ...         self.prefix = prefix
    ...     def _key_of_id(self, x):
    ...         return self.prefix + x
    >>> _wrap_outcoming(S, '_key_of_id', A(prefix='wrapped_')._key_of_id)
    >>> s = S({'a': 1, 'b': 2}); assert list(s) == ['wrapped_a', 'wrapped_b']
    >>>
    >>> S = store_wrap(dict)
    >>> _wrap_outcoming(S, '_obj_of_data', lambda x: x * 7)
    >>> s = S({'a': 1, 'b': 2})
    >>> list(s.values())
    [7, 14]
    """
    if trans_func is not None:
        wrapped_func = getattr(store_cls, wrapped_method)

        if not _has_unbound_self(trans_func):
            # print(f"00000: {store_cls}: {wrapped_method}, {trans_func}, {wrapped_func}, {wrap_arg_idx}")
            @wraps(wrapped_func)
            def new_method(self, x):
                # # Long form (for explanation)
                # super_method = getattr(super(store_cls, self), wrapped_method)
                # output_of_super_method = super_method(x)
                # transformed_output_of_super_method = trans_func(output_of_super_method)
                # return transformed_output_of_super_method
                return trans_func(
                    getattr(super(store_cls, self), wrapped_method)(x)
                )

        else:
            # print(f"11111: {store_cls}: {wrapped_method}, {trans_func}, {wrapped_func}, {wrap_arg_idx}")
            @wraps(wrapped_func)
            def new_method(self, x):
                # # Long form (for explanation)
                # super_method = getattr(super(store_cls, self), wrapped_method)
                # output_of_super_method = super_method(x)
                # transformed_output_of_super_method = trans_func(self, output_of_super_method)
                # return transformed_output_of_super_method
                return trans_func(
                    self, getattr(super(store_cls, self), wrapped_method)(x)
                )

        setattr(store_cls, wrapped_method, new_method)


def _wrap_ingoing(
        store_cls, wrapped_method: str, trans_func: Optional[callable] = None
):
    if trans_func is not None:
        wrapped_func = getattr(store_cls, wrapped_method)

        if not _has_unbound_self(trans_func):

            @wraps(wrapped_func)
            def new_method(self, x):
                return getattr(super(store_cls, self), wrapped_method)(
                    trans_func(x)
                )

        else:

            @wraps(wrapped_func)
            def new_method(self, x):
                return getattr(super(store_cls, self), wrapped_method)(
                    trans_func(self, x)
                )

        setattr(store_cls, wrapped_method, new_method)


@store_decorator
def wrap_kvs(
        store=None,
        *,
        name=None,
        key_of_id=None,
        id_of_key=None,
        obj_of_data=None,
        data_of_obj=None,
        preset=None,
        postget=None,
        __module__=None,
        outcoming_key_methods=(),
        outcoming_value_methods=(),
        ingoing_key_methods=(),
        ingoing_value_methods=(),
):
    r"""Make a Store that is wrapped with the given key/val transformers.

    Naming convention:
        Morphemes:
            key: outer key
            _id: inner key
            obj: outer value
            data: inner value
        Grammar:
            Y_of_X: means that you get a Y output when giving an X input. Also known as X_to_Y.


    Args:
        store: Store class or instance
        name: Name to give the wrapper class
        key_of_id: The outcoming key transformation function.
            Forms are `k = key_of_id(_id)` or `k = key_of_id(self, _id)`
        id_of_key: The ingoing key transformation function.
            Forms are `_id = id_of_key(k)` or `_id = id_of_key(self, k)`
        obj_of_data: The outcoming val transformation function.
            Forms are `obj = obj_of_data(data)` or `obj = obj_of_data(self, data)`
        data_of_obj: The ingoing val transformation function.
            Forms are `data = data_of_obj(obj)` or `data = data_of_obj(self, obj)`
        preset: A function that is called before doing a `__setitem__`.
            The function is called with both `k` and `v` as inputs, and should output a transformed value.
            The intent use is to do ingoing value transformations conditioned on the key.
            For example, you may want to serialize an object depending on if you're writing to a
             '.csv', or '.json', or '.pickle' file.
            Forms are `preset(k, obj)` or `preset(self, k, obj)`
        postget: A function that is called after the value `v` for a key `k` is be `__getitem__`.
            The function is called with both `k` and `v` as inputs, and should output a transformed value.
            The intent use is to do outcoming value transformations conditioned on the key.
            We already have `obj_of_data` for outcoming value trans, but cannot condition it's behavior on k.
            For example, you may want to deserialize the bytes of a '.csv', or '.json', or '.pickle' in different ways.
            Forms are `obj = postget(k, data)` or `obj = postget(self, k, data)`

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
    >>> A = wrap_kvs(dict, name='A',
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
    >>> B = wrap_kvs(dict, name='B', postget=lambda k, v: f'upper {v}' if k[0].isupper() else f'lower {v}')
    >>> b = B()
    >>> b['BIG'] = 'letters'
    >>> b['small'] = 'text'
    >>> list(b.items())
    [('BIG', 'upper letters'), ('small', 'lower text')]
    >>>
    >>>
    >>> # Let's try preset and postget. We'll wrap a dict and write the same list of lists object to
    >>> # keys ending with .csv, .json, and .pkl, specifying the obvious extension-dependent
    >>> # serialization/deserialization we want to associate with it.
    >>>
    >>> # First, some very simple csv transformation functions
    >>> to_csv = lambda LoL: '\\n'.join(map(','.join, map(lambda L: (x for x in L), LoL)))
    >>> from_csv = lambda csv: list(map(lambda x: x.split(','), csv.split('\\n')))
    >>> LoL = [['a','b','c'],['d','e','f']]
    >>> assert from_csv(to_csv(LoL)) == LoL
    >>>
    >>> import json, pickle
    >>>
    >>> def preset(k, v):
    ...     if k.endswith('.csv'):
    ...         return to_csv(v)
    ...     elif k.endswith('.json'):
    ...         return json.dumps(v)
    ...     elif k.endswith('.pkl'):
    ...         return pickle.dumps(v)
    ...     else:
    ...         return v  # as is
    ...
    ...
    >>> def postget(k, v):
    ...     if k.endswith('.csv'):
    ...         return from_csv(v)
    ...     elif k.endswith('.json'):
    ...         return json.loads(v)
    ...     elif k.endswith('.pkl'):
    ...         return pickle.loads(v)
    ...     else:
    ...         return v  # as is
    ...
    >>> mydict = wrap_kvs(dict, preset=preset, postget=postget)
    >>>
    >>> obj = [['a','b','c'],['d','e','f']]
    >>> d = mydict()
    >>> d['foo.csv'] = obj  # store the object as csv
    >>> d  # "printing" a dict by-passes the transformations, so we see the data in the "raw" format it is stored in.
    {'foo.csv': 'a,b,c\\nd,e,f'}
    >>> d['foo.csv']  # but if we actually ask for the data, it deserializes to our original object
    [['a', 'b', 'c'], ['d', 'e', 'f']]
    >>> d['bar.json'] = obj  # store the object as json
    >>> d
    {'foo.csv': 'a,b,c\\nd,e,f', 'bar.json': '[["a", "b", "c"], ["d", "e", "f"]]'}
    >>> d['bar.json']
    [['a', 'b', 'c'], ['d', 'e', 'f']]
    >>> d['bar.json'] = {'a': 1, 'b': [1, 2], 'c': 'normal json'}  # let's write a normal json instead.
    >>> d
    {'foo.csv': 'a,b,c\\nd,e,f', 'bar.json': '{"a": 1, "b": [1, 2], "c": "normal json"}'}
    >>> del d['foo.csv']
    >>> del d['bar.json']
    >>> d['foo.pkl'] = obj  # 'save' obj as pickle
    >>> d['foo.pkl']
    [['a', 'b', 'c'], ['d', 'e', 'f']]

    # TODO: Add tests for outcoming_key_methods etc.
    """
    name = name or store.__qualname__ + "Wrapped"

    # TODO: This is not the best way to handle this. Investigate another way. ######################
    global_names = set(globals()).union(locals())
    if name in global_names:
        raise NameError("That name is already in use")
    # TODO: ########################################################################################

    store_cls = kv_wrap_persister_cls(store, name=name)  # experiment
    store_cls._cls_trans = None

    # store_cls = type(name, (store,), {})
    # store_cls._cls_trans = None

    def cls_trans(store_cls: type):
        for method_name in {"_key_of_id"} | ensure_set(outcoming_key_methods):
            _wrap_outcoming(store_cls, method_name, key_of_id)

        for method_name in {"_obj_of_data"} | ensure_set(
                outcoming_value_methods
        ):
            _wrap_outcoming(store_cls, method_name, obj_of_data)

        for method_name in {"_id_of_key"} | ensure_set(ingoing_key_methods):
            _wrap_ingoing(store_cls, method_name, id_of_key)

        for method_name in {"_data_of_obj"} | ensure_set(
                ingoing_value_methods
        ):
            _wrap_ingoing(store_cls, method_name, data_of_obj)

        # TODO: postget and preset uses num_of_args. Not robust:
        #  Should only count args with no defaults or partial won't be able to be used to make postget/preset funcs
        # TODO: Extract postget and preset patterns?
        if postget is not None:
            if num_of_args(postget) < 2:
                raise ValueError(
                    "A postget function needs to have (key, value) or (self, key, value) arguments"
                )

            if not _has_unbound_self(postget):

                def __getitem__(self, k):
                    return postget(k, super(store_cls, self).__getitem__(k))

            else:

                def __getitem__(self, k):
                    return postget(
                        self, k, super(store_cls, self).__getitem__(k)
                    )

            store_cls.__getitem__ = __getitem__

        if preset is not None:
            if num_of_args(preset) < 2:
                raise ValueError(
                    "A preset function needs to have (key, value) or (self, key, value) arguments"
                )

            if not _has_unbound_self(preset):

                def __setitem__(self, k, v):
                    return super(store_cls, self).__setitem__(k, preset(k, v))

            else:

                def __setitem__(self, k, v):
                    return super(store_cls, self).__setitem__(
                        k, preset(self, k, v)
                    )

            store_cls.__setitem__ = __setitem__

        if __module__ is not None:
            store_cls.__module__ = __module__

        # add an attribute containing the cls_trans.
        # This is is both for debugging and introspection use,
        # as well as if we need to pass on the transformation in a recursive situation
        store_cls._cls_trans = cls_trans

        return store_cls

    return cls_trans(store_cls)


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

    # TODO: Asymmetric key trans breaks getting items (therefore items()). Resolve (remove items() for asym keys?)
    # >>> list(s.items())
    # [('foo', 10), ('bar', 'xo')]
    """

    def wrapper(o, name=None):
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_kr"
        )
        return wrap_kvs(o, name=name, key_of_id=trans_func)

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

    # TODO: Asymmetric key trans breaks getting items (therefore items()). Resolve (remove items() for asym keys?)
    # >>> list(s.items())
    # [('root/foo', 10), ('root/bar', 'xo')]
    """

    def wrapper(o, name=None):
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_kw"
        )
        return wrap_kvs(o, name=name, id_of_key=trans_func)

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
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_vr"
        )
        return wrap_kvs(o, name=name, obj_of_data=trans_func)

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
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_vw"
        )
        return wrap_kvs(o, name=name, data_of_obj=trans_func)

    return wrapper


def _ingoing_vals_wrt_to_keys(trans_func):
    def wrapper(o, name=None):
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_vwk"
        )
        return wrap_kvs(o, name=name, preset=trans_func)

    return wrapper


def _outcoming_vals_wrt_to_keys(trans_func):
    def wrapper(o, name=None):
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_vrk"
        )
        return wrap_kvs(o, name=name, postget=trans_func)

    return wrapper


def mk_trans_obj(**kwargs):
    """Convenience method to quickly make a trans_obj (just an object holding some trans functions"""
    # TODO: Could make this more flexible (assuming here only staticmethods) and validate inputs...
    return type(
        "TransObj", (), {k: staticmethod(v) for k, v in kwargs.items()}
    )()


def kv_wrap(trans_obj):
    """
    kv_wrap: A function that makes a wrapper (a decorator) that will get the wrappers from methods of the input object.

    kv_wrap also has attributes:
        outcoming_keys, ingoing_keys, outcoming_vals, ingoing_vals, and val_reads_wrt_to_keys
    which will only add a single specific wrapper (specified as a function), when that's what you need.

    """

    key_of_id = getattr(trans_obj, "_key_of_id", None)
    id_of_key = getattr(trans_obj, "_id_of_key", None)
    obj_of_data = getattr(trans_obj, "_obj_of_data", None)
    data_of_obj = getattr(trans_obj, "_data_of_obj", None)
    preset = getattr(trans_obj, "_preset", None)
    postget = getattr(trans_obj, "_postget", None)

    def wrapper(o, name=None):
        name = (
                name
                or getattr(o, "__qualname__", getattr(o.__class__, "__qualname__"))
                + "_kr"
        )
        return wrap_kvs(
            o,
            name=name,
            key_of_id=key_of_id,
            id_of_key=id_of_key,
            obj_of_data=obj_of_data,
            data_of_obj=data_of_obj,
            preset=preset,
            postget=postget,
        )

    return wrapper


kv_wrap.mk_trans_obj = mk_trans_obj  # to have a trans_obj maker handy
kv_wrap.outcoming_keys = _kv_wrap_outcoming_keys
kv_wrap.ingoing_keys = _kv_wrap_ingoing_keys
kv_wrap.outcoming_vals = _kv_wrap_outcoming_vals
kv_wrap.ingoing_vals = _kv_wrap_ingoing_vals
kv_wrap.ingoing_vals_wrt_to_keys = _ingoing_vals_wrt_to_keys
kv_wrap.outcoming_vals_wrt_to_keys = _outcoming_vals_wrt_to_keys


def mk_wrapper(wrap_cls):
    """

    You have a wrapper class and you want to make a wrapper out of it,
    that is, a decorator factory with which you can make wrappers, like this:
    ```
    wrapper = mk_wrapper(wrap_cls)
    ```
    that you can then use to transform stores like thiis:
    ```
    MyStore = wrapper(**wrapper_kwargs)(StoreYouWantToTransform)
    ```

    :param wrap_cls:
    :return:

    >>> class RelPath:
    ...     def __init__(self, root):
    ...         self.root = root
    ...         self._root_length = len(root)
    ...     def _key_of_id(self, _id):
    ...         return _id[self._root_length:]
    ...     def _id_of_key(self, k):
    ...         return self.root + k
    >>> relpath_wrap = mk_wrapper(RelPath)
    >>> RelDict = relpath_wrap(root='foo/')(dict)
    >>> s = RelDict()
    >>> s['bar'] = 42
    >>> assert list(s) == ['bar']
    >>> assert s['bar'] == 42
    >>> assert str(s) == "{'foo/bar': 42}"  # reveals that actually, behind the scenes, there's a "foo/" prefix
    """

    @wraps(wrap_cls)
    def wrapper(*args, **kwargs):
        return kv_wrap(wrap_cls(*args, **kwargs))

    return wrapper


@double_up_as_factory
def add_wrapper_method(wrap_cls=None, *, method_name="wrapper"):
    """Decorator that adds a wrapper method (itself a decorator) to a wrapping class
    Clear?
    See `mk_wrapper` function and doctest example if not.

    What `add_wrapper_method` does is just to add a `"wrapper"` method
    (or another name if you ask for it) to `wrap_cls`, so that you can use that
    class for it's purpose of transforming stores more conveniently.

    :param wrap_cls: The wrapper class (the definitioin of the transformation.
        If None, the functiion will make a decorator to decorate wrap_cls later
    :param method_name: The method name you want to use (default is 'wrapper')

    >>>
    >>> @add_wrapper_method
    ... class RelPath:
    ...     def __init__(self, root):
    ...         self.root = root
    ...         self._root_length = len(root)
    ...     def _key_of_id(self, _id):
    ...         return _id[self._root_length:]
    ...     def _id_of_key(self, k):
    ...         return self.root + k
    ...
    >>> RelDict = RelPath.wrapper(root='foo/')(dict)
    >>> s = RelDict()
    >>> s['bar'] = 42
    >>> assert list(s) == ['bar']
    >>> assert s['bar'] == 42
    >>> assert str(s) == "{'foo/bar': 42}"  # reveals that actually, behind the scenes, there's a "foo/" prefix
    """
    setattr(wrap_cls, method_name, mk_wrapper(wrap_cls))
    return wrap_cls


########################################################################################################################
# Aliasing

_method_name_for = {
    "write": "__setitem__",
    "read": "__getitem__",
    "delete": "__delitem__",
    "list": "__iter__",
    "count": "__len__",
}


@store_decorator
def add_path_get(store=None, *, name=None, path_type: type = tuple):
    """
    Make nested stores accessible through key paths.

    Say you have some nested stores.
    You know... like a `ZipFileReader` store whose values are `ZipReader`s,
    whose values are bytes of the zipped files (and you can go on... whose (json) values are...).

    Well, you can access any node of this nested tree of stores like this:

    ```
        MyStore[key_1][key_2][key_3]
    ```

    And that's fine. But maybe you'd like to do it this way instead:

    ```
        MyStore[key_1, key_2, key_3]
    ```

    Or like this:

    ```
        MyStore['key_1/key_2/key_3']
    ```

    Or this:

    ```
        MyStore['key_1.key_2.key_3']
    ```

    You get the point. This is what `add_path_get` is meant for.

    Args:
        store: The store (class or instance) you're wrapping.
            If not specified, the function will return a decorator.
        name: The name to give the class (not applicable to instance wrapping)
        path_type: The type that paths are expressed as. Needs to be an Iterable type. By default, a tuple.
            This is used to decide whether the key should be taken as a "normal" key of the store,
            or should be used to iterate through, recursively getting values.

    Returns: A wrapped store (class or instance), or a store wrapping decorator (if store is not specified)

    See Also: `py2store.key_mappers.paths.PathGetMixin`, `py2store.key_mappers.paths.KeyPath`

    >>> # wrapping an instance
    >>> s = add_path_get({'a': {'b': {'c': 42}}})
    >>> s['a']
    {'b': {'c': 42}}
    >>> s['a', 'b']
    {'c': 42}
    >>> s['a', 'b', 'c']
    42
    >>> # wrapping a class
    >>> S = add_path_get(dict)
    >>> s = S(a={'b': {'c': 42}})
    >>> assert s['a'] == {'b': {'c': 42}}; assert s['a', 'b'] == {'c': 42}; assert s['a', 'b', 'c'] == 42
    >>>
    >>> # using add_path_get as a decorator
    >>> @add_path_get
    ... class S(dict):
    ...    pass
    >>> s = S(a={'b': {'c': 42}})
    >>> assert s['a'] == {'b': {'c': 42}};
    >>> assert s['a', 'b'] == s['a']['b'];
    >>> assert s['a', 'b', 'c'] == s['a']['b']['c']
    >>>
    >>> # a different kind of path?
    >>> # You can choose a different path_type, but sometimes (say both keys and key paths are strings)
    >>> # you need to involve more tools. Like py2store.key_mappers.paths.KeyPath...
    >>> from py2store.key_mappers.paths import KeyPath
    >>> from py2store import kv_wrap
    >>> SS = kv_wrap(KeyPath(path_sep='.'))(S)
    >>> s = SS({'a': {'b': {'c': 42}}})
    >>> assert s['a'] == {'b': {'c': 42}}; assert s['a.b'] == s['a']['b']; assert s['a.b.c'] == s['a']['b']['c']
    """
    name = name or store.__qualname__ + "WithPathGet"

    # TODO: This is not the best way to handle this. Investigate another way. ######################
    global_names = set(globals()).union(locals())
    if name in global_names:
        raise NameError("That name is already in use")
    # TODO: ########################################################################################

    store_cls = kv_wrap_persister_cls(store, name=name)
    store_cls._path_type = path_type

    def __getitem__(self, k):
        if isinstance(k, self._path_type):
            return reduce(lambda store, key: store[key], k, self)
        else:
            return super(store_cls, self).__getitem__(k)

    store_cls.__getitem__ = __getitem__

    return store_cls


def _insert_alias(store, method_name, alias=None):
    if isinstance(alias, str) and hasattr(store, method_name):
        setattr(store, alias, getattr(store, method_name))


@store_decorator
def insert_aliases(
        store=None, *, write=None, read=None, delete=None, list=None, count=None
):
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
        store = type(store.__qualname__, (store,), {})
    for alias, method_name in _method_name_for.items():
        _insert_alias(store, method_name, alias=locals().get(alias))
    return store


@store_decorator
def insert_load_dump_aliases(store=None, *, delete=None, list=None, count=None):
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
    store = insert_aliases(
        store, read="load", delete=delete, list=list, count=count
    )

    def dump(self, obj, key):
        return self.__setitem__(key, obj)

    if isinstance(store, type):
        store.dump = dump
    else:
        store.dump = types.MethodType(dump, store)

    return store


from typing import TypeVar, Any, Callable

FuncInput = TypeVar('FuncInput')
FuncOutput = TypeVar('FuncOutput')


def constant_output(return_val=None, *args, **kwargs):
    """Function that returns a constant value no matter what the inputs are.
    Is meant to be used with functools.partial to create custom versions.

    >>> from functools import partial
    >>> always_true = partial(constant_output, True)
    >>> always_true('regardless', 'of', the='input', will='return True')
    True

    """
    return return_val


@double_up_as_factory
def condition_function_call(func: Callable[[FuncInput], FuncOutput] = None,
                            *,
                            condition: Callable[[FuncInput], bool] = partial(constant_output, True),
                            callback_if_condition_not_met: Callable[[FuncInput], Any] = partial(constant_output, None)
                            ):
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        if condition(*args, **kwargs):
            return func(*args, **kwargs)
        else:
            return callback_if_condition_not_met(*args, **kwargs)

    return wrapped_func


from typing import Callable, MutableMapping, Any

Key = Any
Val = Any
SetitemCondition = Callable[[MutableMapping, Key, Val], bool]

# @store_decorator
# def only_allow_writes_that_obey_condition(*,
#                                           write_condition: SetitemCondition,
#                                           msg='Write arguments did not match condition.'):
#     def _only_allow_writes_that_obey_condition(store: MutableMapping):
#         pass


from py2store.util import has_enabled_clear_method, inject_method, _delete_keys_one_by_one


@double_up_as_factory
def ensure_clear_method(store=None, *, clear_method=_delete_keys_one_by_one):
    """If obj doesn't have an enabled clear method, will add one (a slow one that runs through keys and deletes them"""
    if not has_enabled_clear_method(store):
        inject_method(store, clear_method, 'clear')
    return store


########## To be deprecated ############################################################################################

# TODO: Factor out the method injection pattern (e.g. __getitem__, __setitem__ and __delitem__ are nearly identical)

def filtered_iter(
        filt: Union[callable, Iterable], store=None, *,
        name=None, __module__=None  # TODO: might be able to be deprecated since included in store_decorator
):
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
    >>> assert s.get('bb', None) == None
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

    from warnings import warn

    warn("""filtered_iter is on it's way to be deprecated. Use filt_iter instead.
     To do so, replace:
        - imports of filtered_iter by filt_iter
        - non-keyword arguments by explicitly using arg names, for instance:
            ```filtered_iter(lambda x: True) -> filt_iter(filt=lambda x: True)```
    """)
    if store is None:
        if not callable(filt):  # if filt is not a callable...
            # ... assume it's the collection of keys you want and make a filter function to filter those "in".
            assert next(
                iter(filt)
            ), "filt should be a callable, or an iterable"
            keys_that_should_be_filtered_in = set(filt)

            def filt(k):
                return k in keys_that_should_be_filtered_in

        def wrap(store, name=name, __module__=__module__):
            if not isinstance(
                    store, type
            ):  # then consider it to be an instance
                store_instance = store
                WrapperStore = filtered_iter(filt, name=name, __module__=__module__)(Store)
                return WrapperStore(store_instance)
            else:  # it's a class we're wrapping
                collection_cls = store
                __module__ = __module__ or getattr(collection_cls, "__module__", None)

                name = name or "Filtered" + get_class_name(collection_cls)
                wrapped_cls = type(name, (collection_cls,), {})

                def __iter__(self):
                    yield from filter(
                        filt, super(wrapped_cls, self).__iter__()
                    )

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

                if hasattr(wrapped_cls, "__getitem__"):

                    def __getitem__(self, k):
                        if filt(k):
                            return super(wrapped_cls, self).__getitem__(k)
                        else:
                            raise KeyError(f"Key not in store: {k}")

                    wrapped_cls.__getitem__ = __getitem__

                if hasattr(wrapped_cls, "get"):

                    def get(self, k, default=None):
                        if filt(k):
                            return super(wrapped_cls, self).get(k, default)
                        else:
                            return default

                    wrapped_cls.get = get

                if hasattr(wrapped_cls, "__setitem__"):

                    def __setitem__(self, k, v):
                        if filt(k):
                            return super(wrapped_cls, self).__setitem__(k, v)
                        else:
                            raise KeyError(f"Key not in store: {k}")

                    wrapped_cls.__setitem__ = __setitem__

                if hasattr(wrapped_cls, "__delitem__"):

                    def __delitem__(self, k):
                        if filt(k):
                            return super(wrapped_cls, self).__delitem__(k)
                        else:
                            raise KeyError(f"Key not in store: {k}")

                    wrapped_cls.__delitem__ = __delitem__

                if __module__ is not None:
                    wrapped_cls.__module__ = __module__

                if hasattr(collection_cls, '__doc__'):
                    wrapped_cls.__doc__ = collection_cls.__doc__

                return wrapped_cls

        return wrap
    else:
        return filtered_iter(
            filt, store=None, name=name, __module__=__module__
        )(store)
