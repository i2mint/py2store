import os
import zipfile
import tempfile
from py2store.base import Reader
from py2store.mixins import ReadOnlyMixin
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import requests


class DropboxFolderCopyReader(Reader):
    """Makes a full local copy of the folder (by default, to a local temp folder) and gives access to it.
    """
    def __init__(self, url, path=tempfile.gettempdir()):
        self.url = url
        self.path = path

        os.makedirs(self.path, exist_ok=True)
        self._zip_filepath = os.path.join(self.path, 'shared_folder.zip')

        self._files = []
        self._get_folder()

    def __getitem__(self, rel_path):
        real_path = os.path.join(self.path, rel_path)
        try:
            with open(real_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            raise KeyError(f"Key doesn't exist: {rel_path}")

    def __iter__(self):
        yield from sorted(
            path for path in self._files
            if not path == '/'
        )

    def __contains__(self, rel_path):
        return rel_path in self._files

    def _get_folder(self):
        download_from_dropbox(self.url, self._zip_filepath, as_zip=True)
        self._unzip()
        os.remove(self._zip_filepath)

    def _unzip(self):
        with zipfile.ZipFile(self._zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(self.path)
            self._files = zip_ref.namelist()


class DropboxFileCopyReader(Reader):
    def __init__(self, url, path=None):
        self.url = url
        self.path = path or self._get_filename_from_url()

        download_from_dropbox(self.url, self.path, as_zip=False)
        self.file = open(self.path, 'r')

    def __getitem__(self, index):
        self.file.seek(0)
        return self.readlines()[index]

    def __iter__(self):
        self.file.seek(0)
        yield from self.file

    def __len__(self):
        return len(self.readlines())

    def __contains__(self, k):
        return k in self.read()

    def __del__(self):
        if self.file:
            self.file.close()
            self.file = None

    def read(self):
        self.file.seek(0)
        return self.file.read()

    def readlines(self):
        self.file.seek(0)
        return self.file.readlines()

    def _get_filename_from_url(self):
        # 'https:...txt?dl=0&smth=else' -> 'https:...txt'
        url_w_no_params = self.url.split('?', 1)[0]

        # 'https://www.dropbox.com/.../my_file.txt' -> 'my_file.txt'
        last_part_of_urls_path = url_w_no_params.rsplit('/', 1)[-1]
        return last_part_of_urls_path


def download_from_dropbox(url, path, as_zip=False):
    response = requests.get(
        url,
        params={'dl': int(as_zip)},
        headers={'user-agent': 'Wget/1.16 (linux-gnu)'},
        stream=True,
    )
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
