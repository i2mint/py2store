import os
import shutil
import re
from collections import namedtuple, defaultdict
from warnings import warn
from typing import Any, Hashable, Callable, Iterable, Optional, Union
from functools import update_wrapper as _update_wrapper
from functools import wraps as _wraps
from functools import partialmethod, partial, WRAPPER_ASSIGNMENTS
from types import MethodType

# monkey patching WRAPPER_ASSIGNMENTS to get "proper" wrapping (adding defaults and kwdefaults
wrapper_assignments = (*WRAPPER_ASSIGNMENTS, '__defaults__', '__kwdefaults__')

update_wrapper = partial(_update_wrapper, assigned=wrapper_assignments)
wraps = partial(_wraps, assigned=wrapper_assignments)


def inject_method(obj, method_function, method_name=None):
    """
    method_function could be:
        * a function
        * a {method_name: function, ...} dict (for multiple injections)
        * a list of functions or (function, method_name) pairs
    """
    if method_name is None:
        method_name = method_function.__name__
    assert callable(method_function), f"method_function (the second argument) is supposed to be a callable!"
    assert isinstance(method_name, str), f"method_name (the third argument) is supposed to be a string!"
    if not isinstance(obj, type):
        method_function = MethodType(method_function, obj)
    setattr(obj, method_name, method_function)
    return obj


def _disabled_clear_method(self):
    """The clear method is disabled to make dangerous difficult.
    You don't want to delete your whole DB
    If you really want to delete all your data, you can do so by doing something like this:
        ```
        for k in self:
            del self[k]
        ```

    or (in some cases)

        ```
        for k in self:
            try:
                del self[k]
            except KeyError:
                pass
        ```
    """
    raise NotImplementedError(f"Instance of {type(self)}: {self.clear.__doc__}")


# to be able to check if clear is disabled (see ensure_clear_method function for example):
_disabled_clear_method.disabled = True


def has_enabled_clear_method(store):
    """Returns True iff obj has a clear method that is enabled (i.e. not disabled)"""
    return hasattr(store, 'clear') and not getattr(store.clear, 'disabled', False)


def _delete_keys_one_by_one(self):
    """clear the entire store (delete all keys)"""
    for k in self:
        del self[k]


def _delete_keys_one_by_one_with_keyerror_supressed(self):
    """clear the entire store (delete all keys), ignoring KeyErrors"""
    for k in self:
        try:
            del self[k]
        except KeyError:
            pass


_delete_keys_one_by_one.disabled = False
_delete_keys_one_by_one_with_keyerror_supressed.disabled = False


def partialclass(cls, *args, **kwargs):
    """What partial(cls, *args, **kwargs) does, but returning a class instead of an object.

    :param cls: Class to get the partial of
    :param kwargs: The kwargs to fix

    The raison d'être of partialclass is that it returns a type, so let's have a look at that with
    a useless class.

    >>> class A:
    ...     pass
    >>> assert isinstance(A, type) == isinstance(partialclass(A), type) == True

    >>> class A:
    ...     def __init__(self, a=0, b=1):
    ...         self.a, self.b = a, b
    ...     def mysum(self):
    ...         return self.a + self.b
    ...     def __repr__(self):
    ...         return f"{self.__class__.__name__}(a={self.a}, b={self.b})"
    >>>
    >>> assert isinstance(A, type) == isinstance(partialclass(A), type) == True
    >>>
    >>> assert str(signature(A)) == '(a=0, b=1)'
    >>>
    >>> a = A()
    >>> assert a.mysum() == 1
    >>> assert str(a) == 'A(a=0, b=1)'
    >>>
    >>> assert A(a=10).mysum() == 11
    >>> assert str(A()) == 'A(a=0, b=1)'
    >>>
    >>>
    >>> AA = partialclass(A, b=2)
    >>> assert str(signature(AA)) == '(a=0, *, b=2)'
    >>> aa = AA()
    >>> assert aa.mysum() == 2
    >>> assert str(aa) == 'A(a=0, b=2)'
    >>> assert AA(a=1, b=3).mysum() == 4
    >>> assert str(AA(3)) == 'A(a=3, b=2)'
    >>>
    >>> AA = partialclass(A, a=7)
    >>> assert str(signature(AA)) == '(*, a=7, b=1)'
    >>> assert AA().mysum() == 8
    >>> assert str(AA(a=3)) == 'A(a=3, b=1)'

    Note in the last partial that since ``a`` was fixed, you need to specify the keyword ``AA(a=3)``.
    ``AA(3)`` won't work:

    >>> AA(3)
    Traceback (most recent call last):
      ...
    TypeError: __init__() got multiple values for argument 'a'

    On the other hand, you can use *args to specify the fixtures:

    >>> AA = partialclass(A, 22)
    >>> assert str(AA()) == 'A(a=22, b=1)'
    >>> assert str(signature(AA)) == '(b=1)'
    >>> assert str(AA(3)) == 'A(a=22, b=3)'

    ```
    """
    assert isinstance(cls, type), f"cls should be a type, was a {type(cls)}: {cls}"

    class PartialClass(cls):
        __init__ = partialmethod(cls.__init__, *args, **kwargs)

    copy_attrs(PartialClass, cls, attrs=('__name__', '__qualname__', '__module__', '__doc__'))

    return PartialClass


