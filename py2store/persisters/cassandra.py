from abc import ABC
import uuid

from py2store.base import Persister
from cassandra.cluster import Cluster


KEYS_TABLE = 'storage_keys'
VALUES_TABLE = 'storage_values'
KEYS_TABLE_DFN = f'CREATE TABLE IF NOT EXISTS {KEYS_TABLE} (id uuid, OUTER_KEY TEXT primary key)'
VALUES_TABLE_DFN = f'CREATE TABLE IF NOT EXISTS {VALUES_TABLE} (key_id uuid primary key, VALUE TEXT)'
KEYSPACE_DFN = (
    'CREATE KEYSPACE IF NOT EXISTS py2store WITH REPLICATION = {'
    '\'class\': \'SimpleStrategy\','
    '\'replication_factor\': \'1\''
    '};'
)
USE_KEYSPACE = 'USE py2store'
SELECT_KEYS_QUERY = f'SELECT OUTER_KEY FROM {KEYS_TABLE}'
FIND_KEY_QUERY = f'SELECT id, OUTER_KEY from {KEYS_TABLE} WHERE OUTER_KEY = %s'
FIND_VALUE_QUERY = f'SELECT VALUE FROM {VALUES_TABLE} WHERE key_id = %s'
DEL_KEY_BY_ID_QUERY = f'DELETE FROM {KEYS_TABLE} WHERE OUTER_KEY = %s'
DEL_VAL_BY_KEY_ID_QUERY = f'DELETE FROM {VALUES_TABLE} WHERE key_id = %s'
INSERT_KEY_QUERY = f'INSERT INTO {KEYS_TABLE} (id, OUTER_KEY) VALUES (%s, %s)'
INSERT_VALUE_QUERY = f'INSERT INTO {VALUES_TABLE} (key_id, VALUE) VALUES (%s, %s)'
COUNT_QUERY = f'SELECT COUNT(*) FROM {KEYS_TABLE}'


class CassandraSessionManager(ABC):
    def __init__(self, session=None):
        self._session = session

        # tables creation
        commands = (KEYSPACE_DFN, USE_KEYSPACE, KEYS_TABLE_DFN, VALUES_TABLE_DFN)
        for command in commands:
            self._exec_command(command, tuple())

        super(CassandraSessionManager, self).__init__()

    def _exec_command(self, command, params):
        self._session.execute(command, params)
        return

    def _query(self, query):
        rows = self._session.execute(query)
        for row in rows:
            yield row

    def _query_all(self, query, params):
        return self._session.execute(query, params)

    def iter_keys(self):
        for row in self._query(SELECT_KEYS_QUERY):
            yield row[0]

    def rows_count(self):
        count_row = self._query_all(COUNT_QUERY, tuple())
        return count_row[0][0]

    def get_item(self, k):
        key_rows = self._query_all(FIND_KEY_QUERY, (k,))
        if not key_rows:
            raise KeyError(f"No document found for query: {k}")
        key_id = key_rows[0][0]
        rows = self._query_all(FIND_VALUE_QUERY, (key_id,))
        if not rows:
            raise KeyError(f"No document found for query: {k}")
        return rows[0][0]

    def del_item(self, k):
        key_rows = self._query_all(FIND_KEY_QUERY, (k,))
        if not key_rows:
            raise KeyError(f"No document found for query: {k}")
        key_id = key_rows[0][0]
        self._exec_command(DEL_VAL_BY_KEY_ID_QUERY, (key_id,))
        self._exec_command(DEL_KEY_BY_ID_QUERY, (k,))

    def insert(self, k, v):
        # del item if exists
        try:
            self.del_item(k)
        except KeyError:
            pass
        key_id = uuid.uuid4()
        self._exec_command(INSERT_KEY_QUERY, (key_id, k))
        self._exec_command(INSERT_VALUE_QUERY, (key_id, v))


class CassandraPersister(Persister):
    """
    A basic Cassandra persister.

    >>> s = CassandraPersister()
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
    >>> s = CassandraPersister()
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
            url='localhost',
            cassandra_kwargs=None
    ):
        if cassandra_kwargs is None:
            cassandra_kwargs = {'port': 9042}
        if isinstance(url, str):
            url = [url, ]

        self._cluster = Cluster(url, **cassandra_kwargs)
        self._session = self._cluster.connect()
        self._session_manager = CassandraSessionManager(self._session)

    def __getitem__(self, k):
        return self._session_manager.get_item(k)

    def __setitem__(self, k, v):
        self._session_manager.insert(k, v)

    def __delitem__(self, k):
        self._session_manager.del_item(k)

    def __iter__(self):
        return self._session_manager.iter_keys()

    def __len__(self):
        return self._session_manager.rows_count()
