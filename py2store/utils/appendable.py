"""
Tools to add append-functionality to key-val stores. The main function is
    `appendable_store_cls = add_append_functionality_to_store_cls(store_cls, item2kv, ...)`
You give it the `store_cls` you want to sub class, and a item -> (key, val) function, and you get a store (subclass) that
has a `store.append(item)` method. Also includes an extend method (that just called appends in a loop.

See add_append_functionality_to_store_cls docs for examples.
"""

import time
import types


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
    assert hasattr(obj, 'append'), f"Your object needs to have an append method! Object was: {obj}"

    def extend(self, items):
        for item in items:
            self.append(item)

    if isinstance(obj, type):
        obj = type(obj.__name__, (obj,), {})
        obj.extend = extend
    else:
        obj.extend = types.MethodType(extend, obj)
    return obj


def add_append_functionality_to_store_cls(store_cls, item2kv, new_store_name=None):
    """Makes a new class with append (and consequential extend) methods


    Args:
        store_cls: The store class to subclass
        item2kv: The function that produces a (key, val) pair from an item
        new_store_name: The name to give the new class (default will be 'Appendable' + store_cls.__name__)

    Returns: A subclass of store_cls with two additional methods: append, and extend.


    >>> item_to_kv = lambda item: (item['L'], item)  # use value of 'a' as the key, and value is the item itself
    >>> MyStore = add_append_functionality_to_store_cls(dict, item_to_kv)
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [('let', {'L': 'let', 'I': 'it', 'G': 'go'})]
    >>> # Use mk_item2kv.from_item_to_key_params_and_val with tuple key params
    ... item_to_kv = mk_item2kv_for.item_to_key_params_and_val(lambda x: ((x['L'], x['I']), x['G']), '{}/{}')
    >>> MyStore = add_append_functionality_to_store_cls(dict, item_to_kv)
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [('let/it', 'go')]
    >>> # Use mk_item2kv.from_item_to_key_params_and_val with dict key params
    ... item_to_kv = mk_item2kv_for.item_to_key_params_and_val(
    ...     lambda x: ({'L': x['L'], 'G': x['G']}, x['I']), '{G}_{L}')
    >>> MyStore = add_append_functionality_to_store_cls(dict, item_to_kv)
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [('go_let', 'it')]
    >>> # Use mk_item2kv.fields to get a tuple key from item fields, defining the sub-dict of the remaining fields to be the value
    ... item_to_kv = mk_item2kv_for.fields(['G', 'L'], key_as_tuple=True)
    >>> MyStore = add_append_functionality_to_store_cls(dict, item_to_kv)
    >>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
    [(('go', 'let'), {'I': 'it'})]
    """

    new_store_name = new_store_name or ('Appendable' + store_cls.__name__)

    def append(self, item):
        k, v = item2kv(item)
        self[k] = v

    def extend(self, items):
        for item in items:
            self.append(item)

    return type(new_store_name, (store_cls,), {'append': append, 'extend': extend})


########################################################################################################################

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

        >>> item2key = lambda item: item['L']  # use value of 'L' as the key
        >>> item2key({'L': 'let', 'I': 'it', 'G': 'go'})
        'let'
        >>> item2kv = mk_item2kv_for.item_to_key(item2key)
        >>> item2kv({'L': 'let', 'I': 'it', 'G': 'go'})
        ('let', {'L': 'let', 'I': 'it', 'G': 'go'})
        """

        def item2kv(item):
            return item2key(item), item

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
        if offset_s == 0.0:  # splitting for extra speed (important in real time apps)
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