def copy_attrs(target, source, attrs, raise_error_if_an_attr_is_missing=True):
    """Copy attributes from one object to another.

    >>> class A:
    ...     x = 0
    >>> class B:
    ...     x = 1
    ...     yy = 2
    ...     zzz = 3
    >>> dict_of = lambda o: {a: getattr(o, a) for a in dir(A) if not a.startswith('_')}
    >>> dict_of(A)
    {'x': 0}
    >>> copy_attrs(A, B, 'yy')
    >>> dict_of(A)
    {'x': 0, 'yy': 2}
    >>> copy_attrs(A, B, ['x', 'zzz'])
    >>> dict_of(A)
    {'x': 1, 'yy': 2, 'zzz': 3}

    But if you try to copy something that `B` (the source) doesn't have, copy_attrs will complain:
    >>> copy_attrs(A, B, 'this_is_not_an_attr')
    Traceback (most recent call last):
        ...
    AttributeError: type object 'B' has no attribute 'this_is_not_an_attr'

    If you tell it not to complain, it'll just ignore attributes that are not in source.
    >>> copy_attrs(A, B, ['nothing', 'here', 'exists'], raise_error_if_an_attr_is_missing=False)
    >>> dict_of(A)
    {'x': 1, 'yy': 2, 'zzz': 3}
    """
    if isinstance(attrs, str):
        attrs = (attrs,)
    if raise_error_if_an_attr_is_missing:
        filt = lambda a: True
    else:
        filt = lambda a: hasattr(source, a)
    for a in filter(filt, attrs):
        setattr(target, a, getattr(source, a))


def copy_attrs_from(from_obj, to_obj, attrs):
    from warnings import warn

    warn(f"Deprecated. Use copy_attrs instead.", DeprecationWarning)
    copy_attrs(to_obj, from_obj, attrs)
    return to_obj


