from random import randint
from uuid import uuid4


class BaseTest:
    """ Base test class for persisters and stores. """

    db = None  # Redefine me!

    key = {
        'first_name': 'Robot',
        'last_name': str(uuid4().hex),
    }
    data = {
        'height': '100sm',
        'weight': '50kg',
        'fav number': str(randint(1, 100)),
    }

    data_updated = data.copy()
    data_updated['fav number'] = '9000'

    def test_crud(self):
        self._test_create()
        self._test_read()
        self._test_update()
        self._test_delete()

    def _test_create(self):
        initial_len = len(self.db)

        self.db[self.key] = self.data
        assert len(self.db) == initial_len + 1

    def _test_read(self):
        assert self.key in self.db

        self._assert_eq(self.db[self.key], self.data)
        self._assert_eq(self.db.get(self.key), self.data)

        default_value = object()
        assert self.db.get(self.inexistent_key, default_value) is default_value

    def _test_update(self):
        self.db[self.key] = self.data_updated
        self._assert_eq(self.db[self.key], self.data_updated)

    def _test_delete(self):
        initial_len = len(self.db)

        del self.db[self.key]
        assert len(self.db) == initial_len - 1
        assert self.key not in self.db

    def _assert_eq(self, obj_from_db, data):
        assert obj_from_db == data

    @classmethod
    def teardown_class(cls):
        del cls.db


class BasePersisterTest(BaseTest):
    """ Base test for all Persisters. """
    inexistent_key = {'first_name': 'inexistent key value'}


class BaseStoreTest(BaseTest):
    """ Base test for all Stores. """
    inexistent_key = 'inexistent key'

    key_fields = list(BaseTest.key.keys())
    data_fields = list(BaseTest.data.keys())


class BaseKeyTupleStoreTest(BaseStoreTest):
    """ Base test for all Stores with Keys as tuples. """
    key = tuple(BaseTest.key.values())


class BaseTupleStoreTest(BaseKeyTupleStoreTest):
    """ Base test for all Stores with Keys and Values as tuples. """
    data = tuple(BaseTest.data.values())
    data_updated = tuple(BaseTest.data_updated.values())
