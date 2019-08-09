from collections.abc import Iterable
from py2store.base import Persister
from couchdb import Server


class CouchDbPersister(Persister):
    """
    A basic couchDB persister.
    Note that the couchDB persister is designed not to overwrite the value of a key if the key already exists.
    You can subclass it and use update_one instead of insert_one if you want to be able to overwrite data.

    >>> s = CouchDbPersister()
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
    >>> s = CouchDbPersister(db_name='py2store', key_fields=('name',), data_fields=('yob', 'proj', 'bdfl'))
    >>> for _id in s:  # deleting all docs in tmp
    ...     del s[_id]
    >>> s[{'name': 'guido'}] = {'yob': 1956, 'proj': 'python', 'bdfl': False}
    >>> s[{'name': 'vitalik'}] = {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    >>> for key, val in s.items():
    ...     print(f"{key}: {val}")
    {'name': 'guido'}: {'yob': 1956, 'proj': 'python', 'bdfl': False}
    {'name': 'vitalik'}: {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    """

    def clear(self):
        raise NotImplementedError(
            "clear is disabled by default, for your own protection! "
            "Loop and delete if you really want to."
        )

    def __init__(
            self,
            user='admin',
            password='admin',
            url='http://127.0.0.1:5984',
            db_name='py2store',
            key_fields=('_id', ),
            data_fields=None,
            couchdb_client_kwargs=None
    ):
        if couchdb_client_kwargs is None:
            couchdb_client_kwargs = {}
        if user and password:
            # put credentials in url if provided like https://username:password@example.com:5984/
            if '//' in url:  # if scheme present
                url = f'{url.split("//")[0]}//{user}:{password}@{url.split("//")[1]}'
            else:
                url = f'http//{user}:{password}@{url}'
        self._couchdb_server = Server(url=url, **couchdb_client_kwargs)
        self._db_name = db_name
        # if db not created
        if db_name not in self._couchdb_server:
            self._couchdb_server.create(db_name)
        self._cdb = self._couchdb_server[db_name]
        if isinstance(key_fields, str):
            key_fields = (key_fields,)
        if data_fields is None:
            pass

        # filter out _rev field on output
        if data_fields is None:
            self._data_fields = {k: False for k in key_fields}
            if '_rev' not in key_fields:
                self._data_fields['_rev'] = False
        elif not isinstance(data_fields, dict) and isinstance(data_fields, Iterable):
            self._data_fields = {k: True for k in data_fields}
            if '_id' not in data_fields:
                self._data_fields['_id'] = False
            if '_rev' not in self._data_fields:
                self._data_fields['_rev'] = False

        self._key_fields = key_fields

    def __getitem__(self, k):
        mango_q = {
            'selector': k,
        }
        docs = self._cdb.find(mango_q, self.__return_doc_filter)
        docs = list(docs)
        if len(docs) != 0:
            return docs[0]
        else:
            raise KeyError(f"No document found for query: {k}")

    def __setitem__(self, k, v):
        return self._cdb.save(dict(k, **v))

    def __delitem__(self, k):
        if len(k) > 0:
            mango_q = {
                'selector': k,
            }
            docs = self._cdb.find(mango_q)  # to delete document we need _rev and _id fields, so skip output filtering
            for doc in docs:
                self._cdb.delete(doc)
        else:
            raise KeyError(f"You can't removed that key: {k}")

    def __iter__(self):
        mango_q = {
            'selector': {},
            'fields': self._key_fields
        }
        yield from self._cdb.find(mango_q)

    def __len__(self):
        return self._cdb.info()['doc_count']

    def __return_doc_filter(self, doc):
        doc = dict(doc)
        for data_field in self._data_fields:
            if not self._data_fields[data_field]:
                del doc[data_field]
        return doc
