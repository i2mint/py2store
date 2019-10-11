from functools import partial


def re_get_attr(store, attr, default=None):
    a = getattr(store, attr, None)
    if a is not None:
        return a
    elif hasattr(store, 'store'):
        return re_get_attr(store.store, attr, default)
    else:
        return default


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


unravel_key = partial(store_trans_path, method='_id_of_key')
print_key_trans_path = partial(print_trans_path, method='_id_of_key')
inner_most_key = partial(inner_most, method='_id_of_key')

unravel_val = partial(store_trans_path, method='_data_of_obj')
print_val_trans_path = partial(print_trans_path, method='_data_of_obj')
inner_most_val = partial(inner_most, method='_data_of_obj')
