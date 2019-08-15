from py2store.base import Persister

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from dropbox import Dropbox
    from dropbox.files import DownloadError
    from dropbox.files import LookupError as DropboxLookupError
    from dropbox.exceptions import ApiError
    from dropbox.files import WriteMode


def _is_file_not_found_error(error_object):
    if isinstance(error_object, ApiError):
        if len(error_object.args) >= 2:
            err = error_object.args[1]
            if isinstance(err, DownloadError) and isinstance(err.get_path(), DropboxLookupError):
                return True
    return False


# TODO: Not tested significantly. Need to test with larger folders and bigger files.
# TODO: Lots of better exception handling to do.

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
        except ApiError as err:
            if _is_file_not_found_error(err):
                raise KeyError(f"Key doesn't exist: {k}")
            else:
                raise ValueError("Some unknown error happened (sorry, the lazy dev didn't tell me more than that).")
        if contents_response.status_code:
            return contents_response.content
        else:
            raise ValueError(
                "Response code wasn't 200 when trying to download a file (yet the file seems to exist).")

    def __setitem__(self, k, v):
        return self._con.files_upload(v, k, **self._files_upload_kwargs)

    def __delitem__(self, k):
        return self._con.files_delete_v2(k, self._rev)
