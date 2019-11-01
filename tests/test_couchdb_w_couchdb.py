"""
How to run a test of CouchDB instance locally with a Docker container:

docker rm -f couchdb-test
docker run -d -p 5984:5984 --name couchdb-test couchdb
sleep 10
pytest tests/test_couchdb_w_couchdb.py
"""
from py2store.persisters.couchdb_w_couchdb import CouchDbPersister

from tests.base_test import BasePersisterTest

URI = 'http://localhost:5984'


class TestCouchDBPersister(BasePersisterTest):
    db = CouchDbPersister(
        URI,
        key_fields=list(BasePersisterTest.key.keys()),
    )