def norm_kv_filt(kv_filt: Callable[[Any], bool]):
    """Prepare a boolean function to be used with `filter` when fed an iterable of (k, v) pairs.

    So you have a mapping. Say a dict `d`. Now you want to go through d.items(),
    filtering based on the keys, or the values, or both.

    It's not hard to do, really. If you're using a dict you might use a dict comprehension,
    or in the general case you might do a `filter(lambda kv: my_filt(kv[0], kv[1]), d.items())`
    if you have a `my_filt` that works wiith k and v, etc.

    But thought simple, it can become a bit muddled.
    `norm_kv_filt` simplifies this by allowing you to bring your own filtering boolean function,
    whether it's a key-based, value-based, or key-value-based one, and it will make a
    ready-to-use with `filter` function for you.

    Only thing: Your function needs to call a key `k` and a value `v`.
    But hey, it's alright, if you have a function that calls things differently, just do
    something like
    ```
        new_filt_func = lambda k, v: your_filt_func(..., key=k, ..., value=v, ...)
    ```
    and all will be fine.

    :param kv_filt: callable (starting with signature (k), (v), or (k, v)), and returning  a boolean
    :return: A normalized callable.

    >>> d = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    >>> list(filter(norm_kv_filt(lambda k: k in {'b', 'd'}), d.items()))
    [('b', 2), ('d', 4)]
    >>> list(filter(norm_kv_filt(lambda v: v > 2), d.items()))
    [('c', 3), ('d', 4)]
    >>> list(filter(norm_kv_filt(lambda k, v: (v > 1) & (k != 'c')), d.items()))
    [('b', 2), ('d', 4)]
    """
    if kv_filt is None:
        return None  # because `filter` works with a callable, or None, so we align

    raise_msg = (
        f"kv_filt should be callable (starting with signature (k), (v), or (k, v)),"
        "and returning  a boolean. What you gave me was {fv_filt}"
    )
    assert callable(kv_filt), raise_msg

    params = list(signature(kv_filt).parameters.values())
    assert len(params), raise_msg
    _kv_filt = kv_filt
    if params[0].name == "v":

        def kv_filt(k, v):
            return _kv_filt(v)

    elif params[0].name == "k":
        if len(params) > 1:
            if params[1].name != "v":
                raise ValueError(raise_msg)
        else:

            def kv_filt(k, v):
                return _kv_filt(k)

    else:
        raise ValueError(raise_msg)

    def __kv_filt(kv_item):
        return kv_filt(*kv_item)

    __kv_filt.__name__ = kv_filt.__name__

    return __kv_filt


var_str_p = re.compile("\W|^(?=\d)")

Item = Any


def add_attrs(remember_added_attrs=True, if_attr_exists="raise", **attrs):
    """Make a function that will add attributes to an obj.
    Originally meant to be used as a decorator of a function, to inject
    >>> from py2store.util import add_attrs
    >>> @add_attrs(bar='bituate', hello='world')
    ... def foo():
    ...     pass
    >>> [x for x in dir(foo) if not x.startswith('_')]
    ['bar', 'hello']
    >>> foo.bar
    'bituate'
    >>> foo.hello
    'world'
    >>> foo._added_attrs  # Another attr was added to hold the list of attributes added (in case we need to remove them
    ['bar', 'hello']
    """

    def add_attrs_to_func(obj):
        attrs_added = []
        for attr_name, attr_val in attrs.items():
            if hasattr(obj, attr_name):
                if if_attr_exists == "raise":
                    raise AttributeError(
                        f"Attribute {attr_name} already exists in {obj}"
                    )
                elif if_attr_exists == "warn":
                    warn(f"Attribute {attr_name} already exists in {obj}")
                elif if_attr_exists == "skip":
                    continue
                else:
                    raise ValueError(
                        f"Unknown value for if_attr_exists: {if_attr_exists}"
                    )
            setattr(obj, attr_name, attr_val)
            attrs_added.append(attr_name)

        if remember_added_attrs:
            obj._added_attrs = attrs_added

        return obj

    return add_attrs_to_func


def fullpath(path):
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return os.path.abspath(path)


def attrs_of(obj):
    return set(dir(obj))


def format_invocation(name="", args=(), kwargs=None):
    """Given a name, positional arguments, and keyword arguments, format
    a basic Python-style function call.

    >>> print(format_invocation('func', args=(1, 2), kwargs={'c': 3}))
    func(1, 2, c=3)
    >>> print(format_invocation('a_func', args=(1,)))
    a_func(1)
    >>> print(format_invocation('kw_func', kwargs=[('a', 1), ('b', 2)]))
    kw_func(a=1, b=2)

    """
    kwargs = kwargs or {}
    a_text = ", ".join([repr(a) for a in args])
    if isinstance(kwargs, dict):
        kwarg_items = [(k, kwargs[k]) for k in sorted(kwargs)]
    else:
        kwarg_items = kwargs
    kw_text = ", ".join(["%s=%r" % (k, v) for k, v in kwarg_items])

    all_args_text = a_text
    if all_args_text and kw_text:
        all_args_text += ", "
    all_args_text += kw_text

    return "%s(%s)" % (name, all_args_text)


