from py2store.base import Persister
from ftplib import FTP, all_errors
import os.path
from io import BytesIO

from py2store.utils.uri_parsing import build_uri, parse_uri


def remote_mkdir(ftp, remote_directory):
    """
    Change to this directory, recursively making new folders if needed.
    returns: True if any folders were created.
    """
    if remote_directory == '/':
        # absolute path so change directory to root
        ftp.cwd('/')
        return False
    if remote_directory == '':
        # top-level relative directory must exist
        return False
    try:
        ftp.cwd(remote_directory)  # sub-directory exists
    except all_errors:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        remote_mkdir(ftp, dirname)  # make parent directories
        ftp.mkd(basename)  # sub-directory missing, so created it
        ftp.cwd(basename)
        return True

    return False


class FtpPersister(Persister):
    """
    A basic ftp persister.
    Keys must be names of files.

    >>> from py2store.persisters.ftp_persister import FtpPersister
    >>> s = FtpPersister()
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
    """

    def __init__(
            self,
            uri,
            collection='./py2store',
            encoding='utf8'
    ):
        uri_parsed = parse_uri(uri)

        self._ftp = FTP(
            host=uri_parsed['host'],
            user=uri_parsed['username'],
            passwd=uri_parsed['password'],
        )
        self._rootdir = collection
        self._encoding = encoding
        self._ftp.encoding = encoding
        remote_mkdir(self._ftp, self._rootdir)

    @classmethod
    def from_kwargs(cls, host, port=21, username='', password='', scheme='tcp', **kwargs):
        uri = build_uri(scheme, username=username, password=password, host=host, port=port)
        return cls(uri, **kwargs)

    def __getitem__(self, k):
        bio = BytesIO()
        self._ftp.retrbinary("RETR {}".format(k), bio.write)
        bio.seek(0)
        return bio.read().decode(self._encoding)

    def __setitem__(self, k, v):
        bio = BytesIO(bytearray(v, encoding=self._encoding))
        self._ftp.storbinary('STOR {}'.format(k), bio)

    def __delitem__(self, k):
        if len(k) > 0:
            try:
                self._ftp.delete(k)
            except all_errors:
                raise KeyError(f"You can't removed that key: {k}")
        else:
            raise KeyError(f"You can't removed that key: {k}")

    def __contains__(self, k):
        """
        Implementation of "k in self" check
        """
        try:
            files = self._ftp.nlst()
            if k in files:
                return True
        except all_errors:
            return False

        return False

    def __iter__(self):
        yield from [f for f in self._ftp.nlst() if f != '.' and f != '..']

    def __len__(self):
        files = self._ftp.nlst()
        return len(files) - 2

    def __del__(self):
        """
        Close ssh session when an object is deleted
        """
        self._ftp.close()
