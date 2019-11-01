"""
How to run a test ArangoDB instance locally with a Docker container:

docker rm -f arangodb-instance && \
docker run -e ARANGO_ROOT_PASSWORD=somepassword -p 8529:8529 -d --name arangodb-instance arangodb && \
sleep 10 && \
pytest tests/test_arangodb.py
"""
from py2store.util import ModuleNotFoundWarning

with ModuleNotFoundWarning(f"{__file__}: One of the needed modules can't be found. Will skip this test."):
    from py2store.persisters.arangodb_w_pyarango import ArangoDbPersister
    from py2store.stores.arangodb_store import ArangoDbTupleKeyStore

    from tests.base_test import BasePersisterTest, BaseKeyTupleStoreTest

    DB_URL = 'http://127.0.0.1:8529'
    DB_PASSWORD = 'somepassword'


    class TestArangoDbPersister(BasePersisterTest):
        db = ArangoDbPersister(
            url=DB_URL,
            password=DB_PASSWORD,
            key_fields=list(BasePersisterTest.key.keys()),
        )


    class TestArangoDbTupleKeyStore(BaseKeyTupleStoreTest):
        db = ArangoDbTupleKeyStore(
            url=DB_URL,
            password=DB_PASSWORD,
            key_fields=BaseKeyTupleStoreTest.key_fields,
        )