def groupby(
        items: Iterable[Item],
        key: Callable[[Item], Hashable],
        val: Optional[Callable[[Item], Any]] = None,
        group_factory=list,
) -> dict:
    """Groups items according to group keys updated from those items through the given (item_to_)key function.

    Args:
        items: iterable of items
        key: The function that computes a key from an item. Needs to return a hashable.
        val: An optional function that computes a val from an item. If not given, the item itself will be taken.
        group_factory: The function to make new (empty) group objects and accumulate group items.
            group_items = group_factory() will be called to make a new empty group collection
            group_items.append(x) will be called to add x to that collection
            The default is `list`

    Returns: A dict of {group_key: items_in_that_group, ...}

    See Also: regroupby, itertools.groupby, and py2store.source.SequenceKvReader

    >>> groupby(range(11), key=lambda x: x % 3)
    {0: [0, 3, 6, 9], 1: [1, 4, 7, 10], 2: [2, 5, 8]}
    >>>
    >>> tokens = ['the', 'fox', 'is', 'in', 'a', 'box']
    >>> groupby(tokens, len)
    {3: ['the', 'fox', 'box'], 2: ['is', 'in'], 1: ['a']}
    >>> key_map = {1: 'one', 2: 'two'}
    >>> groupby(tokens, lambda x: key_map.get(len(x), 'more'))
    {'more': ['the', 'fox', 'box'], 'two': ['is', 'in'], 'one': ['a']}
    >>> stopwords = {'the', 'in', 'a', 'on'}
    >>> groupby(tokens, lambda w: w in stopwords)
    {True: ['the', 'in', 'a'], False: ['fox', 'is', 'box']}
    >>> groupby(tokens, lambda w: ['words', 'stopwords'][int(w in stopwords)])
    {'stopwords': ['the', 'in', 'a'], 'words': ['fox', 'is', 'box']}
    """
    groups = defaultdict(group_factory)
    if val is None:
        for item in items:
            groups[key(item)].append(item)
    else:
        for item in items:
            groups[key(item)].append(val(item))
    return dict(groups)


def regroupby(items, *key_funcs, **named_key_funcs):
    """REcursive groupby. Applies the groupby function recursively, using a sequence of key functions.

    Note: The named_key_funcs argument names don't have any external effect.
        They just give a name to the key function, for code reading clarity purposes.

    See Also: groupby, itertools.groupby, and py2store.source.SequenceKvReader

    >>> # group by how big the number is, then by it's mod 3 value
    >>> # note that named_key_funcs argument names doesn't have any external effect (but give a name to the function)
    >>> regroupby([1, 2, 3, 4, 5, 6, 7], lambda x: 'big' if x > 5 else 'small', mod3=lambda x: x % 3)
    {'small': {1: [1, 4], 2: [2, 5], 0: [3]}, 'big': {0: [6], 1: [7]}}
    >>>
    >>> tokens = ['the', 'fox', 'is', 'in', 'a', 'box']
    >>> stopwords = {'the', 'in', 'a', 'on'}
    >>> word_category = lambda x: 'stopwords' if x in stopwords else 'words'
    >>> regroupby(tokens, word_category, len)
    {'stopwords': {3: ['the'], 2: ['in'], 1: ['a']}, 'words': {3: ['fox', 'box'], 2: ['is']}}
    >>> regroupby(tokens, len, word_category)
    {3: {'stopwords': ['the'], 'words': ['fox', 'box']}, 2: {'words': ['is'], 'stopwords': ['in']}, 1: {'stopwords': ['a']}}
    """
    key_funcs = list(key_funcs) + list(named_key_funcs.values())
    assert len(key_funcs) > 0, "You need to have at least one key_func"
    if len(key_funcs) == 1:
        return groupby(items, key=key_funcs[0])
    else:
        key_func, *key_funcs = key_funcs
        groups = groupby(items, key=key_func)
        return {
            group_key: regroupby(group_items, *key_funcs)
            for group_key, group_items in groups.items()
        }


