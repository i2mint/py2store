from py2store.base import Persister
from py2store.mixins import ReadOnlyMixin

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from dropbox import Dropbox
    from dropbox.files import DownloadError
    from dropbox.files import LookupError as DropboxLookupError
    from dropbox.exceptions import ApiError
    from dropbox.files import WriteMode, SharedLink


def _is_file_not_found_error(error_object):
    if isinstance(error_object, ApiError):
        if len(error_object.args) >= 2:
            err = error_object.args[1]
            if isinstance(err, DownloadError) and isinstance(err.get_path(), DropboxLookupError):
                return True
    return False


class DropboxPersister(Persister):
    """
    A persister for dropbox.
    You need to have the python connector (if you don't: pip install dropbox)
    You also need to have a token for your dropbox app. If you don't it's a google away.
    Finally, for the test below, you need to put this token in ~/.py2store_configs.json' under key
    dropbox.__init__kwargs, and have a folder named /py2store_data/test/ in your app space.

    >>> import json
    >>> import os
    >>>
    >>> configs = json.load(open(os.path.expanduser('~/.py2store_configs.json')))
    >>> s = DropboxPersister('/py2store_data/test/', **configs['dropbox']['__init__kwargs'])
    >>> if '/py2store_data/test/_can_remove' in s:
    ...     del s['/py2store_data/test/_can_remove']
    ...
    >>>
    >>> n = len(s)
    >>> if n == 1:
    ...     assert list(s) == ['/py2store_data/test/_can_remove']
    ...
    >>> s['/py2store_data/test/_can_remove'] = b'this is a test'
    >>> assert len(s) == n + 1
    >>> assert s['/py2store_data/test/_can_remove'] == b'this is a test'
    >>> '/py2store_data/test/_can_remove' in s
    True
    >>> del s['/py2store_data/test/_can_remove']
    """

    def __init__(self, rootdir, oauth2_access_token,
                 connection_kwargs=None, files_upload_kwargs=None,
                 files_list_folder_kwargs=None, rev=None):

        if connection_kwargs is None:
            connection_kwargs = {}
        if files_upload_kwargs is None:
            files_upload_kwargs = {'mode': WriteMode.overwrite}
        if files_list_folder_kwargs is None:
            files_list_folder_kwargs = {'recursive': True, 'include_non_downloadable_files': False}

        self._prefix = rootdir
        self._con = Dropbox(oauth2_access_token, **connection_kwargs)
        self._connection_kwargs = connection_kwargs
        self._files_upload_kwargs = files_upload_kwargs
        self._files_list_folder_kwargs = files_list_folder_kwargs
        self._rev = rev

    # TODO: __len__ is taken from Persister, which iterates and counts. Not efficient. Find direct api for this!

    def __iter__(self):
        r = self._con.files_list_folder(self._prefix)
        yield from (x.path_display for x in r.entries)
        cursor = r.cursor
        if r.has_more:
            r = self._con.files_list_folder_continue(cursor)
            yield from (x.path_display for x in r.entries)

    def __getitem__(self, k):
        try:
            metadata, contents_response = self._con.files_download(k)
        except ApiError as e:
            if _is_file_not_found_error(e):
                raise KeyError(f"Key doesn't exist: {k}")
            raise

        if not contents_response.status_code:
            raise ValueError(
                "Response code wasn't 200 when trying to download a file (yet the file seems to exist).")

        return contents_response.content

    def __setitem__(self, k, v):
        return self._con.files_upload(v, k, **self._files_upload_kwargs)

    def __delitem__(self, k):
        return self._con.files_delete_v2(k, self._rev)


def _entry_is_dir(entry):
    return not hasattr(entry, 'is_downloadable')


def _entry_is_file(entry):
    return hasattr(entry, 'is_downloadable')


def _extend_path(path, extension):
    extend_path = '/' + path + '/' + extension + '/'
    extend_path.replace('//', '/')
    return extend_path


class DropboxLinkPersister(ReadOnlyMixin, DropboxPersister):
    def __init__(self, url, oauth2_access_token):
        self._con = Dropbox(oauth2_access_token)
        self.url = url
        self.shared_link = SharedLink(url=url)

    def _yield_from_files_list_folder(self, path, path_gen):
        """
        yield paths from path_gen, which can be a files_list_folder or a files_list_folder_continue,
        in a depth search manner.
        """
        for x in path_gen.entries:
            if _entry_is_file(x):
                yield x.path_display
            else:
                folder_path = _extend_path(path, x.name)
                yield from self._get_path_gen_from_path(path=folder_path)

        if path_gen.has_more:
            yield from self._get_path_gen_from_cursor(path_gen.cursor, path=path)

    def _get_path_gen_from_path(self, path):
        path_gen = self._con.files_list_folder(path=path, recursive=False, shared_link=self.shared_link)
        yield from self._yield_from_files_list_folder(path, path_gen)

    def _get_path_gen_from_cursor(self, cursor, path):
        path_gen = self._con.files_list_folder_continue(cursor)
        yield from self._yield_from_files_list_folder(path, path_gen)

    def __iter__(self):
        yield from self._get_path_gen_from_path(path='')
