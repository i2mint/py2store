"""
a data object layer for object attributes
"""
from collections import abc
from keyword import iskeyword
from warnings import warn


class AttrMap:
    """A read-only façade for navigating a JSON-like object using attribute notation.
    Based on Luciano Ramalho's "Fluent Python" book.

    >>> t = AttrMap({'a': {'b': 2, 'foo': 'bar'}, 'b': [1,2,3]})
    >>> t
    AttrMap({'a': {'b': 2, 'foo': 'bar'}, 'b': [1, 2, 3]})
    >>> t.a
    AttrMap({'b': 2, 'foo': 'bar'})
    >>> t.a.foo
    'bar'
    >>> t.b
    [1, 2, 3]
    """

    def __new__(cls, arg):  # <1>
        if isinstance(arg, abc.Mapping):
            return super().__new__(cls)  # <2>
        elif isinstance(arg, abc.MutableSequence):  # <3>
            return [cls(item) for item in arg]
        else:
            return arg

    def __init__(self, mapping):
        self.__data = {}
        identifiers = []
        for key, value in mapping.items():
            if not isinstance(key, str) or not str.isidentifier(key):
                identifiers.append(key)
            elif iskeyword(key):
                key += '_'
            self.__data[key] = value
        if identifiers:
            warn(
                f'{len(identifiers)} keys were not identifiers. Namely:\n{identifiers}'
            )

    def __getattr__(self, name):
        if hasattr(self.__data, name):
            return getattr(self.__data, name)
        else:
            return AttrMap(self.__data[name])  # <4>

    def __iter__(self):
        yield from self.__data

    def __dir__(self):
        s = set(dir(type(self)))
        s.update(self.__dict__)
        s.update(self)
        return s

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__data})'


def special_dir(self):
    s = set(dir(type(self)))
    s.update(self.__dict__)
    s.update(
        filter(
            lambda k: isinstance(k, str) and str.isidentifier(k) and not iskeyword(k),
            self,
        )
    )
    return s


def attr_wrap(cls, name=None):
    """Returns a Mapping class that routes attribute access to keys of mapping.

    >>> A = attr_wrap(dict)
    >>> t = A({'a_special_attr': 'foo', 'another_attr': 2, # valid identifiers
    ...        42: [1, 2], '$invalid': 'identifier', 'class': 'is a reserved keyword'})  # not valid identifiers
    >>> # verify that we have the attr we want
    >>> assert 'a_special_attr' in dir(t)
    >>> assert 'another_attr' in dir(t)
    >>> # verify that we DO NOT have the attr we DO NOT want
    >>> assert 42 not in dir(t)
    >>> assert '$invalid' not in dir(t)
    >>> assert 'class' not in dir(t)
    """
    return type(
        name or f'Attr{cls.__name__}',
        (cls,),
        {'__getattr__': cls.__getitem__, '__dir__': special_dir},
    )