Groups = dict
GroupKey = Hashable
GroupItems = Iterable[Item]
GroupReleaseCond = Union[
    Callable[[GroupKey, GroupItems], bool],
    Callable[[Groups, GroupKey, GroupItems], bool]
]

from inspect import signature


def igroupby(
        items: Iterable[Item],
        key: Callable[[Item], GroupKey],
        val: Optional[Callable[[Item], Any]] = None,
        group_factory: Callable[[], GroupItems] = list,
        group_release_cond: GroupReleaseCond = lambda k, v: False,
        release_remainding=True,
        append_to_group_items: Callable[[GroupItems, Item], Any] = list.append,
        grouper_mapping=defaultdict
) -> dict:
    """The generator version of py2store groupby.
    Groups items according to group keys updated from those items through the given (item_to_)key function,
    yielding the groups according to a logic defined by ``group_release_cond``

    Args:
        items: iterable of items
        key: The function that computes a key from an item. Needs to return a hashable.
        val: An optional function that computes a val from an item. If not given, the item itself will be taken.
        group_factory: The function to make new (empty) group objects and accumulate group items.
            group_items = group_collector() will be called to make a new empty group collection
            group_items.append(x) will be called to add x to that collection
            The default is `list`
        group_release_cond: A boolean function that will be applied, at every iteration,
            to the accumulated items of the group that was just updated,
            and determines (if True) if the (group_key, group_items) should be yielded.
            The default is False, which results in
            ``lambda group_key, group_items: False`` being used.
        release_remainding: Once the input items have been consumed, there may still be some
            items in the grouping "cache". ``release_remainding`` is a boolean that indicates whether
            the contents of this cache should be released or not.

    Yields: ``(group_key, items_in_that_group)`` pairs


    The following will group numbers according to their parity (0 for even, 1 for odd),
    releasing a list of numbers collected when that list reaches length 3:

    >>> g = igroupby(items=range(11),
    ...             key=lambda x: x % 2,
    ...             group_release_cond=lambda k, v: len(v) == 3)
    >>> list(g)
    [(0, [0, 2, 4]), (1, [1, 3, 5]), (0, [6, 8, 10]), (1, [7, 9])]

    If we specify ``release_remainding=False`` though, we won't get
    >>> g = igroupby(items=range(11),
    ...             key=lambda x: x % 2,
    ...             group_release_cond=lambda k, v: len(v) == 3,
    ...             release_remainding=False)
    >>> list(g)
    [(0, [0, 2, 4]), (1, [1, 3, 5]), (0, [6, 8, 10])]

    # >>> grps = partial(igroupby, group_release_cond=False, release_remainding=True)


    Below we show that, with the default ``group_release_cond = lambda k, v: False``
    and release_remainding=True`` we have ``dict(igroupby(...)) == groupby(...)``

    >>> from functools import partial
    >>> from py2store import groupby
    >>>
    >>> kws = dict(items=range(11), key=lambda x: x % 3)
    >>> assert (dict(igroupby(**kws)) == groupby(**kws)
    ...         == {0: [0, 3, 6, 9], 1: [1, 4, 7, 10], 2: [2, 5, 8]})
    >>>
    >>> tokens = ['the', 'fox', 'is', 'in', 'a', 'box']
    >>> kws = dict(items=tokens, key=len)
    >>> assert (dict(igroupby(**kws)) == groupby(**kws)
    ...         == {3: ['the', 'fox', 'box'], 2: ['is', 'in'], 1: ['a']})
    >>>
    >>> key_map = {1: 'one', 2: 'two'}
    >>> kws.update(key=lambda x: key_map.get(len(x), 'more'))
    >>> assert (dict(igroupby(**kws)) == groupby(**kws)
    ...         == {'more': ['the', 'fox', 'box'], 'two': ['is', 'in'], 'one': ['a']})
    >>>
    >>> stopwords = {'the', 'in', 'a', 'on'}
    >>> kws.update(key=lambda w: w in stopwords)
    >>> assert (dict(igroupby(**kws)) == groupby(**kws)
    ...         == {True: ['the', 'in', 'a'], False: ['fox', 'is', 'box']})
    >>> kws.update(key=lambda w: ['words', 'stopwords'][int(w in stopwords)])
    >>> assert (dict(igroupby(**kws)) == groupby(**kws)
    ...         == {'stopwords': ['the', 'in', 'a'], 'words': ['fox', 'is', 'box']})

    """
    groups = grouper_mapping(group_factory)

    assert callable(group_release_cond), (
        "group_release_cond should be callable (filter boolean function) or False. "
        f"Was {group_release_cond}")
    n_group_release_cond_args = len(signature(group_release_cond).parameters)
    assert n_group_release_cond_args in {2, 3}, (
        "group_release_cond should take two or three inputs:\n"
        " - (group_key, group_items), or\n"
        " - (groups, group_key, group_items)"
        f"The arguments of the function you gave me are: {signature(group_release_cond)}"
    )

    if val is None:
        _append_to_group_items = append_to_group_items
    else:
        _append_to_group_items = lambda group_items, item: (group_items, val(item))

    for item in items:
        group_key = key(item)
        group_items = groups[group_key]
        _append_to_group_items(group_items, item)

        if group_release_cond(group_key, group_items):
            yield group_key, group_items
            del groups[group_key]

    if release_remainding:
        for group_key, group_items in groups.items():
            yield group_key, group_items


