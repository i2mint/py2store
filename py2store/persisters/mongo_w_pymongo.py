from py2store.base import Persister

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from pymongo import MongoClient


class MongoPersister(Persister):
    """
    A basic mongo persister.
    Note that the mongo persister is designed not to overwrite the value of a key if the key already exists.
    You can subclass it and use update_one instead of insert_one if you want to be able to overwrite data.

    >>> s = MongoPersister()  # just use defaults
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
    >>>
    >>> # Making a persister whose keys are 2-dimensional and values are 3-dimensional
    >>> s = MongoPersister(db_name='py2store', collection_name='tmp',
    ...                     key_fields=('first', 'last'), data_fields=('yob', 'proj', 'bdfl'))
    >>> for _id in s:  # deleting all docs in tmp
    ...     del s[_id]
    >>> # writing two items
    >>> s[{'first': 'Guido', 'last': 'van Rossum'}] = {'yob': 1956, 'proj': 'python', 'bdfl': False}
    >>> s[{'first': 'Vitalik', 'last': 'Buterin'}] = {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    >>> # Seeing that those two items are there
    >>> for key, val in s.items():
    ...     print(f"{key} --> {val}")
    {'first': 'Guido', 'last': 'van Rossum'} --> {'yob': 1956, 'proj': 'python', 'bdfl': False}
    {'first': 'Vitalik', 'last': 'Buterin'} --> {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    """

    def clear(self):
        raise NotImplementedError("clear is disabled by default, for your own protection! "
                                  "Loop and delete if you really want to.")

    def __init__(self, db_name='py2store', collection_name='test', key_fields=('_id',), data_fields=None,
                 mongo_client_kwargs=None):
        if mongo_client_kwargs is None:
            mongo_client_kwargs = {}
        self._mongo_client = MongoClient(**mongo_client_kwargs)
        self._db_name = db_name
        self._collection_name = collection_name
        self._mgc = self._mongo_client[db_name][collection_name]
        if isinstance(key_fields, str):
            key_fields = (key_fields,)
        if data_fields is None:
            pass

        self._key_projection = {k: True for k in key_fields}
        if '_id' not in key_fields:
            self._key_projection.update(_id=False)  # need to explicitly specify this since mongo includes _id by dflt
        if data_fields is None:
            data_fields = {k: False for k in key_fields}
        elif not isinstance(data_fields, dict):
            data_fields = {k: True for k in data_fields}
            if '_id' not in data_fields:
                data_fields['_id'] = False
        self._data_fields = data_fields
        self._key_fields = key_fields

    def __getitem__(self, k):
        doc = self._mgc.find_one(k, projection=self._data_fields)
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
