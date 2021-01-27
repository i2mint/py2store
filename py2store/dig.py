from functools import partial

# TODO: Make a generator and a index getter for keys and vals (and both).
#  Point is to be able to get views from any level.

not_found = type("NotFound", (), {})()
no_default = type("NoDefault", (), {})()


def get_first_attr_found(store, attrs, default=no_default):
    for attr in attrs:
        a = getattr(store, attr, not_found)
        if a != not_found:
            return a
    if default == no_default:
        raise AttributeError(f"None of the attributes were found: {attrs}")
    else:
        return default


def recursive_get_attr(store, attr, default=None):
    a = getattr(store, attr, None)
    if a is not None:
        return a
    elif hasattr(store, "store"):
        return recursive_get_attr(store.store, attr, default)
    else:
        return default


re_get_attr = recursive_get_attr
dig_up = recursive_get_attr


def store_trans_path(store, arg, method):
    f = getattr(store, method, None)
    if f is not None:
        trans_arg = f(arg)
        yield trans_arg
        if hasattr(store, "store"):
            yield from unravel_key(store.store, trans_arg)


def print_trans_path(store, arg, method, with_type=False):
    gen = (arg, *store_trans_path(store, arg, method))
    if with_type:
        gen = map(lambda x: f"{type(x)}: {x}", gen)
    else:
        gen = map(str, gen)
    print("\n".join(gen))


def last_element(gen):
    x = None
    for x in gen:
        pass
    return x


def inner_most(store, arg, method):
    return last_element(store_trans_path(store, arg, method))


# TODO: Better change the signature to reflect context (k (key) or v (val) instead of arg)
unravel_key = partial(store_trans_path, method="_id_of_key")
print_key_trans_path = partial(print_trans_path, method="_id_of_key")
inner_most_key = partial(inner_most, method="_id_of_key")

# TODO: inner_most_val doesn't really do what one expects. It just does what inner_most_key does
unravel_val = partial(store_trans_path, method="_data_of_obj")
print_val_trans_path = partial(print_trans_path, method="_data_of_obj")
inner_most_val = partial(inner_most, method="_data_of_obj")

from functools import partial


def next_layer(store, layer_attrs=('store',)):
    for attr in layer_attrs:
        attr_val = getattr(store, attr, not_found)
        if attr_val is not not_found:
            return attr_val
    return not_found


def recursive_calls(func, x, sentinel=not_found):
    while True:
        if x is sentinel:
            break
        else:
            yield x
            x = func(x)


def layers(store, layer_attrs=('store',)):
    _next_layer = partial(next_layer, layer_attrs=layer_attrs)
    return list(recursive_calls(_next_layer, store))


def trace_getitem(store, k, layer_attrs=('store',)):
    """A generator of layered steps to inspect a store.
    
    :param store: An instance that has the base.Store interface
    :param k: A key
    :param layer_attrs: The attribute names that should be checked to get the next layer.
    :return: A generator of (layer, method, value)

    We start with a small dict:
        
    >>> d = {'a.num': '1000', 'b.num': '2000'}

    Now let's add layers to it. For example, with wrap_kvs:
    >>> from py2store.trans import wrap_kvs
    
    Say that we want the interface to not see the ``'.num'`` strings, and deal with numerical values, not strings.
    
    >>> s = wrap_kvs(d,
    ...              key_of_id=lambda x: x[:-len('.num')],
    ...              id_of_key=lambda x: x + '.num',
    ...              obj_of_data=lambda x: int(x),
    ...              data_of_obj=lambda x: str(x)
    ...             )
    >>>
    
    Oh, and we want the interface to display upper case keys.
    
    >>> ss = wrap_kvs(s,
    ...              key_of_id=lambda x: x.upper(),
    ...              id_of_key=lambda x: x.lower(),
    ...             )
    
    And we want the numerical unit to be the kilo (that's 1000):
    
    >>> sss = wrap_kvs(ss,
    ...                obj_of_data=lambda x: x / 1000,
    ...                data_of_obj=lambda x: x * 1000
    ...               )
    >>>
    >>> dict(sss.items())
    {'A': 1.0, 'B': 2.0}
    
    Well, if we had bugs, we'd like to inspect the various layers, and how they transform the data.
    
    Here's how to do that:
    
    >>> for layer, method, value in trace_getitem(sss, 'A'):
    ...     print(layer, method, value)
    ...
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    NameError: name 'trace_getitem' is not defined
    >>> from py2store.dig import trace_getitem
    >>>
    >>> for layer, method, value in trace_getitem(sss, 'A'):
    ...     print(layer, method, value)
    ...
    {'a.num': '1000', 'b.num': '2000'} _id_of_key A
    {'a.num': '1000', 'b.num': '2000'} _id_of_key A
    {'a.num': '1000', 'b.num': '2000'} _id_of_key a
    {'a.num': '1000', 'b.num': '2000'} _id_of_key a
    {'a.num': '1000', 'b.num': '2000'} _id_of_key a.num
    {'a.num': '1000', 'b.num': '2000'} _id_of_key a.num
    {'a.num': '1000', 'b.num': '2000'} __getitem__ 1000
    {'a.num': '1000', 'b.num': '2000'} _obj_of_data 1000
    {'a.num': '1000', 'b.num': '2000'} _obj_of_data 1000
    {'a.num': '1000', 'b.num': '2000'} _obj_of_data 1000
    {'a.num': '1000', 'b.num': '2000'} _obj_of_data 1000
    {'a.num': '1000', 'b.num': '2000'} _obj_of_data 1000
    {'a.num': '1000', 'b.num': '2000'} _obj_of_data 1.0
    """
    _layers = layers(store, layer_attrs)

    layer = None
    for i, layer in enumerate(_layers):
        if hasattr(layer, '_id_of_key'):
            k = layer._id_of_key(k)
            yield (layer, '_id_of_key', k)

    if layer is not None:
        v = layer[k]
        yield (layer, '__getitem__', v)

        for layer in _layers[:i][::-1]:
            if hasattr(layer, '_obj_of_data'):
                v = layer._obj_of_data(v)
                yield (layer, '_obj_of_data', v)


def trace_info(trace, item_func=print):
    for item in trace:
        item_func(item)


def _trace_item_info(item):
    layer, method, value = item
    return f"{layer.__class__.__name__}.{method}: {type(value).__name__}"


def print_trace_info(trace, item_info=_trace_item_info):
    for item in trace:
        print(item_info(item))
