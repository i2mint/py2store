class BaseStoreTest:
    """
    Base test for all Stores.
    """

    # Redefine these two:
    key = None
    data = None

    def _test_create(self, store):
        assert len(store) == 0

        # Assigning a value to a new key...
        store[self.key] = self.data
        assert len(store) == 1

    def _test_read(self, store):
        assert store[self.key] == self.data
        assert store.get(self.key) == self.data

        # Testing s.get with default...
        assert store.get('inexistent key', 'default val') == 'default val'

        # Testing __contains__...
        assert self.key in store

    def _test_update(self, store):
        new_data = tuple('_'.join((i, 'new')) for i in self.data)
        store[self.key] = new_data
        assert store[self.key] == new_data

    def _test_delete(self, store):
        del store[self.key]
        assert len(store) == 0

        # See that key is not in store (and testing __contains__)...
        assert self.key not in store
