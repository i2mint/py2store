from collections.abc import MutableMapping
from pymongo import MongoClient
from functools import wraps
from py2store.base import Store


class MongoPersister(MutableMapping):
    """
    A basic mongo persister.
    Note that the mongo persister is designed not to overwrite the value of a key if the key already exists.
    You can subclass it and use update_one instead of insert_one if you want to be able to overwrite data.

    >>> s = MongoPersister(collection_name='tmp')
    >>> for _id in s:  # deleting all docs in tmp
    ...     del s[_id]
    >>> k = {'_id': 'foo'}
    >>> v = {'val': 'bar'}
    >>> k in s  # see that key is not in store (and testing __contains__)
    False
    >>> len(s)
    0
    >>> s[k] = v
    >>> len(s)
    1
    >>> list(s)
    [{'_id': 'foo'}]
    >>> s[k]
    {'val': 'bar'}
    >>> s.get(k)
    {'val': 'bar'}
    >>> s.get({'not': 'a key'}, {'default': 'val'})  # testing s.get with default
    {'default': 'val'}
    >>> list(s.values())
    [{'val': 'bar'}]
    >>> k in s  # testing __contains__ again
    True
    >>> del s[k]
    >>> len(s)
    0
    """

    def clear(self):
        raise NotImplementedError("clear is disabled by default, for your own protection! "
                                  "Loop and delete if you really want to.")

    def __init__(self, db_name='py2store', collection_name='test', key_fields=('_id',), mongo_client_kwargs=None):
        if mongo_client_kwargs is None:
            mongo_client_kwargs = {}
        self._mongo_client = MongoClient(**mongo_client_kwargs)
        self._db_name = db_name
        self._collection_name = collection_name
        self._mgc = self._mongo_client[db_name][collection_name]
        if isinstance(key_fields, str):
            key_fields = (key_fields,)

        self._key_projection = {k: True for k in key_fields}
        if '_id' not in key_fields:
            self._key_projection.update(_id=False)  # need to explicitly specify this since mongo includes _id by dflt
        self._not_key_projection = {k: False for k in key_fields}
        self._key_fields = key_fields





    def __getitem__(self, k):
        doc = self._mgc.find_one(k, projection=self._not_key_projection)
        if doc is not None:
            return doc
        else:
            raise KeyError(f"No document found for query: {k}")

    def __setitem__(self, k, v):
        return self._mgc.insert_one(dict(k, **v))

    def __delitem__(self, k):
        if len(k) > 0:
            return self._mgc.delete_one(k)
        else:
            raise KeyError(f"You can't removed that key: {k}")

    def __iter__(self):
        yield from self._mgc.find(projection=self._key_projection)

    def __len__(self):
        return self._mgc.count_documents({})


class MongoStore(Store):
    @wraps(MongoPersister.__init__)
    def __init__(self, *args, **kwargs):
        persister = MongoPersister(*args, **kwargs)
        super().__init__(persister)


class MongoTupleKeyStore(MongoStore):
    """
    MongoStore using tuple keys.

    >>> s = MongoTupleKeyStore(collection_name='tmp', key_fields=('_id', 'user'))
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
    def _id_of_key(self, k):
        return {field: field_val for field, field_val in zip(self.store._key_fields, k)}

    def _key_of_id(self, _id):
        return tuple(_id.values())


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
    assert (k in s) == True # testing __contains__ again
    del s[k]
    assert len(s) == 0