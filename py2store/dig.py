from functools import partial

# TODO: Make a generator and a index getter for keys and vals (and both).
#  Point is to be able to get views from any level.

not_found = type('NotFound', (), {})()
no_default = type('NoDefault', (), {})()


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
    elif hasattr(store, 'store'):
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
        if hasattr(store, 'store'):
            yield from unravel_key(store.store, trans_arg)


def print_trans_path(store, arg, method, with_type=False):
    gen = (arg, *store_trans_path(store, arg, method))
    if with_type:
        gen = map(lambda x: f"{type(x)}: {x}", gen)
    else:
        gen = map(str, gen)
    print('\n'.join(gen))


def last_element(gen):
    x = None
    for x in gen:
        pass
    return x


def inner_most(store, arg, method):
    return last_element(store_trans_path(store, arg, method))


# TODO: Better change the signature to reflect context (k (key) or v (val) instead of arg)
unravel_key = partial(store_trans_path, method='_id_of_key')
print_key_trans_path = partial(print_trans_path, method='_id_of_key')
inner_most_key = partial(inner_most, method='_id_of_key')

# TODO: inner_most_val doesn't really do what one expects. It just does what inner_most_key does
unravel_val = partial(store_trans_path, method='_data_of_obj')
print_val_trans_path = partial(print_trans_path, method='_data_of_obj')
inner_most_val = partial(inner_most, method='_data_of_obj')
