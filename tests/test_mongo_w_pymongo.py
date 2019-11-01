"""
How to run a test MongoDB instance locally with a Docker container:

docker rm -f mongo-test && \
docker run -d -p 27017:27017 --name mongo-test mongo && \
sleep 10 && \
pytest tests/test_mongo_w_pymongo.py
"""
from py2store.persisters.mongo_w_pymongo import MongoPersister

from tests.base_test import BasePersisterTest

URI = 'mongodb://localhost:27017/test_db'


class TestMongoPersister(BasePersisterTest):
    db = MongoPersister(
        URI,
        key_fields=list(BasePersisterTest.key.keys()),
    )

    def _assert_eq(self, obj_from_db, data):
        """ Custom comparison by attributes, since persister returns dicts. """
        for data_key, data_val in data.items():
            val_from_db = obj_from_db[data_key]
            assert val_from_db == data_val
