from dataclasses import dataclass
import os
from py2store.key_mappers.naming import StrTupleDict
from py2store.key_mappers.str_utils import is_manual_format_string

pjoin = os.path.join
sep = os.path.sep


@dataclass
class ParametrizedPath:

    def __init__(self, rootdir: str = '', subpath: str = '{subpath}',
                 format_dict=None, process_kwargs=None, process_info_dict=None):
        self.rootdir = rootdir
        assert is_manual_format_string(subpath), \
            "You need to use manual formatting (that is, name all your {} braces)"
        self.subpath = subpath
        self._keymap = StrTupleDict(
            self.rjoin(self.subpath),
            format_dict=format_dict, process_kwargs=process_kwargs, process_info_dict=process_info_dict)

    def rjoin(self, *p):
        return os.path.join(self.rootdir, *p)

    def to_tuple(self, path: str):
        return self._keymap.info_tuple(path)

    def from_tuple(self, t: tuple):
        return self._keymap.mk(*t)

    def to_dict(self, path: str):
        return self._keymap.info_dict(path)

    def from_dict(self, d: str):
        return self._keymap.mk(**d)


from py2store.mixins import GetBasedContainerMixin
from py2store.persisters.local_files import (
    LocalFileRWD, IterBasedSizedMixin, iter_filepaths_in_folder_recursively)


class Local(ParametrizedPath, LocalFileRWD, IterBasedSizedMixin, GetBasedContainerMixin):
    def __init__(self, rootdir, subpath='{subpath}', open_kwargs=None, **keymap_kws):
        ParametrizedPath.__init__(self, rootdir, subpath, **keymap_kws)
        open_kwargs = open_kwargs or {}
        LocalFileRWD.__init__(self, **open_kwargs)

    def __iter__(self):
        return iter_filepaths_in_folder_recursively(self.rootdir)
