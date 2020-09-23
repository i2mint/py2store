"""
Tools to add append-functionality to key-val stores. The main function is
    `appendable_store_cls = add_append_functionality_to_store_cls(store_cls, item2kv, ...)`
You give it the `store_cls` you want to sub class, and a item -> (key, val) function, and you get a store (subclass) that
has a `store.append(item)` method. Also includes an extend method (that just called appends in a loop.

See add_append_functionality_to_store_cls docs for examples.
"""

import time
import types

from py2store.trans import store_decorator


def define_extend_as_seq_of_appends(obj):
    """Inject an extend method in obj that will used append method.

    Args:
        obj: Class (type) or instance of an object that has an "append" method.

    Returns: The obj, but with that extend method.

    >>> class A:
    ...     def __init__(self):
    ...         self.t = list()
    ...     def append(self, item):
    ...         self.t.append(item)
    ...
    >>> AA = define_extend_as_seq_of_appends(A)
    >>> a = AA()
    >>> a.extend([1,2,3])
    >>> a.t
    [1, 2, 3]
    >>> a.extend([10, 20])
    >>> a.t
    [1, 2, 3, 10, 20]
    >>> a = A()
    >>> a = define_extend_as_seq_of_appends(a)
    >>> a.extend([1,2,3])
    >>> a.t
    [1, 2, 3]
    >>> a.extend([10, 20])
    >>> a.t
    [1, 2, 3, 10, 20]

    """
    assert hasattr(
        obj, "append"
    ), f"Your object needs to have an append method! Object was: {obj}"

    def extend(self, items):
        for item in items:
            self.append(item)

    if isinstance(obj, type):
        obj = type(obj.__name__, (obj,), {})
        obj.extend = extend
    else:
        obj.extend = types.MethodType(extend, obj)
    return obj


########################################################################################################################

class NotSpecified:
    pass