def ntup(**kwargs):
    return namedtuple("NamedTuple", list(kwargs))(**kwargs)


def str_to_var_str(s: str) -> str:
    """Make a valid python variable string from the input string.
    Left untouched if already valid.

    >>> str_to_var_str('this_is_a_valid_var_name')
    'this_is_a_valid_var_name'
    >>> str_to_var_str('not valid  #)*(&434')
    'not_valid_______434'
    >>> str_to_var_str('99_ballons')
    '_99_ballons'
    """
    return var_str_p.sub("_", s)


def fill_with_dflts(d, dflt_dict=None):
    """
    Fed up with multiline handling of dict arguments?
    Fed up of repeating the if d is None: d = {} lines ad nauseam (because defaults can't be dicts as a default
    because dicts are mutable blah blah, and the python kings don't seem to think a mutable dict is useful enough)?
    Well, my favorite solution would be a built-in handling of the problem of complex/smart defaults,
    that is visible in the code and in the docs. But for now, here's one of the tricks I use.

    Main use is to handle defaults of function arguments. Say you have a function `func(d=None)` and you want
    `d` to be a dict that has at least the keys `foo` and `bar` with default values 7 and 42 respectively.
    Then, in the beginning of your function code you'll say:

        d = fill_with_dflts(d, {'a': 7, 'b': 42})

    See examples to know how to use it.

    ATTENTION: A shallow copy of the dict is made. Know how that affects you (or not).
    ATTENTION: This is not recursive: It won't be filling any nested fields with defaults.

    Args:
        d: The dict you want to "fill"
        dflt_dict: What to fill it with (a {k: v, ...} dict where if k is missing in d, you'll get a new field k, with
            value v.

    Returns:
        a dict with the new key:val entries (if the key was missing in d).

    >>> fill_with_dflts(None)
    {}
    >>> fill_with_dflts(None, {'a': 7, 'b': 42})
    {'a': 7, 'b': 42}
    >>> fill_with_dflts({}, {'a': 7, 'b': 42})
    {'a': 7, 'b': 42}
    >>> fill_with_dflts({'b': 1000}, {'a': 7, 'b': 42})
    {'a': 7, 'b': 1000}
    """
    if d is None:
        d = {}
    if dflt_dict is None:
        dflt_dict = {}
    return dict(dflt_dict, **d)


