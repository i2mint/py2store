from abc import ABCMeta, abstractmethod
from typing import Union
from collections.abc import Collection, Mapping, MutableMapping, Container
from py2store.errors import KeyValidationError, OverWritesNotAllowedError


class Loader(object):

    def __init__(self, data_of_key, obj_of_data=None):
        self.data_of_key = data_of_key
        if obj_of_data is not None or not callable(obj_of_data):
            raise TypeError('serializer must be None or a callable')
        self.obj_of_data = obj_of_data

    def __call__(self, k):
        if self.obj_of_data is not None:
            return self.obj_of_data(self.data_of_key(k))
        else:
            return self.data_of_key(k)


class Dumper(object):
    def __init__(self, save_data_to_key, data_of_obj=None):
        self.save_data_to_key = save_data_to_key
        if data_of_obj is not None or not callable(data_of_obj):
            raise TypeError('serializer must be None or a callable')
        self.data_of_obj = data_of_obj

    def __call__(self, k, v):
        if self.data_of_obj is not None:
            return self.save_data_to_key(k, self.data_of_obj(v))
        else:
            return self.save_data_to_key(k, v)


from functools import wraps
from collections import defaultdict


def transform_args(**trans_func_for_arg):
    """
    Make a decorator that transforms function arguments before calling the function.
    For example:
        * original argument: a relative path --> used argument: a full path
        * original argument: a pickle filepath --> used argument: the loaded object
    :param rootdir: rootdir to be used for all name arguments of target function
    :param name_arg: the position (int) or argument name of the argument containing the name
    :return: a decorator
    >>> def f(a, b, c):
    ...     return "a={a}, b={b}, c={c}".format(a=a, b=b, c=c)
    >>>
    >>> print(f('foo', 'bar', 3))
    a=foo, b=bar, c=3
    >>> ff = transform_args()(f)
    >>> print(ff('foo', 'bar', 3))
    a=foo, b=bar, c=3
    >>> ff = transform_args(a=lambda x: 'ROOT/' + x)(f)
    >>> print(ff('foo', 'bar', 3))
    a=ROOT/foo, b=bar, c=3
    >>> ff = transform_args(b=lambda x: 'ROOT/' + x)(f)
    >>> print(ff('foo', 'bar', 3))
    a=foo, b=ROOT/bar, c=3
    >>> ff = transform_args(a=lambda x: 'ROOT/' + x, b=lambda x: 'ROOT/' + x)(f)
    >>> print(ff('foo', b='bar', c=3))
    a=ROOT/foo, b=ROOT/bar, c=3
    """

    def transform_args_decorator(func):
        if len(trans_func_for_arg) == 0:  # if no transformations were specified...
            return func  # just return the function itself
        else:
            @wraps(func)
            def transform_args_wrapper(*args, **kwargs):
                # get a {argname: argval, ...} dict from *args and **kwargs
                # Note: Didn't really need an if/else here but...
                # Note: ... assuming getcallargs gives us an overhead that can be avoided if there's only keyword args.
                if len(args) > 0:
                    val_of_argname = inspect.getcallargs(func, *args, **kwargs)
                else:
                    val_of_argname = kwargs
                # apply transform functions to argument values
                for argname, trans_func in trans_func_for_arg.items():
                    val_of_argname[argname] = trans_func(val_of_argname[argname])
                # call the function with transformed values
                return func(**val_of_argname)

            return transform_args_wrapper

    return transform_args_decorator


def wrap_method_output(wrapper_func):
    def _wrap_output(wrapped):
        @wraps(wrapped)
        def _wrapped(self, *args, **kwargs):
            return wrapper_func(wrapped(self, *args, **kwargs))

        return _wrapped

    return _wrap_output


def wrap_iter_method_output(wrapper_func):
    def _wrap_iter_output(wrapped):
        @wraps(wrapped)
        def _wrapped(self, *args, **kwargs):
            return map(wrapper_func, wrapped(self, *args, **kwargs))

        return _wrapped

    return _wrap_iter_output


def transform_class_method(cls, method, method_output_trans=None, method_iter_output_trans=None, **arg_trans):
    assert method_output_trans is None or method_iter_output_trans is None, \
        "You cannot specify both method_output_trans and method_iter_output_trans!"
    wrapped_method = transform_args(**arg_trans)(getattr(cls, method))
    if method_output_trans is not None:
        setattr(cls, method, wrap_method_output(method_output_trans)(wrapped_method))
    elif method_iter_output_trans is not None:
        setattr(cls, method, wrap_iter_method_output(method_iter_output_trans)(wrapped_method))
    else:
        setattr(cls, method, wrapped_method)


