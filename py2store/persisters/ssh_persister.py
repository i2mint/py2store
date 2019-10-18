import os.path
import stat

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import paramiko

from py2store.base import Persister


def remote_mkdir(sftp, remote_directory):
    """
    Change to this directory, recursively making new folders if needed.
    returns: True if any folders were created.
    """
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return False
    if remote_directory == '':
        # top-level relative directory must exist
        return False
    try:
        sftp.chdir(remote_directory)  # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        remote_mkdir(sftp, dirname)  # make parent directories
        sftp.mkdir(basename)  # sub-directory missing, so created it
        sftp.chdir(basename)
        return True

    return False


class SshPersister(Persister):
    """
    A basic ssh persister.
    Keys must be names of files.

    >>> from py2store.persisters.ssh_persister import SshPersister
    >>> s = SshPersister()
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
            uri,  # Example: dict(url='10.1.103.201', user='stud', password='stud')
            collection='./py2store',
            encoding='utf8',
    ):
        """
        :param uri: A dict of the following key-values:
            :param str hostname: the server to connect to, REQUIRED, others are optional
            :param int port: the server port to connect to
            :param str username:
                the username to authenticate as (defaults to the current local
                username)
            :param str password:
                Used for password authentication; is also used for private key
                decryption if ``passphrase`` is not given.
            :param str passphrase:
                Used for decrypting private keys.
            :param .PKey pkey: an optional private key to use for authentication
            :param str key_filename:
                the filename, or list of filenames, of optional private key(s)
                and/or certs to try for authentication
            :param float timeout:
                an optional timeout (in
        :param collection: root direction
        :param encoding:
        """
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh.connect(**uri)
        self._sftp = self._ssh.open_sftp()
        self._rootdir = collection
        self._encoding = encoding
        remote_mkdir(self._sftp, self._rootdir)

    def __getitem__(self, k):
        remote_file = self._sftp.file(k, mode='r')
        data = remote_file.read().decode(self._encoding)
        return data

    def __setitem__(self, k, v):
        remote_file = self._sftp.file(k, mode='w')
        remote_file.write(str(v).encode(self._encoding))

    def __delitem__(self, k):
        if len(k) > 0:
            try:
                self._sftp.remove(k)
            except IOError:
                raise KeyError(f"You can't removed that key: {k}")
        else:
            raise KeyError(f"You can't removed that key: {k}")

    def __contains__(self, k):
        """
        Implementation of "k in self" check
        """
        try:
            fileattr = self._sftp.lstat(k)
            if stat.S_ISREG(fileattr.st_mode):
                return True
        except Exception:
            return False

        return False

    def __iter__(self):
        files = self._sftp.listdir()
        yield from files

    def __len__(self):
        files = self._sftp.listdir()
        return len(files)

    def __del__(self):
        """
        Close ssh session when an object is deleted
        """
        self._ssh.close()