# Note: Had replaced with cached_property (new in 3.8)
# if not sys.version_info >= (3, 8):
#     from functools import cached_property
# # etc...
# But then I realized that the way cached_property is implemented, pycharm does not see the properties (lint)
# So I'm reverting to lazyprop
# TODO: Keep track of the evolution of functools.cached_property and compare performance.
class lazyprop:
    """
    A descriptor implementation of lazyprop (cached property).
    Made based on David Beazley's "Python Cookbook" book and enhanced with boltons.cacheutils ideas.

    >>> class Test:
    ...     def __init__(self, a):
    ...         self.a = a
    ...     @lazyprop
    ...     def len(self):
    ...         print('generating "len"')
    ...         return len(self.a)
    >>> t = Test([0, 1, 2, 3, 4])
    >>> t.__dict__
    {'a': [0, 1, 2, 3, 4]}
    >>> t.len
    generating "len"
    5
    >>> t.__dict__
    {'a': [0, 1, 2, 3, 4], 'len': 5}
    >>> t.len
    5
    >>> # But careful when using lazyprop that no one will change the value of a without deleting the property first
    >>> t.a = [0, 1, 2]  # if we change a...
    >>> t.len  # ... we still get the old cached value of len
    5
    >>> del t.len  # if we delete the len prop
    >>> t.len  # ... then len being recomputed again
    generating "len"
    3
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, "__doc__")
        self.__isabstractmethod__ = getattr(
            func, "__isabstractmethod__", False
        )
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = instance.__dict__[self.func.__name__] = self.func(instance)
            return value

    def __repr__(self):
        cn = self.__class__.__name__
        return "<%s func=%s>" % (cn, self.func)


from functools import lru_cache, wraps
import weakref


@wraps(lru_cache)
def memoized_method(*lru_args, **lru_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapped_func(self, *args, **kwargs):
            # Storing the wrapped method inside the instance since a strong reference to self would not allow it to die.
            self_weak = weakref.ref(self)

            @wraps(func)
            @lru_cache(*lru_args, **lru_kwargs)
            def cached_method(*args, **kwargs):
                return func(self_weak(), *args, **kwargs)

            setattr(self, func.__name__, cached_method)
            return cached_method(*args, **kwargs)

        return wrapped_func

    return decorator


class lazyprop_w_sentinel(lazyprop):
    """
    A descriptor implementation of lazyprop (cached property).
    Inserts a `self.func.__name__ + '__cache_active'` attribute

    >>> class Test:
    ...     def __init__(self, a):
    ...         self.a = a
    ...     @lazyprop_w_sentinel
    ...     def len(self):
    ...         print('generating "len"')
    ...         return len(self.a)
    >>> t = Test([0, 1, 2, 3, 4])
    >>> lazyprop_w_sentinel.cache_is_active(t, 'len')
    False
    >>> t.__dict__  # let's look under the hood
    {'a': [0, 1, 2, 3, 4]}
    >>> t.len
    generating "len"
    5
    >>> lazyprop_w_sentinel.cache_is_active(t, 'len')
    True
    >>> t.len  # notice there's no 'generating "len"' print this time!
    5
    >>> t.__dict__  # let's look under the hood
    {'a': [0, 1, 2, 3, 4], 'len': 5, 'sentinel_of__len': True}
    >>> # But careful when using lazyprop that no one will change the value of a without deleting the property first
    >>> t.a = [0, 1, 2]  # if we change a...
    >>> t.len  # ... we still get the old cached value of len
    5
    >>> del t.len  # if we delete the len prop
    >>> t.len  # ... then len being recomputed again
    generating "len"
    3
    """

    sentinel_prefix = "sentinel_of__"

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = instance.__dict__[self.func.__name__] = self.func(instance)
            setattr(
                instance, self.sentinel_prefix + self.func.__name__, True
            )  # my hack
            return value

    @classmethod
    def cache_is_active(cls, instance, attr):
        return getattr(instance, cls.sentinel_prefix + attr, False)


class Struct:
    def __init__(self, **attr_val_dict):
        for attr, val in attr_val_dict.items():
            setattr(self, attr, val)


class MutableStruct(Struct):
    def extend(self, **attr_val_dict):
        for attr in attr_val_dict.keys():
            if hasattr(self, attr):
                raise AttributeError(
                    f"The attribute {attr} already exists. Delete it if you want to reuse it!"
                )
        for attr, val in attr_val_dict.items():
            setattr(self, attr, val)


def max_common_prefix(a):
    """
    Given a list of strings (or other sliceable sequences), returns the longest common prefix
    :param a: list-like of strings
    :return: the smallest common prefix of all strings in a
    """
    if not a:
        return ""
    # Note: Try to optimize by using a min_max function to give me both in one pass. The current version is still faster
    s1 = min(a)
    s2 = max(a)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


class SimpleProperty(object):
    def __get__(self, obj, objtype=None):
        return obj.d

    def __set__(self, obj, value):
        obj.d = value

    def __delete__(self, obj):
        del obj.d


class DelegatedAttribute:
    def __init__(self, delegate_name, attr_name):
        self.attr_name = attr_name
        self.delegate_name = delegate_name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            # return instance.delegate.attr
            return getattr(self.delegate(instance), self.attr_name)

    def __set__(self, instance, value):
        # instance.delegate.attr = value
        setattr(self.delegate(instance), self.attr_name, value)

    def __delete__(self, instance):
        delattr(self.delegate(instance), self.attr_name)

    def delegate(self, instance):
        return getattr(instance, self.delegate_name)

    def __str__(self):
        return ""

    # def __call__(self, instance, *args, **kwargs):
    #     return self.delegate(instance)(*args, **kwargs)


def delegate_as(
        delegate_cls, to="delegate", include=frozenset(), exclude=frozenset()
):
    raise NotImplementedError("Didn't manage to make this work fully")
    # turn include and ignore into sets, if they aren't already
    include = set(include)
    exclude = set(exclude)
    delegate_attrs = set(delegate_cls.__dict__.keys())
    attributes = include | delegate_attrs - exclude

    def inner(cls):
        # create property for storing the delegate
        setattr(cls, to, property())
        # don't bother adding attributes that the class already has
        attrs = attributes - set(cls.__dict__.keys())
        # set all the attributes
        for attr in attrs:
            setattr(cls, attr, DelegatedAttribute(to, attr))
        return cls

    return inner


class HashableMixin:
    def __hash__(self):
        return id(self)


class ImmutableMixin:
    def _immutable(self, *args, **kws):
        raise TypeError("object is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable


class imdict(dict, HashableMixin, ImmutableMixin):
    """ A frozen hashable dict """

    pass


def move_files_of_folder_to_trash(folder):
    trash_dir = os.path.join(
        os.getenv("HOME"), ".Trash"
    )  # works with mac (perhaps linux too?)
    assert os.path.isdir(trash_dir), f"{trash_dir} directory not found"

    for f in os.listdir(folder):
        src = os.path.join(folder, f)
        if os.path.isfile(src):
            dst = os.path.join(trash_dir, f)
            print(f"Moving to trash: {src}")
            shutil.move(src, dst)


class ModuleNotFoundErrorNiceMessage:
    def __init__(self, msg=None):
        self.msg = msg

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ModuleNotFoundError:
            if self.msg is not None:
                warn(self.msg)
            else:
                raise ModuleNotFoundError(
                    f"""
It seems you don't have required `{exc_val.name}` package for this Store.
Try installing it by running:

    pip install {exc_val.name}
    
in your terminal.
For more information: https://pypi.org/project/{exc_val.name}
            """
                )


class ModuleNotFoundWarning:
    def __init__(self, msg="It seems you don't have a required package."):
        self.msg = msg

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ModuleNotFoundError:
            warn(self.msg)
            #             if exc_val is not None and getattr(exc_val, 'name', None) is not None:
            #                 warn(f"""
            # It seems you don't have required `{exc_val.name}` package for this Store.
            # This is just a warning: The process goes on...
            # (But, hey, if you really need that package, try installing it by running:
            #
            #     pip install {exc_val.name}
            #
            # in your terminal.
            # For more information: https://pypi.org/project/{exc_val.name}, or google around...
            #                 """)
            #             else:
            #                 print("It seems you don't have a required package")
            return True


class ModuleNotFoundIgnore:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ModuleNotFoundError:
            pass
        return True


def num_of_args(func):
    return len(signature(func).parameters)
