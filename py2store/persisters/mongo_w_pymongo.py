from functools import wraps
from typing import Callable, Mapping, Optional, Iterable

from py2store.base import KvReader, KvPersister
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from pymongo import MongoClient
    from pymongo.collection import Collection


class MongoCollectionReaderBase(KvReader):
    def __init__(self,
                 mgc: Optional[Collection] = None,
                 key_fields=("_id",),
                 data_fields: Optional[Iterable] = None,
                 filt: Optional[dict] = None):
        if mgc is None:
            mgc = _mk_dflt_mgc()
        self._mgc = mgc
        if isinstance(key_fields, str):
            key_fields = (key_fields,)
        if data_fields is None:
            pass

        self._key_projection = {k: True for k in key_fields}
        if "_id" not in key_fields:
            self._key_projection.update(
                _id=False
            )  # need to explicitly specify this since mongo includes _id by dflt
        if data_fields is None:
            data_fields = {k: False for k in key_fields}
        elif not isinstance(data_fields, dict):
            data_fields = {k: True for k in data_fields}
            if "_id" not in data_fields:
                data_fields["_id"] = False
        self._data_fields = data_fields
        self._key_fields = key_fields

        if filt is None:
            filt = {}
        self._filt = filt

    @classmethod
    def from_params(
            cls,
            db_name: str = "py2store",
            collection_name: str = "test",
            key_fields: Iterable = ("_id",),
            data_fields: Optional[Iterable] = None,
            filt: Optional[dict] = None,
            mongo_client: Optional[dict] = None,
    ):
        if mongo_client is None:
            mongo_client = MongoClient()
        elif isinstance(mongo_client, dict):
            mongo_client = MongoClient(**mongo_client)

        return cls(
            mgc=mongo_client[db_name][collection_name],
            key_fields=key_fields,
            data_fields=data_fields,
            filt=filt,
        )

    def _filtered_key(self, k):
        return dict(k, **self._filt)

    def __getitem__(self, k):
        assert isinstance(k, Mapping), \
            f"k (key) must be a mapping (typically a dictionary). Were:\n\tk={k}"
        return self._mgc.find(filter=self._filtered_key(k), projection=self._data_fields)

    def __iter__(self):
        yield from self._mgc.find(filter=self._filt, projection=self._key_projection)

    def __len__(self):
        return self._mgc.count_documents(self._filt)

    def __contains__(self, k):
        cursor = self._mgc.find(filter=self._filtered_key(k), projection={'_id': False})
        r = next(cursor, False)
        if r is not False:
            return True

    def items(self):
        for doc in self._mgc.find(filter=self._filt, projection=dict(self._key_projection, **self._data_fields)):
            key = {k: doc.pop(k) for k in self._key_fields}
            yield key, doc

    def values(self):
        yield from self._mgc.find(filter=self._filt, projection=self._data_fields)

    def keys(self):
        yield from self._mgc.find(filter=self._filt, projection=self._key_projection)

    def __length_hint__(self):  # TODO: Proper/common/canonical use of __length_hint__?
        """Estimates the TOTAL number of documents in the collection (NOT filtered by any filt)."""
        return self._mgc.estimated_document_count()


class MongoCollectionReader(MongoCollectionReaderBase):
    """

    """

    def __getitem__(self, k):
        cursor = super().__getitem__(k)
        doc = next(cursor, None)
        if doc is not None:
            return doc
        else:
            raise KeyError(f"No document found for query: {k}")


class GetitemAsQueryCursorMixin:
    def __getitem__(self, k):
        assert isinstance(k, Mapping), \
            f"k (key) must be a mapping (typically a dictionary). Were:\n\tk={k}"
        return self._mgc.find(filter=self._filtered_key(k), projection=self._data_fields)


