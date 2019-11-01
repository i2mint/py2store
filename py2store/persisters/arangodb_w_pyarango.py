from py2store.base import Persister
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from pyArango.connection import Connection
    from pyArango.theExceptions import DocumentNotFoundError


class ArangoDbPersister(Persister):
    """
    A basic ArangoDB persister.
    >>> from py2store.persisters.arangodb_w_pyarango import ArangoDbPersister
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
            key_fields=('key',),  # _id, _key and _rev are reserved by db
            key_fields_separator='::',
    ):
        self._connection = Connection(
            arangoURL=url,
            username=user,
            password=password,
        )

        self._db_name = db_name
        self._collection_name = collection_name

        # If DB not created:
        if not self._connection.hasDatabase(self._db_name):
            self._connection.createDatabase(self._db_name)

        self._adb = self._connection[self._db_name]

        # If collection not created:
        if not self._adb.hasCollection(self._collection_name):
            self._collection = self._adb.createCollection(name=self._collection_name)

        self._collection = self._adb[self._collection_name]

        if isinstance(key_fields, str):
            key_fields = (key_fields,)

        self._key_fields = key_fields
        self._key_fields_separator = key_fields_separator

    def _make_key(self, keys_dict):
        """
        Convert a dict of keys into a real key-string by joining dict values in a predefined order.

        DB requirements for the key:
            The key must be a string value.
            Keys are case-sensitive.
            Numeric keys are not allowed.
            The key must be from 1 byte to 254 bytes long.
            It must consist of:
                - letters a-z (lower or upper case),
                - digits 0-9
                - any of the following characters: _ - : . @ ( ) + , = ; $ ! * ' %

            Any other characters cannot be used inside key values.
        """
        key_values = [keys_dict[key_label] for key_label in self._key_fields]
        key_str = self._key_fields_separator.join(key_values)
        return key_str

    def _split_key(self, joined_key_str):
        """
        Convert a key-string used by DB internally
        into a user-friendly dict of key labels and values.
        """
        key_values = joined_key_str.split(self._key_fields_separator)
        keys_dict = dict(zip(self._key_fields, key_values))
        return keys_dict

    def __fetchitem__(self, keys_dict):
        key = self._make_key(keys_dict)
        try:
            return self._collection[key]
        except DocumentNotFoundError:
            raise KeyError(f"No document found for query: {keys_dict}")

    def __getitem__(self, keys_dict):
        item = self.__fetchitem__(keys_dict)
        doc = item.getStore()

        # todo (Mike): maybe move this cleanup to a base Arango Store?
        # exclude reserved keys and corresponded values
        data = {
            key: doc[key]
            for key in doc
            if key not in self._reserved and
               key not in self._key_fields
        }
        return data

    def __setitem__(self, keys_dict, values_dict):
        try:
            doc = self.__fetchitem__(keys_dict)
        except KeyError:
            doc = self._collection.createDocument()
            doc._key = self._make_key(keys_dict)

        for k, v in values_dict.items():
            doc[k] = v

        doc.save()

    def __delitem__(self, keys_dict):
        doc = self.__fetchitem__(keys_dict)
        doc.delete()

    def __iter__(self):
        docs = self._collection.fetchAll()

        yield from (
            {
                key_name: doc[key_name]
                for key_name in self._key_fields
            }
            for doc in docs
        )

    def __len__(self):
        return self._collection.count()
