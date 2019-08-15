from py2store.base import Persister
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from pyArango.connection import Connection


class ArangoDbPersister(Persister):
    """
    A basic ArangoDB persister.
    >>> from py2store.persisters._arangodb_in_progress import ArangoDbPersister
    >>> s = ArangoDbPersister()
    >>> k = {'key': '777'} # Each collection will happily accept user-defined _key values.
    >>> v = {'val': 'bar'}
    >>> for _key in s:
    ...     del s[_key]
    ...
    >>> k in s
    False
    >>> len(s)
    0
    >>> s[k] = v
    >>> len(s)
    1
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
    >>> s = ArangoDbPersister(db_name='py2store', key_fields=('name',))
    >>> for _key in s:
    ...     del s[_key]
    ...
    >>> s[{'name': 'guido'}] = {'yob': 1956, 'proj': 'python', 'bdfl': False}
    >>> s[{'name': 'guido'}]
    {'yob': 1956, 'proj': 'python', 'bdfl': False}
    >>> s[{'name': 'vitalik'}] = {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    >>> s[{'name': 'vitalik'}]
    {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    >>> for key, val in s.items():
    ...     print(f"{key}: {val}")
    {'name': 'guido'}: {'yob': 1956, 'proj': 'python', 'bdfl': False}
    {'name': 'vitalik'}: {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    """

    # reserved by the database fields
    _reserved = {"_key", "_id", "_rev"}

    def __init__(
            self,
            user='root',
            password='root',
            url='http://127.0.0.1:8529',
            db_name='py2store',
            collection_name='test',
            key_fields=('key',)  # _id, _key and _rev are reserved by db
    ):
        self._connection = Connection(arangoURL=url, username=user, password=password)
        self._db_name = db_name
        self._collection_name = collection_name
        # if db not created
        if not self._connection.hasDatabase(self._db_name):
            self._connection.createDatabase(self._db_name)

        self._adb = self._connection[self._db_name]
        # if collection not created
        if not self._adb.hasCollection(self._collection_name):
            self._collection = self._adb.createCollection(name=self._collection_name)

        self._collection = self._adb[self._collection_name]

        if isinstance(key_fields, str):
            key_fields = (key_fields,)

        self._key_fields = key_fields

    def __fetchitem__(self, k):
        f = self._collection.fetchFirstExample(k)
        if f is not None and len(f) == 1:
            return f[0]

        return None

    def __getitem__(self, k):
        f = self.__fetchitem__(k)
        if f is not None:
            d = f.getStore()
            # exclude reserved keys and corresponded values
            d = {x: d[x] for x in d if x not in self._reserved and x not in self._key_fields}
            return d
        else:
            raise KeyError(f"No document found for query: {k}")

    def __setitem__(self, k, v):
        doc = self._collection.createDocument(dict(k, **v))
        doc.save()

    def __delitem__(self, k):
        if len(k) > 0:
            f = self.__fetchitem__(k)
            if f is not None:
                return f.delete()

        raise KeyError(f"You can't removed that key: {k}")

    def __iter__(self):
        docs = self._collection.fetchAll()

        yield from [{x: d[x] for x in d.getStore() if x in self._key_fields} for d in docs]

    def __len__(self):
        return self._collection.count()
