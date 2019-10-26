from functools import wraps

from py2store.base import Store
from py2store.persisters.arangodb_w_pyarango import ArangoDbPersister
from py2store.util import lazyprop


class ArangoDbStore(Store):
    @wraps(ArangoDbPersister.__init__)
    def __init__(self, *args, **kwargs):
        persister = ArangoDbPersister(*args, **kwargs)
        super().__init__(persister)


class ArangoDbTupleKeyStore(ArangoDbStore):
    """
    ArangoDbStore using tuple keys.

    >>> from py2store.stores.arangodb_store import ArangoDbTupleKeyStore
    >>> s = ArangoDbTupleKeyStore(collection_name='test', key_fields=('key', 'user'))
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
