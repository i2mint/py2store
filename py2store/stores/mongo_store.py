from functools import wraps

from py2store.persisters.mongo_w_pymongo import OldMongoPersister

from py2store.base import Store
from py2store.util import lazyprop


class MongoStore(Store):
    @wraps(OldMongoPersister.__init__)
    def __init__(self, *args, **kwargs):
        persister = OldMongoPersister(*args, **kwargs)
        super().__init__(persister)


class MongoTupleKeyStore(MongoStore):
    """
    MongoStore using tuple keys.

    >>> s = MongoTupleKeyStore(db_name='py2store_tests', collection_name='tmp', key_fields=('_id', 'user'))
    >>> for k in s: del s[k]
    >>> k = (1234, 'user')
    >>> v = {'name': 'bob', 'age': 42}
    >>> if k in s:  # deleting all docs in tmp
    ...     del s[k]
    >>> assert (k in s) == False  # see that key is not in store (and testing __contains__)
    >>> orig_length = len(s)
    >>> s[k] = v
    >>> assert len(s) == orig_length + 1
    >>> assert k in list(s)
    >>> assert s[k] == v
    >>> assert s.get(k) == v
    >>> assert v in list(s.values())
    >>> assert (k in s) == True # testing __contains__ again
    >>> del s[k]
    >>> assert len(s) == orig_length
    """

    @lazyprop
    def _key_fields(self):
        return self.store._key_fields

    def _id_of_key(self, k):
        return {field: field_val for field, field_val in zip(self._key_fields, k)}

    def _key_of_id(self, _id):
        return tuple(_id[x] for x in self._key_fields)


# TODO: Finish
class MongoAnyKeyStore(MongoStore):
    """
    MongoStore using tuple keys.

    >>> s = MongoAnyKeyStore(db_name='py2store_tests', collection_name='tmp', )
    >>> for k in s: del s[k]
    >>> s['foo'] = {'must': 'be', 'a': 'dict'}
    >>> s['foo']
    {'must': 'be', 'a': 'dict'}
    """

    @wraps(MongoStore.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self._key_fields, tuple), "key_fields should be a tuple or a string"
        assert len(self._key_fields) == 1, "key_fields must have one and only one element (a string)"
        self._key_field = self._key_fields[0]

    @lazyprop
    def _key_fields(self):
        return self.store._key_fields

    def _id_of_key(self, k):
        return {self._key_field: k}

    def _key_of_id(self, _id):
        return _id[self._key_field]

    def __setitem__(self, k, v):
        if k in self:
            del self[k]
        super().__setitem__(k, v)


def test_mongo_store(s=MongoStore(), k=None, v=None):
    if k is None:
        k = {'_id': 'foo'}
    if v is None:
        v = {'val': 'bar'}
    if k in s:  # deleting all docs in tmp
        del s[k]
    assert (k in s) == False  # see that key is not in store (and testing __contains__)
    orig_length = len(s)
    s[k] = v
    assert len(s) == orig_length + 1
    assert k in list(s)
    assert s[k] == v
    assert s.get(k) == v
    assert v in list(s.values())
    assert (k in s) == True  # testing __contains__ again
    del s[k]
    assert len(s) == 0
