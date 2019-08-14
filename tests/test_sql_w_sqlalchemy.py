import os

from py2store.stores.sql_w_sqlalchemy import SQLAlchemyTupleStore
from tests.base_test import BaseStoreTest

SQLITE_DB_PATH = 'test.db'
SQLITE_DB_URI = f'sqlite:///{SQLITE_DB_PATH}'
SQLITE_TABLE_NAME = 'test_table'


def clean_db_path(path=SQLITE_DB_PATH):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


class TestSQLAlchemyTupleStore(BaseStoreTest):
    key_dict = {
        'first_name': 'Yuri',
        'last_name': 'Gagarin',
    }
    key = tuple(key_dict.values())

    data_dict = {
        'height': '185sm',
        'weight': '80kg',
        'is_hero': 'yes he is',
    }
    data = tuple(data_dict.values())

    joined_values = {**key_dict, **data_dict}

    @classmethod
    def teardown_class(cls):
        clean_db_path()

    def test_crud(self):
        store = SQLAlchemyTupleStore(
            db_uri=SQLITE_DB_URI,
            collection_name=SQLITE_TABLE_NAME,
            key_fields=list(self.key_dict.keys()),
            data_fields=list(self.data_dict.keys()),
        )

        self._test_create(store)
        self._test_read(store)
        self._test_update(store)
        self._test_delete(store)
