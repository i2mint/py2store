from py2store.util import ModuleNotFoundErrorNiceMessage
from py2store.stores.local_store import LocalBinaryStore

from io import BytesIO
import os
import pickle

with ModuleNotFoundErrorNiceMessage():
    import pandas as pd


def df_from_data_given_ext(data, ext, **kwargs):
    if ext.startswith('.'):
        ext = ext[1:]
    if ext in {'xls', 'xlsx'}:
        kwargs = dict({'index': False}, **kwargs)
        return pd.read_excel(data, **kwargs)
    elif ext in {'csv'}:
        kwargs = dict({'index_col': False}, **kwargs)
        return pd.read_csv(data, **kwargs)
    elif ext in {'tsv'}:
        kwargs = dict({'sep': '\t', 'index_col': False}, **kwargs)
        return pd.read_csv(data, **kwargs)
    elif ext in {'json'}:
        kwargs = dict({'orient': 'records'}, **kwargs)
        return pd.read_json(data, **kwargs)
    elif ext in {'html'}:
        kwargs = dict({'index_col': False}, **kwargs)
        return pd.read_html(data, **kwargs)[0]
    elif ext in {'p', 'pickle'}:
        return pickle.load(data, **kwargs)
    else:
        raise ValueError(f"Don't know how to handle extension: {ext}")


# TODO: Make the logic independent from local files assumption.
# TODO: Better separate Reader, and add DfStore to make a writer.

class DfReader(LocalBinaryStore):

    def __init__(self, path_format, ext_specs=None):
        super().__init__(path_format)
        if ext_specs is None:
            ext_specs = {}
        self.ext_specs = ext_specs

    def __getitem__(self, k):
        _, ext = os.path.splitext(k)
        if ext.startswith('.'):
            ext = ext[1:]
        kwargs = self.ext_specs.get(ext, {})
        data = BytesIO(super().__getitem__(k))
        return df_from_data_given_ext(data, ext, **kwargs)

    def __setitem__(self, k, v):
        raise NotImplementedError("This is a reader: No write operation allowed")

    def __delitem__(self, k):
        raise NotImplementedError("This is a reader: No delete operation allowed")
