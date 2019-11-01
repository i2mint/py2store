from py2store.persisters.ftp_persister import FtpPersister

URI = 'ftp://anonymous:anonymous@speedtest.tele2.net/'
ROOT_DIR = '/'
FILE_TO_READ = '1KB.zip'


class TestFtpPersister:
    db = FtpPersister(URI, collection=ROOT_DIR)

    def test_read_file(self):
        assert self.db[FILE_TO_READ]
