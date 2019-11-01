from os import environ
from uuid import uuid4
from tests.base_test import BasePersisterTest
from py2store.util import ModuleNotFoundWarning

with ModuleNotFoundWarning(f"{__file__}: One of the needed modules can't be found. Will skip this test."):
    from py2store.persisters.dropbox_w_dropbox import DropboxPersister, DropboxLinkPersister

    ROOT_DIR = environ.get('DROPBOX_ROOT_DIR', '/test_data')
    TOKEN = environ.get('DROPBOX_TOKEN')


    class TestDropboxPersister(BasePersisterTest):
        db = DropboxPersister(
            rootdir=ROOT_DIR,
            oauth2_access_token=TOKEN,
        )

        key = '/'.join((ROOT_DIR, uuid4().hex))
        data = b'Some binary data here.'
        data_updated = b'Smth completely different.'
        inexistent_key = '/'.join((ROOT_DIR, uuid4().hex, 'x'))


    class TestDropboxLinkPersister(TestDropboxPersister):
        db = DropboxLinkPersister(
            url='https://www.dropbox.com/sh/0ru09jmk0w9tdnr/AAA-PPON2sYmwUUoGQpBQh1Ia?dl=0',
            oauth2_access_token=TOKEN,
        )

        def _create_test_file(self):
            db = DropboxPersister(
                rootdir=ROOT_DIR,
                oauth2_access_token=TOKEN,
            )
            db[self.key] = self.data

        def test_crud(self):
            # Read-a-file test only, since LinkPersister has a read-only access.
            self._create_test_file()
            self._test_read()

            all_objects = list(self.db)
            key = all_objects[0]
            assert self.db[key]
