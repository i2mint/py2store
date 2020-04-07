# from py2store.util import lazyprop, num_of_args
from py2store.base import KvReader


class FuncReader(KvReader):
    """Reader that seeds itself from a data fetching function list
    Uses the function list names as the keys, and their returned value as the values.

    For example: You have a list of urls that contain the data you want to have access to.
    You can write functions that bare the names you want to give to each dataset, and have the function
    fetch the data from the url, extract the data from the response and possibly prepare it
    (we advise minimally, since you can always transform from the raw source, but the opposite can be impossible).

    >>> def foo():
    ...     return 'bar'
    >>> def pi():
    ...     return 3.14159
    >>> s = FuncReader([foo, pi])
    >>> list(s)
    ['foo', 'pi']
    >>> s['foo']
    'bar'
    >>> s['pi']
    3.14159
    """

    def __init__(self, funcs):
        # TODO: assert no free arguments (arguments are allowed but must all have defaults)
        self.funcs = funcs
        self._func_of_name = {func.__name__: func for func in funcs}

    def __contains__(self, k):
        return k in self._func_of_name

    def __iter__(self):
        yield from self._func_of_name

    def __len__(self):
        return len(self._func_of_name)

    def __getitem__(self, k):
        return self._func_of_name[k]()  # call the func
