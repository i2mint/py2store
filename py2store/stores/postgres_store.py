import codecs
import pickle
import psycopg2

from abc import ABC
from collections.abc import MutableMapping
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from py2store import Store

KEYS_TABLE = 'storage_keys'
VALUES_TABLE = 'storage_values'
KEYS_TABLE_DFN = f'CREATE TABLE IF NOT EXISTS {KEYS_TABLE} (id SERIAL PRIMARY KEY, OUTER_KEY TEXT NOT NULL)'
VALUES_TABLE_DFN = (
    f'CREATE TABLE IF NOT EXISTS {VALUES_TABLE}'
    f' (id SERIAL PRIMARY KEY, key_id integer REFERENCES {KEYS_TABLE} (id), VALUE TEXT NOT NULL)'
)
SELECT_KEYS_QUERY = f'SELECT OUTER_KEY FROM {KEYS_TABLE}'
SELECT_QUERY = (
    f'SELECT VALUE FROM {KEYS_TABLE} INNER JOIN {VALUES_TABLE} ON {KEYS_TABLE}.id = {VALUES_TABLE}.key_id'
)
FIND_KEY_QUERY = f'SELECT id, OUTER_KEY from {KEYS_TABLE} WHERE OUTER_KEY = %s'
FIND_VALUE_QUERY = f'{SELECT_QUERY} WHERE OUTER_KEY = %s'
DEL_KEY_BY_ID_QUERY = f'DELETE FROM {KEYS_TABLE} WHERE id = %s'
DEL_VAL_BY_KEY_ID_QUERY = f'DELETE FROM {VALUES_TABLE} WHERE key_id = %s'
INSERT_KEY_QUERY = f'INSERT INTO {KEYS_TABLE} (OUTER_KEY) VALUES (%s)'
INSERT_VALUE_QUERY = f'INSERT INTO {VALUES_TABLE} (key_id, VALUE) VALUES (%s, %s)'
COUNT_QUERY = f'SELECT COUNT(*) FROM {KEYS_TABLE}'


class PostgresConnectionManager(ABC):
    def __init__(self, pg_client_kwargs=None):
        if pg_client_kwargs is None:
            pg_client_kwargs = {}
        self._connection = self._connect(pg_client_kwargs)

        # tables creation
        commands = (KEYS_TABLE_DFN, VALUES_TABLE_DFN)
        for command in commands:
            self._exec_command(command, tuple())

        super(PostgresConnectionManager, self).__init__()

    def _connect(self, pg_client_kwargs):
        raise NotImplementedError()

    def _exec_command(self, command, params, use_last_val=False):
        raise NotImplementedError()

    def _query(self, query):
        raise NotImplementedError()

    def _query_all(self, query, params):
        raise NotImplementedError()

    def iter_keys(self):
        for row in self._query(SELECT_KEYS_QUERY):
            yield row[0]

    def rows_count(self):
        count_row = self._query_all(COUNT_QUERY, tuple())
        return count_row[0][0]

    def get_item(self, k):
        rows = self._query_all(FIND_VALUE_QUERY, (k,))
        if not rows:
            raise KeyError(f"No document found for query: {k}")
        return rows[0][0]

    def del_item(self, k):
        key_rows = self._query_all(FIND_KEY_QUERY, (k,))
        if not key_rows:
            raise KeyError(f"No document found for query: {k}")
        key_id = key_rows[0][0]
        self._exec_command(DEL_VAL_BY_KEY_ID_QUERY, (key_id,))
        self._exec_command(DEL_KEY_BY_ID_QUERY, (key_id,))

    def insert(self, k, v):
        # del item if exists
        try:
            self.del_item(k)
        except KeyError:
            pass
        key_id = self._exec_command(INSERT_KEY_QUERY, (k,), True)
        self._exec_command(INSERT_VALUE_QUERY, (key_id, v))


class PsycopgConnectionManager(PostgresConnectionManager):
    def __init__(self, pg_client_kwargs):
        super(PsycopgConnectionManager, self).__init__(pg_client_kwargs)

    def _connect(self, connection_kwargs):
        try:
            return psycopg2.connect(**connection_kwargs)
        except psycopg2.OperationalError:
            # probably DB not created yet
            db_name = connection_kwargs['dbname']
            connection_kwargs['dbname'] = 'postgres'
            conn = psycopg2.connect(**connection_kwargs)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            cur.execute(f'CREATE DATABASE {db_name}')
            cur.close()
            conn.commit()

            connection_kwargs['dbname'] = db_name
            return psycopg2.connect(**connection_kwargs)

    def _exec_command(self, command, params, use_last_val=False):
        cur = self._connection.cursor()
        cur.execute(command, params)

        last_val = None
        if use_last_val:
            cur.execute('SELECT LASTVAL()')
            last_val = cur.fetchone()[0]
        cur.close()
        self._connection.commit()
        return last_val

    def _query(self, query):
        cur = self._connection.cursor()
        cur.execute(query)

        row = cur.fetchone()
        while row is not None:
            yield row
            row = cur.fetchone()

    def _query_all(self, query, params):
        cur = self._connection.cursor()
        cur.execute(query, params)

        rows = cur.fetchall()
        cur.close()
        return rows


class PostgresPersister(MutableMapping):
    def __init__(self, pg_client_kwargs=None):
        self.conn_manager = PsycopgConnectionManager(pg_client_kwargs)

    def __iter__(self):
        return self.conn_manager.iter_keys()

    def __len__(self) -> int:
        return self.conn_manager.rows_count()

    def __getitem__(self, k):
        return self.conn_manager.get_item(k)

    def __delitem__(self, k) -> None:
        self.conn_manager.del_item(k)

    def __setitem__(self, k, v) -> None:
        self.conn_manager.insert(k, v)


class PickleSerializer:
    @staticmethod
    def loads(pickled):
        return pickle.loads(codecs.decode(pickled.encode(), "base64"))

    @staticmethod
    def dumps(obj):
        return codecs.encode(pickle.dumps(obj), "base64").decode()


class PostgresStore(Store):
    def clear(self):
        super(PostgresStore, self).clear()

    def __init__(self, db_name='py2store'):
        conn_params = {
            'dbname': db_name,

        }
        self.persister = PostgresPersister(conn_params)
        self.serializer = PickleSerializer()
        super(PostgresStore, self).__init__(self.persister)

    def _data_of_obj(self, v):
        return self.serializer.dumps(v)

    def _obj_of_data(self, data):
        return self.serializer.loads(data)

    def _id_of_key(self, k):
        return self.serializer.dumps(k)

    def _key_of_id(self, _id):
        return self.serializer.loads(_id)


def test_psql_store(s=PostgresStore(), k=None, v=None):
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


if __name__ == '__main__':
    test_psql_store()
