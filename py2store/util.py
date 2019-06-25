import os
import shutil
import inspect
import itertools


class lazyprop:
    """
    A descriptor implementation of lazyprop (cached property) from David Beazley's "Python Cookbook" book.
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
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value


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


def move_files_of_folder_to_trash(folder):
    trash_dir = os.path.join(os.getenv("HOME"), '.Trash')  # works with mac (perhaps linux too?)
    assert os.path.isdir(trash_dir), f"{trash_dir} directory not found"

    for f in os.listdir(folder):
        src = os.path.join(folder, f)
        if os.path.isfile(src):
            dst = os.path.join(trash_dir, f)
            print(f"Moving to trash: {src}")
            shutil.move(src, dst)
