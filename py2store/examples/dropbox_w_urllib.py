"""Dropbox read access with mapping interface -- using only builtins"""
import os
import zipfile
import tempfile
import urllib.request
from py2store.base import KvReader


class DropboxFolderCopyReader(KvReader):
    """Makes a full local copy of the folder (by default, to a local temp folder) and gives access to it."""

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
        yield from sorted(path for path in self._files if not path == '/')

    def __contains__(self, rel_path):
        return rel_path in self._files

    def _get_folder(self):
        download_from_dropbox(self.url, self._zip_filepath)
        self._unzip()
        os.remove(self._zip_filepath)

    def _unzip(self):
        with zipfile.ZipFile(self._zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(self.path)
            self._files = zip_ref.namelist()


class DropboxFileCopyReader(KvReader):
    def __init__(self, url, path=None):
        self.url = url
        self.path = path or self._get_filename_from_url()

        download_from_dropbox(self.url, self.path)
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


DFLT_USER_AGENT = 'Wget/1.16 (linux-gnu)'


def download_from_dropbox(url, file, chk_size=1024, user_agent=DFLT_USER_AGENT):
    def iter_content_and_copy_to(file):
        req = urllib.request.Request(url)
        req.add_header('user-agent', user_agent)
        with urllib.request.urlopen(req) as response:
            while True:
                chk = response.read(chk_size)
                if len(chk) > 0:
                    file.write(chk)
                else:
                    break

    if not isinstance(file, str):
        iter_content_and_copy_to(file)
    else:
        with open(file, 'wb') as _target_file:
            iter_content_and_copy_to(_target_file)


def bytes_from_dropbox(url, chk_size=1024, user_agent=DFLT_USER_AGENT):
    from io import BytesIO

    with BytesIO() as file:
        download_from_dropbox(url, file, chk_size=chk_size, user_agent=user_agent)
        file.seek(0)
        return file.read()


# DFLT_USER_AGENT = 'Wget/1.16 (linux-gnu)'
# def download_from_dropbox(url, file, as_zip=False, chunk_size=1024, user_agent=DFLT_USER_AGENT):
#
#     response = requests.get(
#         url,
#         params={'dl': int(as_zip)},
#         headers={'user-agent': user_agent},
#         stream=True,
#     )
#
#     def iter_content_and_copy_to(file):
#         for chunk in response.iter_content(chunk_size=chunk_size):
#             if chunk:
#                 file.write(chunk)
#
#     if not isinstance(file, str):
#         iter_content_and_copy_to(file)
#     else:
#         with open(file, 'wb') as _target_file:
#             iter_content_and_copy_to(_target_file)
#
#
# def bytes_from_dropbox(url, chunk_size=1024, user_agent=DFLT_USER_AGENT):
#     from io import BytesIO
#     with BytesIO() as file:
#         download_from_dropbox(url, file, chunk_size=chunk_size, user_agent=user_agent)
#         file.seek(0)
#         return file.read()