def wrap_class_methods(**method_trans_spec):
    def class_wrapper(cls):
        for method, method_trans in method_trans_spec.items():
            if hasattr(cls, method):
                transform_class_method(cls, method, **method_trans)
        return cls

    return class_wrapper


def mk_method_trans_spec_from_methods_specs_dict(methods_specs_dict):
    method_trans_spec = defaultdict(dict)
    for methods, specs in methods_specs_dict.items():
        if isinstance(methods, str):
            methods = (methods,)
        for method in methods:
            method_trans_spec[method].update(specs)
    return dict(method_trans_spec)


import re

val_in_trans = lambda x: 'hello {}'.format(x)
val_out_trans = lambda x: re.sub('hello', 'hi', x)
key_in_trans = lambda x: '__' + x
key_out_trans = lambda x: x[2:]

from collections import UserDict

methods_specs_dict = {
    ('__contains__', '__getitem__', '__setitem__', '__delitem__'): dict(key=key_in_trans),
    '__setitem__': dict(item=val_in_trans),
    '__iter__': dict(method_iter_output_trans=key_out_trans),
    '__getitem__': dict(method_output_trans=val_out_trans)
}

methods_specs_dict = mk_method_trans_spec_from_methods_specs_dict(methods_specs_dict)


@wrap_class_methods(**methods_specs_dict)
class AA(UserDict):
    pass


aa = AA()
aa['foo'] = 'shoo'
# the __str__ method isn't wrapped, so we see the actual STORED keys and values
assert str(aa) == "{'__foo': 'hello shoo'}"  # we see that __foo, not foo is the actual key, and "hello shoo" the value
assert 'foo' in aa  # yet from the interface, it looks like 'foo' is a key of aa...
assert '__foo' not in aa  # ... and '__foo' is not a key.
aa['foo'] = 'bar'  # let's replace the value of 'foo'
assert str(aa) == "{'__foo': 'hello bar'}"  # see what's stored
aa['star'] = 'wars'  # let's add another
assert list(aa) == ['foo', 'star']  # what are the keys?
assert list(aa.keys()) == ['foo', 'star']  # another way to do that
# see here that when we ask for values, we don't get what we asked to store,
# nor what is actually stored, but something else
assert list(aa.values()) == ['hi bar', 'hi wars']
assert str(list(aa.items())) == "[('foo', 'hi bar'), ('star', 'hi wars')]"  # the keys and values we get from items()
assert str(aa) == "{'__foo': 'hello bar', '__star': 'hello wars'}"  # what is actually stored
del aa['foo']  # testing deletion of a key
assert str(aa) == "{'__star': 'hello wars'}"  # it worked!

# def _check_methods(C, *methods):
#     """
#     Check that all methods listed are in the __dict__ of C, or in the classes of it's mro.
#     One trick pony borrowed from collections.abc.
#     """
#     mro = C.__mro__
#     for method in methods:
#         for B in mro:
#             if method in B.__dict__:
#                 if B.__dict__[method] is None:
#                     return NotImplemented
#                 break
#         else:
#             return NotImplemented
#     return True


# class Serializer(metaclass=ABCMeta):
#     """
#     An ABC for an object serializer.
#     Single purpose: returning data is meant to be persisted
#     How the object serialized into data to be persisted should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, obj):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Serializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
#
#
# class Deserializer(metaclass=ABCMeta):
#     """
#     An ABC for an object deserializer.
#     Single purpose: returning the object keyed by a requested key k.
#     How the data is deserialized into an object should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, data: bytes):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Deserializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
#
#
# class Persister(metaclass=ABCMeta):
#     """
#     An ABC for an object serializer.
#     Single purpose: returning data is meant to be persisted
#     How the object serialized into data to be persisted should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, obj):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Serializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
#
#
# class Loader(metaclass=ABCMeta):
#     """
#     An ABC for an object deserializer.
#     Single purpose: returning the object keyed by a requested key k.
#     How the data is deserialized into an object should be defined in a concrete subclass.
#     """
#     __slots__ = ()
#
#     @abstractmethod
#     def __call__(self, data: bytes):
#         pass
#
#     @classmethod
#     def __subclasshook__(cls, C):
#         if cls is Deserializer:
#             return _check_methods(C, "__call__")
#         return NotImplemented
