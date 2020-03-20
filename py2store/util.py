import os
import shutil
import re
from collections import namedtuple, defaultdict
from warnings import warn
from typing import Any, Hashable, Callable, Iterable

var_str_p = re.compile('\W|^(?=\d)')

Item = Any


def groupby(items: Iterable[Item], key: Callable[[Item], Hashable]):
    """Groups items according to group keys updated from those items through the given (item_to_)key function.

    Args:
        items: iterable of items
        key: The function that computes a key from an item. Needs to return

    Returns: A dict of {group_key: items_in_that_group, ...}

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
    groups = defaultdict(list)
    for k in items:
        groups[key(k)].append(k)
    return dict(groups)


def regroupby(items, *key_funcs, **named_key_funcs):
    """REcursive groupby. Applies the groupby function recursively, using a sequence of key functions.

    Note: The named_key_funcs argument names don't have any external effect.
        They just give a name to the key function, for code reading clarity purposes.

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
        return {group_key: regroupby(group_items, *key_funcs) for group_key, group_items in groups.items()}


def ntup(**kwargs):
    return namedtuple('NamedTuple', list(kwargs))(**kwargs)


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
    return var_str_p.sub('_', s)


# TODO: Make it work with a store, without having to load and store the values explicitly.
class DictAttr:
    """Convenience class to hold Key-Val pairs with both a dict-like and struct-like interface.
    The dict-like interface has just the basic get/set/del/iter/len
    (all "dunders": none visible as methods). There is no get, update, etc.
    This is on purpose, so that the only visible attributes (those you get by tab-completion for instance)
    are the those you injected.

    >>> da = DictAttr(foo='bar', life=42)
    >>> da.foo
    'bar'
    >>> da['life']
    42
    >>> da.true = 'love'
    >>> len(da)  # count the number of fields
    3
    >>> da['friends'] = 'forever'  # write as dict
    >>> da.friends  # read as attribute
    'forever'
    >>> list(da)  # list fields (i.e. keys i.e. attributes)
    ['foo', 'life', 'true', 'friends']
    >>> del da['friends']  # delete as dict
    >>> del da.foo # delete as attribute
    >>> list(da)
    ['life', 'true']
    >>> da._dict  # the hidden dict that is wrapped
    {'life': 42, 'true': 'love'}
    """
    _dict = None

    def __init__(self, **kwargs):
        super().__setattr__('_dict', {})
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, k):
        return self._dict[k]

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def __delitem__(self, k):
        delattr(self, k)

    def __iter__(self):
        return iter(self._dict.keys())

    def __len__(self):
        return len(self._dict)

    def __setattr__(self, k, v):
        self._dict[k] = v
        super().__setattr__(k, v)

    def __delattr__(self, k):
        del self._dict[k]
        super().__delattr__(k)


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


class lazyprop:
    """
    A descriptor implementation of lazyprop (cached property).
    Made based on David Beazley's "Python Cookbook" book and enhanced with boltons.cacheutils ideas.
    It's
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
        self.__doc__ = getattr(func, '__doc__')
        self.__isabstractmethod__ = getattr(func, '__isabstractmethod__', False)
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = instance.__dict__[self.func.__name__] = self.func(instance)
            return value

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s func=%s>' % (cn, self.func)


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
    sentinel_prefix = 'sentinel_of__'

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = instance.__dict__[self.func.__name__] = self.func(instance)
            setattr(instance, self.sentinel_prefix + self.func.__name__, True)  # my hack
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
                raise AttributeError(f"The attribute {attr} already exists. Delete it if you want to reuse it!")
        for attr, val in attr_val_dict.items():
            setattr(self, attr, val)


def max_common_prefix(a):
    """
    Given a list of strings (or other sliceable sequences), returns the longest common prefix
    :param a: list-like of strings
    :return: the smallest common prefix of all strings in a
    """
    if not a:
        return ''
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


def delegate_as(delegate_cls, to='delegate', include=frozenset(), exclude=frozenset()):
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


class imdict(dict):
    """ A frozen hashable dict """

    def __hash__(self):
        return id(self)

    def _immutable(self, *args, **kws):
        raise TypeError('object is immutable')

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable


def move_files_of_folder_to_trash(folder):
    trash_dir = os.path.join(os.getenv("HOME"), '.Trash')  # works with mac (perhaps linux too?)
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
                raise ModuleNotFoundError(f"""
It seems you don't have required `{exc_val.name}` package for this Store.
Try installing it by running:

    pip install {exc_val.name}
    
in your terminal.
For more information: https://pypi.org/project/{exc_val.name}
            """)


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
