from py2store.persisters.sql_w_sqlalchemy import SQLAlchemyPersister
from py2store.stores.sql_w_sqlalchemy import SQLAlchemyTupleStore
from tests.base_test import BasePersisterTest, BaseTupleStoreTest

SQLITE_DB_URI = 'sqlite:///:memory:'
SQLITE_TABLE_NAME = 'test_table'


class TestSQLAlchemyPersister(BasePersisterTest):
    db = SQLAlchemyPersister(
        uri=SQLITE_DB_URI,
        collection=SQLITE_TABLE_NAME,
        key_fields=list(BasePersisterTest.key.keys()),
        data_fields=list(BasePersisterTest.data.keys()),
    )

    def _assert_eq(self, obj_from_db, data):
        """ Custom comparison by attributes, since persister returns objects. """
        for data_key, data_val in data.items():
            val_from_db = getattr(obj_from_db, data_key)
            assert val_from_db == data_val


class TestSQLAlchemyPersisterInitedFromKwargs(TestSQLAlchemyPersister):
    db = SQLAlchemyPersister.from_kwargs(
        scheme='sqlite',
        database='test2.db',
        collection=SQLITE_TABLE_NAME,
        key_fields=list(BasePersisterTest.key.keys()),
        data_fields=list(BasePersisterTest.data.keys()),
    )


class TestSQLAlchemyTupleStore(BaseTupleStoreTest):
    db = SQLAlchemyTupleStore(
        uri=SQLITE_DB_URI,
        collection=SQLITE_TABLE_NAME,
        key_fields=BaseTupleStoreTest.key_fields,
        data_fields=BaseTupleStoreTest.data_fields,
    )
