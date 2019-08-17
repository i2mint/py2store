from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from pydrive.auth import GoogleAuth
    from pydrive.drive import GoogleDrive

from py2store.base import Persister


class GoogleDrivePersister(Persister):
    '''
    A basic Google Drive persister implemented with the pydrive library.
    Keys must be names of files.

    **** Authentication ***
    Drive API requires OAuth2.0 for authentication.
    1. Go to APIs Console and make your own project.
    2. Search for ‘Google Drive API’, select the entry, and click ‘Enable’.
    3. Select ‘Credentials’ from the left menu, click ‘Create Credentials’, select ‘OAuth client ID’.
    4. Now, the product name and consent screen need to be set -> click ‘Configure consent screen’ and follow the instructions.
       Once finished:
        - Select ‘Application type’ to be Web application.
        - Enter an appropriate name.
        - Input http://localhost:8080 for ‘Authorized JavaScript origins’.
        - Input http://localhost:8080/ for ‘Authorized redirect URIs’.
        - Click ‘Save’.
    5. Click ‘Download JSON’ on the right side of Client ID to download client_secret_<really long ID>.json.
    see: https://pythonhosted.org/PyDrive/quickstart.html for details.
    6. Rename the file to “client_secrets.json” and place it in your working directory.

    >>> from py2store.persisters.googledrive_w_pydrive import GoogleDrivePersister
    >>> s = GoogleDrivePersister()
    >>> k = 'foo'
    >>> v = 'bar'
    >>> for _key in s:
    ...     del s[_key]
    >>> len(s)
    0
    >>> s[k] = v
    >>> s[k]
    'bar'
    >>> s.get(k)
    'bar'
    >>> len(s)
    1
    >>> list(s.values())
    ['bar']
    >>> k in s
    True
    >>> del s[k]
    >>> k in s
    False
    >>> len(s)
    0
    '''

    def __init__(
            self,
            rootdir='py2store'
    ):
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication
        self._drive = GoogleDrive(gauth)
        files = self.fetch_files('root')
        for f in files:
            if f['title'] == rootdir:
                self._rootdir_id = f['id']
                print('found')

        if self._rootdir_id is None:
            folder = self._drive.CreateFile({'title': rootdir, 'mimeType': 'application/vnd.google-apps.folder'})
            folder.Upload()
            self._rootdir_id = folder['id']

    def __getitem__(self, k):
        files = self.fetch_files(self._rootdir_id)
        for f in files:
            if f['title'] == k:
                return f.GetContentString()

        raise KeyError(f"You can't access that key: {k}")

    def __setitem__(self, k, v):
        f = self._drive.CreateFile({"title": k, "parents": [{"kind": "drive#fileLink", "id": self._rootdir_id}]})
        f.SetContentString(str(v))
        f.Upload()

    def __delitem__(self, k):
        if len(k) > 0:
            try:
                files = self.fetch_files(self._rootdir_id)
                for f in files:
                    if f['title'] == k:
                        f.Delete()
            except Exception:
                raise KeyError(f"You can't removed that key: {k}")
        else:
            raise KeyError(f"You can't removed that key: {k}")

    def __contains__(self, k):
        """
        Implementation of "k in self" check
        """
        try:
            files = self.fetch_files(self._rootdir_id)
            for f in files:
                if f['title'] == k:
                    return True
        except Exception:
            return False

        return False

    def __iter__(self):
        files = self.fetch_files(self._rootdir_id)
        yield from [f['title'] for f in files]

    def __len__(self):
        files = self.fetch_files(self._rootdir_id)
        return len(files)

    def fetch_files(self, id):
        return self._drive.ListFile({'q': "'{}' in parents and trashed=false".format(id)}).GetList()
