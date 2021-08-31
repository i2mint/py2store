"""
walking through kv stores
"""
from py2store import cached_keys, KvReader
from py2store.util import copy_attrs
from collections.abc import Mapping


# Pattern:
# TODO: Educational: This creates havoc in doctests. See why.
# Note: No users, so perhaps not needed.
# @cached_keys(keys_cache=set, name='SrcReader')
# class SrcReader(KvReader):
#     def __init__(self, src, src_to_keys, key_to_obj):
#         self.src = src
#         self.src_to_keys = src_to_keys
#         self.key_to_obj = key_to_obj
#         copy_attrs(
#             src, to_obj=self, attrs=('__name__', '__qualname__', '__module__')
#         )
#
#     def __iter__(self):
#         yield from self.src_to_keys(self, self.src)
#
#     def __getitem__(self, k):
#         return self.key_to_obj(self, self.src, k)
#
#     # def __repr__(self):
#     #     return f"{self.__class__.__qualname__}({self.src}, {self._key_filt})"


inf = float('infinity')


def print_call(func, name=None, really=True):
    func_name = name or getattr(func, '__name__', func)

    def _func(*args, **kwargs):
        if really:
            print(f'Calling {func_name} with {args=} and {kwargs=}')
        return func(*args, **kwargs)

    return _func


def val_is_mapping(p, k, v):
    return isinstance(v, Mapping)


def asis(p, k, v):
    return p, k, v


def tuple_keypath_and_val(p, k, v):
    if p == ():  # we're just begining (the root),
        p = (k,)  # so begin the path with the first key.
    else:
        p = (*p, k)  # extend the path (append the new key)
    return p, v


DO_NOT_YIELD = type('DoNotYield', (), {})()


# TODO: More docs and doctests. This one even merits an extensive usage and example tutorial!
def kv_walk(
    v: Mapping,
    yield_func=asis,  # (p, k, v) -> what you want the gen to yield
    walk_filt=val_is_mapping,  # (p, k, v) -> whether to explore the nested structure v further
    pkv_to_pv=tuple_keypath_and_val,
    p=(),
):
    """

    :param v:
    :param yield_func: (pp, k, vv) -> what ever you want the gen to yield
    :param walk_filt: (p, k, vv) -> (bool) whether to explore the nested structure v further
    :param pkv_to_pv:  (p, k, v) -> (pp, vv)
        where pp is a form of p + k (update of the path with the new node k)
        and vv is the value that will be used by both walk_filt and yield_func
    :param p: The path to v

    >>> d = {'a': 1, 'b': {'c': 2, 'd': 3}}
    >>> list(kv_walk(d))
    [(('a',), 'a', 1), (('b',), 'b', {'c': 2, 'd': 3}), (('b', 'c'), 'c', 2), (('b', 'd'), 'd', 3)]
    >>> list(kv_walk(d, lambda p, k, v: '.'.join(p)))
    ['a', 'b', 'b.c', 'b.d']
    >>> list(kv_walk(d, lambda p, k, v: '.'.join(p)))
    ['a', 'b', 'b.c', 'b.d']
    """
    # print(f"1: entered with: v={v}, p={p}")
    for k, vv in v.items():
        # print(f"2: item: k={k}, vv={vv}")
        pp, vv = pkv_to_pv(
            p, k, vv
        )  # update the path with k (and preprocess v if necessary)
        to_yield = yield_func(pp, k, vv)
        if to_yield is not DO_NOT_YIELD:
            yield to_yield
        if walk_filt(
            p, k, vv
        ):  # should we recurse? (based on some function of p, k, v)
            # print(f"3: recurse with: pp={pp}, vv={vv}\n")
            yield from kv_walk(vv, yield_func, walk_filt, pkv_to_pv, pp)  # recurse
        # else:
        # print(f"4: yield_func(pp={pp}, k={k}, vv={vv})\n --> {yield_func(pp, k, vv)}")

        # yield yield_func(pp, k, vv)  # yield something computed from p, k, vv


from inspect import signature


def conjunction(*funcs, name=None):
    """Make a function that is the conjunction of other functions.
    And by that we mean that
    ```
    conjunction(*args, **kwargs)
    ```
    will be equal to
    ```
    func_1(*args, **kwargs) & ... & func_n(*args, **kwargs)
    ```
    for all `args, kwargs`.
    """
    first_func, *other_funcs = funcs

    def conjunct(*args, **kwargs):
        result = first_func(*args, **kwargs)
        for func in other_funcs:
            result &= func(*args, **kwargs)
        return result

    conjunct.funcs = funcs
    conjunct.__signature__ = signature(first_func)
    conjunct.__return_annotation__ = signature(funcs[-1]).return_annotation
    if name is not None:
        conjunct.__name__ = name

    return conjunct


def until_max_path_length(max_path_length: int = 1):
    def max_path_length_walk_filt(p, k, v):
        return len(p) <= max_path_length

    return max_path_length_walk_filt
