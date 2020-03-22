##############################################################################
# Copyright (c) 2003 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
##############################################################################
"""Cached properties
See the CachedProperty class.

This module was taken from https://github.com/zopefoundation/zope.cachedescriptors.
"""

from functools import update_wrapper

ncaches = 0


class _CachedProperty(object):
    """
    Cached property implementation class.
    """

    def __init__(self, func, *names):
        global ncaches
        ncaches += 1
        self.data = (func, names,
                     "_v_cached_property_key_%s" % ncaches,
                     "_v_cached_property_value_%s" % ncaches)
        update_wrapper(self, func)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        func, names, key_name, value_name = self.data

        key = names and [getattr(inst, name) for name in names]
        value = getattr(inst, value_name, self)

        if value is not self:
            # We have a cached value
            if key == getattr(inst, key_name, self):
                # Cache is still good!
                return value

        # We need to compute and cache the value

        value = func(inst)
        setattr(inst, key_name, key)
        setattr(inst, value_name, value)

        return value


def CachedProperty(*args):
    """
    CachedProperties.
    This is usable directly as a decorator when given names, or when not. Any of these patterns
    will work:
    * ``@CachedProperty``
    * ``@CachedProperty()``
    * ``@CachedProperty('n','n2')``
    * def thing(self: ...; thing = CachedProperty(thing)
    * def thing(self: ...; thing = CachedProperty(thing, 'n')
    """

    if not args:  # @CachedProperty()
        return _CachedProperty  # A callable that produces the decorated function

    arg1 = args[0]
    names = args[1:]
    if callable(arg1):  # @CachedProperty, *or* thing = CachedProperty(thing, ...)
        return _CachedProperty(arg1, *names)

    # @CachedProperty( 'n' )
    # Ok, must be a list of string names. Which means we are used like a factory
    # so we return a callable object to produce the actual decorated function
    def factory(function):
        return _CachedProperty(function, arg1, *names)

    return factory


class Lazy(object):
    """Lazy Attributes.
    """

    def __init__(self, func, name=None):
        if name is None:
            name = func.__name__
        self.data = (func, name)
        update_wrapper(self, func)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        func, name = self.data
        value = func(inst)
        inst.__dict__[name] = value
        return value


class readproperty(object):

    def __init__(self, func):
        self.func = func
        update_wrapper(self, func)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        func = self.func
        return func(inst)


class cachedIn(object):
    """Cached property with given cache attribute."""

    def __init__(self, attribute_name):
        self.attribute_name = attribute_name

    def __call__(self, func):

        def get(instance):
            try:
                value = getattr(instance, self.attribute_name)
            except AttributeError:
                value = func(instance)
                setattr(instance, self.attribute_name, value)
            return value

        update_wrapper(get, func)

        return property(get)
