from collections.abc import MutableMapping
from paramiko import *
import os.path
import stat


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
        sftp.chdir(remote_directory) # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        remote_mkdir(sftp, dirname) # make parent directories
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True

    return False



class SshPersister(MutableMapping):
    """
    A basic ssh persister.
    Keys must be names of files.

    >>> from py2store.persisters._ssh_in_progress import SshPersister
    >>> s = SshPersister()
    >>> k = 'foo'
    >>> v = 'bar'
    >>> for _key in s:
    ...     del s[_key]
    >>> len(s)
    0
    >>> s[k] = v
    >>> s[k]
    b'bar'
    >>> s.get(k)
    b'bar'
    >>> len(s)
    1
    >>> list(s.values())
    [b'bar']
    >>> k in s
    True
    >>> del s[k]
    >>> k in s
    False
    >>> len(s)
    0
    """

    def clear(self):
        raise NotImplementedError(
            "clear is disabled by default, for your own protection! "
            "Loop and delete if you really want to."
        )

    def __init__(self,
                 user='stud',
                 password='stud',
                 url='10.1.103.201',
                 rootdir='./py2store',

    ):
        self._ssh = SSHClient()
        self._ssh.set_missing_host_key_policy(AutoAddPolicy())
        self._ssh.connect(url, username=user, password=password)
        self._sftp = self._ssh.open_sftp()
        self._rootdir = rootdir
        remote_mkdir(self._sftp, self._rootdir)


    def __getitem__(self, k):
        remote_file = self._sftp.file(k, mode='r')
        data = remote_file.read()
        return data

    def __setitem__(self, k, v):
        remote_file = self._sftp.file(k, mode='w')
        remote_file.write(v)

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