class mk_item2kv_for:
    """A bunch of functions to make item2kv functions

    A few examples (see individual methods' docs for more examples)

    >>> # item_to_key
    >>> item2kv = mk_item2kv_for.item_to_key(item2key=lambda item: item['L'] )
    >>> item2kv({'L': 'let', 'I': 'it', 'G': 'go'})
    ('let', {'L': 'let', 'I': 'it', 'G': 'go'})
    >>>
    >>> # utc_key
    >>> import time
    >>> item2key = mk_item2kv_for.utc_key()
    >>> k, v = item2key('some data')
    >>> assert abs(time.time() - k) < 0.01  # which asserts that k is indeed a (current) utc timestamp
    >>> assert v == 'some data'  # just the item itself
    >>>
    >>> # item_to_key_params_and_val
    >>> item_to_kv = mk_item2kv_for.item_to_key_params_and_val(lambda x: ((x['L'], x['I']), x['G']), '{}/{}')
    >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
    ('let/it', 'go')
    >>>
    >>> # fields
    >>> item_to_kv = mk_item2kv_for.fields(['L', 'I'])
    >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
    ({'L': 'let', 'I': 'it'}, {'G': 'go'})
    >>> item_to_kv = mk_item2kv_for.fields(('G', 'L'), keep_field_in_value=True)
    >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})  # note the order of the key is not ('G', 'L')...
    ({'L': 'let', 'G': 'go'}, {'L': 'let', 'I': 'it', 'G': 'go'})
    >>> item_to_kv = mk_item2kv_for.fields(('G', 'L'), key_as_tuple=True)  # but ('G', 'L') order is respected here
    >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
    (('go', 'let'), {'I': 'it'})
    """

    @staticmethod
    def item_to_key(item2key):
        """Make item2kv from a item2key function (the value will be the item itself).

        Args:
            item2key: an item -> key function

        Returns: an item -> (key, val) function

        >>> item2key = lambda item: item['G']  # use value of 'L' as the key
        >>> item2key({'L': 'let', 'I': 'it', 'G': 'go'})
        'go'
        >>> item2kv = mk_item2kv_for.item_to_key(item2key)
        >>> item2kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ('go', {'L': 'let', 'I': 'it', 'G': 'go'})
        """

        def item2kv(item):
            return item2key(item), item

        return item2kv

    @staticmethod
    def field(field, keep_field_in_value=True, dflt_if_missing=NotSpecified):
        """item2kv that uses a specific key of a (mapping) item as the key

        Note: If keep_field_in_value=False, the field will be popped OUT of the item.
         If that's not the desired effect, one should feed copies of the items (e.g. map(dict.copy, items))

        :param field: The field (value) to use as the returned key
        :param keep_field_in_value: Whether to leave the field in the item. If False, will pop it out
        :param dflt_if_missing: If specified (even None) will use the specified key as the key, if the field is missig
        :return: A item2kv function

        >>> item2kv = mk_item2kv_for.field('G')
        >>> item2kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ('go', {'L': 'let', 'I': 'it', 'G': 'go'})
        >>> item2kv = mk_item2kv_for.field('G', keep_field_in_value=False)
        >>> item2kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ('go', {'L': 'let', 'I': 'it'})
        >>> item2kv = mk_item2kv_for.field('G', dflt_if_missing=None)
        >>> item2kv({'L': 'let', 'I': 'it', 'DIE': 'go'})
        (None, {'L': 'let', 'I': 'it', 'DIE': 'go'})

        """
        if dflt_if_missing is NotSpecified:
            if keep_field_in_value:
                def item2kv(item):
                    return item[field], item
            else:
                def item2kv(item):
                    return item.pop(field), item
        else:
            if keep_field_in_value:
                def item2kv(item):
                    return item.get(field, dflt_if_missing), item
            else:
                def item2kv(item):
                    return item.pop(field, dflt_if_missing), item

        return item2kv

    @staticmethod
    def utc_key(offset_s=0.0):
        """Make an item2kv function that uses the current time as the key, and the unchanged item as a value.
        The offset_s, which is added to the output key, can be used, for example, to align to another system's clock,
        or to get a more accurate timestamp of an event.

        Use case for offset_s:
            * Align to another system's clock
            * Get more accurate timestamping of an event. For example, in situations where the item is a chunk of live
            streaming data and we want the key (timestamp) to represent the timestamp of the beginning of the chunk.
            Without an offset_s, the timestamp would be the timestamp after the last byte of the chunk was produced,
            plus the time it took to reach the present function. If we know the data production rate (e.g. sample rate)
            and the average lag to get to the present function, we can get a more accurate timestamp for the beginning
            of the chunk

        Args:
            offset_s: An offset (in seconds, possibly negative) to add to the current time.

        Returns: an item -> (current_utc_s, item) function

        >>> import time
        >>> item2key = mk_item2kv_for.utc_key()
        >>> k, v = item2key('some data')
        >>> assert abs(time.time() - k) < 0.01  # which asserts that k is indeed a (current) utc timestamp
        >>> assert v == 'some data'  # just the item itself

        """
        if (
                offset_s == 0.0
        ):  # splitting for extra speed (important in real time apps)

            def item2kv(item):
                return time.time(), item

        else:

            def item2kv(item):
                return time.time() + offset_s, item

        return item2kv

    @staticmethod
    def item_to_key_params_and_val(item_to_key_params_and_val, key_str_format):
        """Make item2kv from a function that produces key_params and val,
        and a key_template that will produce a string key from the key_params

        Args:
            item_to_key_params_and_val: an item -> (key_params, val) function
            key_str_format: A string format such that
                    key_str_format.format(*key_params) or
                    key_str_format.format(**key_params)
                will produce the desired key string

        Returns: an item -> (key, val) function

        >>> # Using tuple key params with unnamed string format fields
        >>> item_to_kv = mk_item2kv_for.item_to_key_params_and_val(lambda x: ((x['L'], x['I']), x['G']), '{}/{}')
        >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ('let/it', 'go')
        >>>
        >>> # Using dict key params with named string format fields
        >>> item_to_kv = mk_item2kv_for.item_to_key_params_and_val(
        ...                             lambda x: ({'second': x['L'], 'first': x['G']}, x['I']), '{first}_{second}')
        >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ('go_let', 'it')
        """

        def item2kv(item):
            key_params, val = item_to_key_params_and_val(item)
            if isinstance(key_params, dict):
                return key_str_format.format(**key_params), val
            else:
                return key_str_format.format(*key_params), val

        return item2kv

    @staticmethod
    def fields(fields, keep_field_in_value=False, key_as_tuple=False):
        """Make item2kv from specific fields of a Mapping (i.e. dict-like object) item.

        Note: item2kv will not mutate item (even if keep_field_in_value=False).

        Args:
            fields: The sequence (list, tuple, etc.) of item fields that should be used to create the key.
            keep_field_in_value: Set to True to return the item as is, as the value
            key_as_tuple: Set to True if you want keys to be tuples (note that the fields order is important here!)

        Returns: an item -> (item[fields], item[not in fields]) function

        >>> item_to_kv = mk_item2kv_for.fields('L')
        >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ({'L': 'let'}, {'I': 'it', 'G': 'go'})
        >>> item_to_kv = mk_item2kv_for.fields(['L', 'I'])
        >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ({'L': 'let', 'I': 'it'}, {'G': 'go'})
        >>> item_to_kv = mk_item2kv_for.fields(('G', 'L'), keep_field_in_value=True)
        >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})  # note the order of the key is not ('G', 'L')...
        ({'L': 'let', 'G': 'go'}, {'L': 'let', 'I': 'it', 'G': 'go'})
        >>> item_to_kv = mk_item2kv_for.fields(('G', 'L'), key_as_tuple=True)  # but ('G', 'L') order is respected here
        >>> item_to_kv({'L': 'let', 'I': 'it', 'G': 'go'})
        (('go', 'let'), {'I': 'it'})

        """
        if isinstance(fields, str):
            fields_set = {fields}
            fields = (fields,)
        else:
            fields_set = set(fields)

        def item2kv(item):
            if keep_field_in_value:
                key = dict()
                for k, v in item.items():
                    if k in fields_set:
                        key[k] = v
                val = item
            else:
                key = dict()
                val = dict()
                for k, v in item.items():
                    if k in fields_set:
                        key[k] = v
                    elif not keep_field_in_value:
                        val[k] = v

            if key_as_tuple:
                return tuple(key[f] for f in fields), val
            else:
                return key, val

        return item2kv


