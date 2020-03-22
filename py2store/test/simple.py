import pytest
import os
import shutil
from tempfile import gettempdir
from py2store.errors import OverWritesNotAllowedError, DeletionsNotAllowed
from py2store.test.util import get_s3_test_access_info_from_env_vars


# from collections.abc import MutableMapping
# from py2store.base import AbstractObjStore
# import typing
#
# Store = typing.Union(AbstractObjStore, MutableMapping)

def _delete_keys_from_store(store, keys_to_delete):
    for k in keys_to_delete:
        if k in store:  # if key already in s, delete it
            del store[k]


def _test_ops_on_store(store):
    s = store  # just to be able to use shorthand "s"

    _delete_keys_from_store(s, ['_foo', '_hello', '_non_existing_key_'])

    # test "not in"
    assert '_non_existing_key_' not in s, \
        "I really wasn't expecting that key to be in there!"

    s['_foo'] = 'bar'  # store 'bar' in '_foo'
    assert "_foo" in s, '"_foo" in s'
    assert s['_foo'] == 'bar'

    s['_hello'] = 'world'  # store 'world' in '_hello'

    if hasattr(s, 'keys'):
        assert set(s.keys()).issuperset({'_foo', '_hello'})
    if hasattr(s, 'values'):
        assert set(s.values()).issuperset({'bar', 'world'})
    if hasattr(s, 'items'):
        assert set(s.items()).issuperset({('_foo', 'bar'), ('_hello', 'world')})
    # if hasattr(s, 'get'):
    #     assert s.get('_hello') == 'world'
    #     assert s.get('_non_existing_key_', 'some default') == 'some default'
    #     assert s.get('_non_existing_key_', None) is None
    if hasattr(s, 'setdefault'):
        assert s.setdefault('_hello', 'this_will_never_be_used') == 'world'
        assert s.setdefault('_non_existing_key_', 'this_will') == 'this_will'
        assert s['_non_existing_key_'] == 'this_will'
        del s['_non_existing_key_']

    # test "not in" when there's something
    assert '_non_existing_key_' not in s, \
        "I really wasn't expecting that key to be in there!"

    # wraped in try/except in case deleting is not allowed
    try:
        # testing deletion
        del s['_hello']  # delet _hello
        assert '_hello' not in s
        s['_hello'] = 'world'  # put it back

        if hasattr(s, 'pop'):
            v = s.pop('_hello')
            assert v == 'world'
            assert '_hello' not in s
            s['_hello'] = 'world'  # put it back
    except DeletionsNotAllowed:
        pass

    # wraped in try/except in case overwriting is not allowed
    try:
        s['_foo'] = 'a different value'
        assert s['_foo'] == 'a different value'
    except OverWritesNotAllowedError:
        pass

    _delete_keys_from_store(s, ['_foo', '_hello'])


def _test_len(store):
    s = store  # just to be able to use shorthand "s"

    _delete_keys_from_store(s, ['_foo', '_hello'])

    n = len(s)  # remember how many items there are

    s['_foo'] = 'bar'  # store 'bar' in '_foo'
    assert len(s) == n + 1, "You should have an extra item in the store"

    s['_hello'] = 'world'  # store 'world' in '_hello'
    assert len(s) == n + 2, "You should have had two extra items in the store"

    try:
        # testing deletion
        del s['_hello']  # delet _hello
        assert len(s) == n + 1
        s['_hello'] = 'world'  # put it back

        if hasattr(s, 'pop'):
            _ = s.pop('_hello')
            assert len(s) == n + 1
            s['_hello'] = 'world'  # put it back
    except DeletionsNotAllowed:
        pass

    # wraped in try/except in case overwriting is not allowed
    try:
        s['_foo'] = 'a different value'
        assert len(s) == n + 2
    except OverWritesNotAllowedError:
        pass

    _delete_keys_from_store(s, ['_foo', '_hello'])


#
# @fixture
# def empty_dict_store():
#     return {}
def _multi_test(store):
    _test_ops_on_store(store)
    _test_len(store)


def test_dict_ops():
    store = dict()
    _multi_test(store)


# def test_simple_file_ops():
#     from py2store.stores.local_store import RelativePathFormatStore
#
#     rootdir = os.path.join(gettempdir(), 'py_store_tests')
#     # empty and recreate rootdir if necessary
#     if os.path.isdir(rootdir):
#         shutil.rmtree(rootdir)
#     os.mkdir(rootdir)
#
#     store = RelativePathFormatStore(path_format=rootdir)
#     # store._obj_of_data = partial(str, encoding='utf-8')
#     _multi_test(store)

def _test_path_format_local_file_ops(cls):
    rootdir = os.path.join(gettempdir(), 'py_store_tests')
    # empty and recreate rootdir if necessary
    if os.path.isdir(rootdir):
        shutil.rmtree(rootdir)
    os.mkdir(rootdir)

    store = cls(path_format=rootdir)
    _multi_test(store)


def test_local_file_ops():
    rootdir = os.path.join(gettempdir(), 'py_store_tests')
    # empty and recreate rootdir if necessary
    if os.path.isdir(rootdir):
        shutil.rmtree(rootdir)
    os.mkdir(rootdir)

    from py2store.stores.local_store import RelativePathFormatStore as cls
    _test_path_format_local_file_ops(cls)

    from py2store.stores.local_store import RelativePathFormatStore2 as cls
    _test_path_format_local_file_ops(cls)


def test_dropbox():
    from py2store.access import FAK
    from py2store.stores.dropbox_store import DropboxTextStore
    import json
    import os

    try:
        filepath = os.path.expanduser('~/.py2store_configs/stores/json/dropbox.json')
        configs = json.load(open(filepath))
        store = DropboxTextStore('/py2store_data/test/', **configs[FAK]['k'])
        _multi_test(store)
    except FileNotFoundError:
        from warnings import warn
        warn(f"FileNotFoundError: {filepath}")

    # from py2store.kv import LocalFileStore as cls
    # _test_path_format_local_file_ops(cls)


# def test_s3_ops():
#     from functools import partial
#     encode_as_utf8 = partial(str, encoding='utf-8')
#     try:
#         print("\n----About to test s3 ops\n")
#         s3_access = get_s3_test_access_info_from_env_vars(perm='rw')
#         # from py2store.stores.s3_store import S3BucketStore, S3BucketStoreNoOverwrites
#         # from py2store.stores.delegation_stores import S3Store
#         from py2store.kv import S3Store
#         prefix = 'py_store_tests'
#         s = S3Store.from_s3_resource_kwargs(_prefix=prefix, **s3_access)
#         # s._data_of_obj = encode_as_utf8
#         s._obj_of_data = encode_as_utf8
#
#         _multi_test(s)
#         print("----Finished testing s3 ops")
#
#     except LookupError as e:
#         msg = "Not going to be able to test with test_s3_ops since I don't have a proper access to s3\n"
#         msg += str(e)
#         print(msg)


if __name__ == '__main__':
    pytest.main()
