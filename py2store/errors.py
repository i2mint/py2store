from collections.abc import Mapping
from inspect import signature


# TODO: More on wrapped_callback: Handle *args too. Make it work with builtins (no signature!)
# TODO: What about traceback?
# TODO: Make it a more general and useful store decorator. Trans store into an getitem exception catching store.
def items_with_caught_exceptions(d: Mapping, callback=None,
                                 catch_exceptions=(Exception,), yield_callback_output=False):
    """
    Do what Mapping.items() does, but catching exceptions when getting the values for a key.


    Some time your `store.items()` is annoying because of some exceptions that happen
    when you're retrieving some value for some of the keys.

    Yes, if that happens, it's that something is wrong with your store, and yes,
    if it's a store that's going to be used a lot, you really should build the right store
    that doesn't have that problem.

    But now that we appeased the paranoid naysayers with that warning, let's get to business:
    Sometimes you just want to get through the hurdle to get the job done. Sometimes your store is good enough,
    except for a few exceptions. Sometimes your store gets it's keys from a large pool of possible keys
    (e.g. github stores or kaggle stores, or any store created by a free-form search seed),
    so you can't really depend on the fact that all the keys given by your key iterator
    will give you a value without exception
    -- especially if you slapped on a bunch of post-processing on the out-coming values.

    So you can right a for loop to iterate over your keys, catch the exceptions, do something with it...

    Or, in many cases, you can just use `items_with_caught_exceptions`.

    :param d: Any Mapping
    :param catch_exceptions: A tuple of exceptions that should be caught
    :param callback: A function that will be called every time an exception is caught.
        The signature of the callback function is required to be:
            k (key), e (error obj), d (mapping), i (index)
        but
    :return: An (key, val) generator with exceptions caught

    >>> from collections.abc import Mapping
    >>> class Test(Mapping):  # a Mapping class that has keys 0..9, but raises of KeyError if the key is not even
    ...     n = 10
    ...     def __iter__(self):
    ...         yield from range(2, self.n)
    ...     def __len__(self):
    ...         return self.n
    ...     def __getitem__(self, k):
    ...         if k % 2 == 0:
    ...             return k
    ...         else:
    ...             raise KeyError('Not even')
    >>>
    >>> list(items_with_caught_exceptions(Test()))
    [(2, 2), (4, 4), (6, 6), (8, 8)]
    >>>
    >>> def my_log(k, e):
    ...     print(k, e)
    >>> list(items_with_caught_exceptions(Test(), callback=my_log))
    3 'Not even'
    5 'Not even'
    7 'Not even'
    9 'Not even'
    [(2, 2), (4, 4), (6, 6), (8, 8)]
    >>> def my_other_log(i):
    ...     print(i)
    >>> list(items_with_caught_exceptions(Test(), callback=my_other_log))
    1
    3
    5
    7
    [(2, 2), (4, 4), (6, 6), (8, 8)]
    """

    # wrap the input callback to make the callback definition less constrained for the user.
    if callback is not None:
        try:
            params = signature(callback).parameters

            def wrapped_callback(**kwargs):
                kwargs = {k: v for k, v in kwargs.items() if k in params}
                return callback(**kwargs)
        except ValueError:
            def wrapped_callback(k, e, d, i):
                return callback(k, e, d, i)

    else:
        def wrapped_callback(k, e, d, i):
            pass  # do nothing

    for i, k in enumerate(d):  # iterate over keys of the mapping
        try:
            v = d[k]  # try getting the value...
            yield k, v  # and if you do, yield the (k, v) pair
        except catch_exceptions as e:  # catch the specific exceptions you requested to catch
            t = wrapped_callback(k=k, e=e, d=d, i=i)  # call it
            if yield_callback_output:  # if the user wants the output of the callback
                yield t  # yield it


def _assert_condition(condition, err_msg='', err_cls=AssertionError):
    if not condition:
        raise err_cls(err_msg)


class KeyValidationError(ValueError):
    """Error to raise when a key is not valid"""
    pass


class NoSuchKeyError(KeyError):
    pass


class OperationNotAllowed(NotImplementedError):
    pass


class ReadsNotAllowed(OperationNotAllowed):
    pass


class WritesNotAllowed(OperationNotAllowed):
    pass


class DeletionsNotAllowed(OperationNotAllowed):
    pass


class IterationNotAllowed(OperationNotAllowed):
    pass


class OverWritesNotAllowedError(OperationNotAllowed):
    """Error to raise when a key is not valid"""
    pass
