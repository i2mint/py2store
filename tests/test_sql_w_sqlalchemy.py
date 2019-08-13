import os

import pytest

from py2store.stores.sql_w_sqlalchemy import SQLAlchemyPersister, SQLAlchemyStore


SQLITE_DB_PATH = 'test.db'
SQLITE_DB_URI = f'sqlite:///{SQLITE_DB_PATH}'


@pytest.fixture(scope='function')
def sqlite_db():
    yield
    try:
        os.remove(SQLITE_DB_PATH)
    except FileNotFoundError:
        pass


class TestSQLAlchemy:
    key = {
        'first_name': 'Yuri',
        'last_name': 'Gagarin',
    }
    key_as_tuple = tuple(key.values())

    data = {
        'height': '185sm',
        'weight': '80kg',
        'is_hero': 'yes he is',
    }
    data_as_tuple = tuple(data.values())

    joined_values = {**key, **data}

    def test_persister(self, sqlite_db):
        sql_dict = SQLAlchemyPersister(
            db_uri='sqlite:///test.db',
            collection_name='tmp',
            key_fields=list(self.key.keys()),
            data_fields=list(self.data.keys()),
        )

        # Assigning a value to a new key...
        sql_dict[self.key] = self.data
        assert len(sql_dict) == 1

        for k, v in self.joined_values.items():
            object_from_db = sql_dict[self.key]
            assert getattr(object_from_db, k) == v

        assert sql_dict.get(self.key) == object_from_db

        # Testing s.get with default...
        assert sql_dict.get({'first_name': 'totally not Yuri'}, 'default val') == 'default val'

        # Testing __contains__ again...
        assert self.key in sql_dict

        # Testing deleting key...
        del sql_dict[self.key]
        assert len(sql_dict) == 0

        # See that key is not in store (and testing __contains__)...
        assert self.key not in sql_dict
        assert len(sql_dict) == 0

    def test_store(self, sqlite_db):
        sql_dict = SQLAlchemyStore(
            db_uri='sqlite:///test.db',
            collection_name='tmp',
            key_fields=list(self.key.keys()),
            data_fields=list(self.data.keys()),
        )

        # Assigning a value to a new key...
        sql_dict[self.key_as_tuple] = self.data_as_tuple
        assert len(sql_dict) == 1
        assert sql_dict[self.key_as_tuple] == self.data_as_tuple
        assert sql_dict.get(self.key_as_tuple) == self.data_as_tuple

        # Testing s.get with default...
        assert sql_dict.get('totally not Yuri', 'default val') == 'default val'

        # Testing __contains__...
        assert self.key_as_tuple in sql_dict

        # Testing deleting key...
        del sql_dict[self.key_as_tuple]
        assert len(sql_dict) == 0

        # See that key is not in store (and testing __contains__)...
        assert self.key_as_tuple not in sql_dict
        assert len(sql_dict) == 0