class MongoCollectionPersister(MongoCollectionReader):
    """
    >>> s = MongoCollectionPersister()  # just use defaults
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
    >>> s = MongoCollectionPersister.from_params(db_name='py2store', collection_name='tmp',
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

    def __setitem__(self, k, v):
        assert isinstance(k, Mapping) and isinstance(v, Mapping), \
            f"k (key) and v (value) must both be mappings (often dictionaries). Were:\n\tk={k}\n\tv={v}"
        return self._mgc.insert_one(dict(v, **self._filtered_key(k)))

    def __delitem__(self, k):
        if len(k) > 0:
            return self._mgc.delete_one(self._filtered_key(k))
        else:
            raise KeyError(f"You can't removed that key: {k}")


class MongoAppendablePersister(MongoCollectionPersister):
    def append(self, v):
        return self._mgc.insert_one(v)

    def extend(self, items):
        return self._mgc.insert_many(items)


class MongoClientReader(KvReader):
    @wraps(MongoClient.__init__)
    def __init__(self, **mongo_client_kwargs):
        self._mongo_client = MongoClient(**mongo_client_kwargs)

    def __iter__(self):
        yield from self._mongo_client.list_database_names()

    def __getitem__(self, k):
        return MongoDbReader(
            db_name=k, mongo_client=self._mongo_client
        )  # or just wrap self._mongo_client[k]?


class MongoDbReader(KvReader):
    def __init__(
            self,
            db_name="py2store",
            mk_collection_store=MongoCollectionReader,
            mongo_client=None,
            **mongo_client_kwargs,
    ):
        """Base Mongo Db Reader. Keys are collection names and values are collection store instances.

        :param db_name: Name of db
        :param mk_collection_store: Function that is called on a key (collection name) to make the
            collection store instance.
            Use mk_collection_store to define what kind of collection stores you want to make.
            Will be called with only one unnamed argument; the collection name.
            Use custom classes here, and/or partials (curried functions) thereof, to fix any parameters you want to fix.
        :param mongo_client: MongoClient instance, kwargs to make it (MongoClient(**kwargs)), or callable to make it
        :param mongo_client_kwargs: **kwargs to make a MongoClient, that is used if mongo_client is callable
        """
        if mongo_client is None:
            self._mongo_client = MongoClient(**mongo_client_kwargs)
        elif isinstance(mongo_client, dict):
            self._mongo_client = MongoClient(**mongo_client)
        else:
            self._mongo_client = mongo_client
        self._db_name = db_name
        self.db = self._mongo_client[db_name]
        self.collection_store_cls = mk_collection_store

    def __iter__(self):
        yield from self.db.list_collection_names()

    def __getitem__(self, k):
        return self.collection_store_cls(self.db[k])


def _mk_dflt_mgc():
    return MongoClient()["py2store"]["test"]


class OldMongoPersister(KvPersister):
    """
    A basic mongo persister.
    Note that the mongo persister is designed not to overwrite the value of a key if the key already exists.
    You can subclass it and use update_one instead of insert_one if you want to be able to overwrite data.

    >>> s = OldMongoPersister()  # just use defaults
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
    >>> s = OldMongoPersister(db_name='py2store', collection_name='tmp',
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

    def __init__(
            self,
            db_name="py2store",
            collection_name="test",
            key_fields=("_id",),
            data_fields=None,
            mongo_client_kwargs=None,
    ):
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
        if "_id" not in key_fields:
            self._key_projection.update(
                _id=False
            )  # need to explicitly specify this since mongo includes _id by dflt
        if data_fields is None:
            data_fields = {k: False for k in key_fields}
        elif not isinstance(data_fields, dict):
            data_fields = {k: True for k in data_fields}
            if "_id" not in data_fields:
                data_fields["_id"] = False
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


class OldMongoInsertPersister(OldMongoPersister):
    def __init__(
            self,
            db_name="py2store",
            collection_name="test",
            data_fields=None,
            mongo_client_kwargs=None,
    ):
        super().__init__(
            db_name=db_name,
            collection_name=collection_name,
            data_fields=data_fields,
            key_fields=("_id",),
            mongo_client_kwargs=mongo_client_kwargs,
        )

    def append(self, v):
        return self._mgc.insert_one(v)

    def extend(self, items):
        return self._mgc.insert_many(items)
