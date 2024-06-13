import codecs
import pickle

from functools import wraps
from py2store.base import Store
from py2store.persisters.cassandra import CassandraPersister


class PickleSerializer:
    @staticmethod
    def loads(pickled):
        return pickle.loads(codecs.decode(pickled.encode(), "base64"))

    @staticmethod
    def dumps(obj):
        return codecs.encode(pickle.dumps(obj), "base64").decode()


class CassandraStore(Store):
    def clear(self):
        super(CassandraStore, self).clear()

    @wraps(CassandraPersister.__init__)
    def __init__(self, *args, **kwargs):
        persister = CassandraPersister(*args, **kwargs)
        self.serializer = PickleSerializer()
        super().__init__(persister)

    def _data_of_obj(self, v):
        return self.serializer.dumps(v)

    def _obj_of_data(self, data):
        return self.serializer.loads(data)

    def _id_of_key(self, k):
        return self.serializer.dumps(k)

    def _key_of_id(self, _id):
        return self.serializer.loads(_id)


def test_cassandra_store(s=CassandraStore(), k=None, v=None):
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

    k = (1234, 'user')
    v = {'name': 'bob', 'age': 42}
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
    assert len(s) == orig_length


if __name__ == '__main__':
    test_cassandra_store()
