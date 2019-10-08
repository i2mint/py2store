import os
import shutil

import pytest

from py2store.persisters.dropbox_w_requests import DropboxFolderCopyReader, DropboxFileCopyReader

SHARED_FOLDER_URL = 'https://www.dropbox.com/sh/0ru09jmk0w9tdnr/AAA-PPON2sYmwUUoGQpBQh1Ia?dl=1'
SHARED_FILE_URL = 'https://www.dropbox.com/s/wx9j4zm7zv9zffd/0b98e2af76c94a0a9cc2808866dd62de?dl=0'


@pytest.fixture()
def shared_folder_persister():
    path = 'tests/data/path'
    persister = DropboxFolderCopyReader(
        url=SHARED_FOLDER_URL,
        path=path,
    )
    yield persister
    try:
        shutil.rmtree(persister.path)
    except FileNotFoundError:
        pass


class TestDropboxSharedFolderPersister:
    def test_read(self, shared_folder_persister):
        files = [i for i in shared_folder_persister]
        assert files
        assert shared_folder_persister[files[-1]]


@pytest.fixture()
def shared_file_persister():
    persister = DropboxFileCopyReader(SHARED_FILE_URL)
    yield persister
    try:
        os.remove(persister.path)
    except FileNotFoundError:
        pass


class TestDropboxSharedFilePersister:

    def test_read(self, shared_file_persister):
        assert shared_file_persister.read()
        assert [i for i in shared_file_persister]
        assert shared_file_persister[1]