@store_decorator
def appendable(
        store_cls=None, *, item2kv,
):
    """Makes a new class with append (and consequential extend) methods

    Args:
        store_cls: The store class to subclass
        item2kv: The function that produces a (key, val) pair from an item
        new_store_name: The name to give the new class (default will be 'Appendable' + store_cls.__name__)

    Returns: A subclass of store_cls with two additional methods: append, and extend.


    >>> item_to_kv = lambda item: (item['L'], item)  # use value of 'L' as the key, and value is the item itself
    >>> MyStore = appendable(dict, item2kv=item_to_kv)
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [('let', {'L': 'let', 'I': 'it', 'G': 'go'})]

    Use mk_item2kv.from_item_to_key_params_and_val with tuple key params

    >>> item_to_kv = appendable.mk_item2kv_for.item_to_key_params_and_val(lambda x: ((x['L'], x['I']), x['G']), '{}/{}')
    >>> MyStore = appendable(item2kv=item_to_kv)(dict)  # showing the append(...)(store) form
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [('let/it', 'go')]

    Use mk_item2kv.from_item_to_key_params_and_val with dict key params

    >>> item_to_kv = appendable.mk_item2kv_for.item_to_key_params_and_val(
    ...     lambda x: ({'L': x['L'], 'G': x['G']}, x['I']), '{G}_{L}')
    >>> @appendable(item2kv=item_to_kv)  # showing the @ form
    ... class MyStore(dict):
    ...     pass
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [('go_let', 'it')]

    Use mk_item2kv.fields to get a tuple key from item fields,
    defining the sub-dict of the remaining fields to be the value.
    Also showing here how you can decorate the instance itself.

    >>> item_to_kv = appendable.mk_item2kv_for.fields(['G', 'L'], key_as_tuple=True)
    >>> d = {}
    >>> s = appendable(d, item2kv=item_to_kv)
    >>> s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [(('go', 'let'), {'I': 'it'})]
    """

    def append(self, item):
        k, v = item2kv(item)
        self[k] = v

    def extend(self, items):
        for item in items:
            self.append(item)

    return type(
        "Appendable" + store_cls.__name__,
        (store_cls,),
        {"append": append, "extend": extend}
    )


add_append_functionality_to_store_cls = appendable  # for back compatibility

appendable.mk_item2kv_for = mk_item2kv_for  # adding as attribute for convenient access

