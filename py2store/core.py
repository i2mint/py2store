import os

from py2store.key_mappers.paths import PrefixRelativizationMixin

file_sep = os.path.sep


def ensure_slash_suffix(path):
    if not path.endswith(file_sep):
        return path + file_sep
    else:
        return path


class PrefixRelativization(PrefixRelativizationMixin):
    """A key wrap that allows one to interface with absolute paths through relative paths.
    The original intent was for local files. Instead of referencing files through an absolute path such as
        /A/VERY/LONG/ROOT/FOLDER/the/file/we.want
    we can instead reference the file as
        the/file/we.want

    But PrefixRelativization can be used, not only for local paths, but when ever a string reference is involved.
    In fact, not only strings, but any key object that has a __len__, __add__, and subscripting.
    """

    def __init__(self, _prefix=""):
        self._prefix = _prefix

# class PathFormat:  # is now in py2store.persisters.local_files
