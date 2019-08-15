from functools import wraps

from py2store.base import Store
from py2store.persisters.couchdb_w_couchdb import CouchDbPersister
from py2store.util import lazyprop


class CouchDbStore(Store):
    def clear(self):
        super(CouchDbStore, self).clear()

    @wraps(CouchDbPersister.__init__)
    def __init__(self, *args, **kwargs):
        persister = CouchDbPersister(*args, **kwargs)
        super().__init__(persister)


class CouchDbTupleKeyStore(CouchDbStore):
    """
    CouchDbStore using tuple keys.

    >>> s = CouchDbTupleKeyStore(key_fields=('_id', 'user'))
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


def test_couchdb_store(s=CouchDbStore(), k=None, v=None):
    if k is None:
        k = {'_id': 'foo'}
    if v is None:
        v = {'val': 'bar'}
    if k in s:  # deleting all docs in tmp
        del s[k]
    assert (k in s) is False  # see that key is not in store (and testing __contains__)
    orig_length = len(s)
    s[k] = v
    assert len(s) == orig_length + 1
    assert k in list(s)
    assert s[k] == v
    assert s.get(k) == v
    assert v in list(s.values())
    assert (k in s) is True  # testing __contains__ again
    del s[k]
    assert len(s) == 0

    # tuple as key test
    s = CouchDbTupleKeyStore(key_fields=('_id', 'user'))
    k = (1234, 'user')
    v = {'name': 'bob', 'age': 42}
    if k in s:  # deleting all docs in tmp
        del s[k]
    assert (k in s) is False  # see that key is not in store (and testing __contains__)
    orig_length = len(s)
    s[k] = v
    assert len(s) == orig_length + 1
    assert k in list(s)
    assert s[k] == v
    assert s.get(k) == v
    assert v in list(s.values())
    assert (k in s) is True # testing __contains__ again
    del s[k]
    assert len(s) == orig_length


if __name__ == '__main__':
    test_couchdb_store()