from collections.abc import Sequence
from typing import Iterable, Optional

NotAVal = type(
    "NotAVal", (), {}
)()  # singleton instance to distinguish from None


#
# class FixedSizeStack(Sequence):
#     """A finite Sequence that can have no more than one element.
#
#     >>> t = FixedSizeStack(maxsize=1)
#     >>> assert len(t) == 0
#     >>>
#     >>> t.append('something')
#     >>> assert len(t) == 1
#     >>> assert t[0] == 'something'
#     >>>
#     >>> t.append('something else')
#     >>> assert len(t) == 1  # still only one item
#     >>> assert t[0] == 'something'  # still the same item
#
#     Not that we'd ever these methods of FirstAppendOnly,
#     but know that FirstAppendOnly is a collection.abc.Sequence, so...
#
#     >>> t[:1] == t[:10] == t[::-1] == t[::-10] == t[0:2:10] == list(reversed(t)) == ['something']
#     True
#     >>>
#     >>> assert t.count('something') == 1
#     >>> assert t.index('something') == 0
#
#     """
#
#     def __init__(self, iterable: Optional[Iterable] = None, *, maxsize: int):
#         self.maxsize = maxsize
#         self.data = [NotAVal] * maxsize
#         # self.data = (isinstance(iterable, Iterable) and list(iterable)) or []
#         # if iterable is not None:
#         #     pass
#         self.cursor = 0
#
#     def append(self, v):
#         if self.cursor < self.maxsize:
#             self.data[self.cursor] = v
#             self.cursor += 1
#
#     def __len__(self):
#         return self.cursor
#
#     def __getitem__(self, k):
#         if isinstance(k, int):
#             if k < self.cursor:
#                 return self.data[k]
#             else:
#                 raise IndexError(
#                     f"There are only {len(self)} items: You asked for self[{k}]."
#                 )
#         elif isinstance(k, slice):
#             return self.data[: self.cursor][k]
#         else:
#             raise IndexError(
#                 f"A {self.__class__} instance can only have one value, or none at all."
#             )
#

class FirstAppendOnly(Sequence):
    """A finite Sequence that can have no more than one element.

    >>> t = FirstAppendOnly()
    >>> assert len(t) == 0
    >>>
    >>> t.append('something')
    >>> assert len(t) == 1
    >>> assert t[0] == 'something'
    >>>
    >>> t.append('something else')
    >>> assert len(t) == 1  # still only one item
    >>> assert t[0] == 'something'  # still the same item
    >>>
    >>> # Not that we'd ever these methods of FirstAppendOnly, but know that FirstAppendOnly is a collection.abc.Sequence, so...
    >>> t[:1] == t[:10] == t[::-1] == t[::-10] == t[0:2:10] == list(reversed(t)) == ['something']
    <stdin>:1: RuntimeWarning: coroutine 'AioFileBytesPersister.asetitem' was never awaited
    RuntimeWarning: Enable tracemalloc to get the object allocation traceback
    True
    >>>
    >>> t.count('something') == 1
    True
    >>> t.index('something') == 0
    True
    """

    def __init__(self):
        self.val = NotAVal

    def append(self, v):
        if self.val == NotAVal:
            self.val = v

    def __len__(self):
        return int(self.val != NotAVal)

    def __getitem__(self, k):
        if len(self) == 0:
            raise IndexError(
                f"There are no items in this {self.__class__} instance"
            )
        elif k == 0:
            return self.val
        elif isinstance(k, slice):
            return [self.val][k]
        else:
            raise IndexError(
                f"A {self.__class__} instance can only have one value, or none at all."
            )

    # @staticmethod
    # def from

# def add_append_functionality_to_str_key_store(store_cls,
#                                               item_to_key_params_and_val,
#                                               key_template=None,
#                                               new_store_name=None):
#     def item_to_kv(item):
#         nonlocal key_template
#         if key_template is None:
#             key_params, _ = item_to_key_params_and_val(item)
#             key_template = path_sep.join('{{{}}}'.format(p) for p in key_params)
#         key_params, val = item_to_key_params_and_val(item)
#         return key_template.format(**key_params), val
#
#     return add_append_functionality_to_store_cls(store_cls, item_to_kv, new_store_name)
