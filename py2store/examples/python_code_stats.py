"""
Get stats about packages. Your own, or other's.
Things like...

>>> import collections
>>> modules_info_df(collections)
                      lines  empty_lines  ...  num_of_functions  num_of_classes
collections.__init__   1273          189  ...                 1               9
collections.abc           3            1  ...                 0              25
<BLANKLINE>
[2 rows x 7 columns]
>>> modules_info_df_stats(collections.abc)
lines                      1276.000000
empty_lines                 190.000000
comment_lines                73.000000
docs_lines                  133.000000
function_lines              138.000000
num_of_functions              1.000000
num_of_classes               34.000000
empty_lines_ratio             0.148903
comment_lines_ratio           0.057210
function_lines_ratio          0.108150
mean_lines_per_function     138.000000
dtype: float64
>>> stats_of(['urllib', 'json', 'collections'])
                              urllib         json  collections
empty_lines_ratio           0.157034     0.136818     0.148903
comment_lines_ratio         0.074142     0.038432     0.057210
function_lines_ratio        0.213907     0.449654     0.108150
mean_lines_per_function    13.463768    41.785714   138.000000
lines                    4343.000000  1301.000000  1276.000000
empty_lines               682.000000   178.000000   190.000000
comment_lines             322.000000    50.000000    73.000000
docs_lines                425.000000   218.000000   133.000000
function_lines            929.000000   585.000000   138.000000
num_of_functions           69.000000    14.000000     1.000000
num_of_classes             55.000000     3.000000    34.000000
"""
import re
import os
from py2store import filt_iter
from py2store.sources import Attrs
from py2store.filesys import FileStringReader
from types import FunctionType, ModuleType
from inspect import getsource

psep = os.path.sep

DFLT_ON_ERROR = "ignore"  # could be 'print', 'ignore', or 'raise'

empty_line = re.compile("^\s*$")
comment_line_p = re.compile("^\s+#.+$")
line_p = re.compile("\n|\r|\n\r|\r\n")
only_py_ext = lambda path: path.endswith(".py")
no_test_folder = lambda path: "test" not in path.split(psep)


def lines(string):
    return line_p.split(string)


def _num_lines_of_function_code(obj: FunctionType):
    assert isinstance(obj, FunctionType)
    return len(getsource(obj).split("\n")) - len(
        (obj.__doc__ or "").split("\n")
    )


def _root_dir_and_name(root):
    """
    The parent path and leaf name for the given root
    :param root: module instance, dot path, or directory path
    :return:
    """
    if isinstance(root, str) and not os.path.dirname(root):
        root = __import__(
            root
        )  # assume it's a dot path string of a module and try to import it
    if isinstance(root, ModuleType):
        root = os.path.dirname(root.__file__)
    if root.endswith(psep):
        root = root[:-1]
    return os.path.dirname(root), os.path.basename(root)


# TODO: Must be a standard lib for this!
def _path_to_module_str(path, root_path):
    """
    The dot-path module string for a path (given the root_path, assumed to be on the python path)
    :param path: The path to the module.
    :param root_path: The path that's assumed to be on the python path
    :return:
    """
    assert path.endswith(".py")
    path = path[:-3]

    if root_path.endswith(psep):
        root_path = root_path[:-1]
    root_path, root_package = _root_dir_and_name(root_path)
    len_root = len(root_path) + 1
    path_parts = path[len_root:].split(psep)
    if path_parts[-1] == "__init__.py":
        path_parts = path_parts[:-1]
    return ".".join(path_parts)


def get_objs(root, k):
    name = _path_to_module_str(k, root)
    module_store = Attrs.module_from_path(
        k, key_filt=lambda x: not x.startswith("__"), name=name
    )

    def obj_filt(
            obj,
    ):  # to make sure we only analyze objects defined in module itself, not imported
        obj_module = getattr(obj, "__module__", None)
        if obj_module:
            return obj_module == name

    objs = list(
        filter(obj_filt, (vv._source for vv in module_store.values()))
    )
    return objs


def modules_info_gen(root, filepath_filt=only_py_ext, on_error=DFLT_ON_ERROR):
    """
    Yields statistics (as dicts) of modules under the root module or directory of a python package.

    :param root: module instance, dot path, or directory path
    :param filepath_filt: filepath filter function or regular expression
    :param on_error: What to do when an error occurs when extracting information from a module.
        Values are 'ignore', 'print', 'raise', or 'yield'
    :return: A generator of dicts
    """
    """Gives us statistics given the root module or directory of a python package"""
    if isinstance(filepath_filt, str):
        filt_pattern = re.compile(filepath_filt)
        filepath_filt = filt_pattern.match

    parent_dir, dirname = _root_dir_and_name(root)
    root = os.path.join(parent_dir, dirname)

    @filt_iter(filepath_filt)
    class PyCodeReader(FileStringReader):
        pass

    pycode = PyCodeReader(root)

    for filepath, code_str in pycode.items():
        try:
            name = _path_to_module_str(filepath, root)
            module_store = Attrs.module_from_path(
                filepath, key_filt=lambda x: not x.startswith("__"), name=name
            )

            def obj_filt(
                    obj,
            ):  # to make sure we only analyze objects defined in module itself, not imported
                obj_module = getattr(obj, "__module__", None)
                if obj_module:
                    return obj_module == name

            objs = list(
                filter(obj_filt, (vv._source for vv in module_store.values()))
            )
            yield method_name(code_str, filepath, objs)
        except Exception as e:
            if on_error == "print":
                print(f"Problem with {filepath}: {str(e)[:50]}\n")
            elif on_error == "ignore":
                pass
            elif on_error == "yield":
                yield {"filepath": filepath, "error": e}
            else:
                raise


def method_name(code_str, filepath, objs):
    return {
        "filepath": filepath,
        "lines": len(lines(code_str)),
        "empty_lines": sum(
            bool(empty_line.match(line)) for line in lines(code_str)
        ),
        "comment_lines": sum(
            bool(comment_line_p.match(line))
            for line in lines(code_str)
        ),
        "docs_lines": sum(
            len(lines(obj.__doc__ or "")) for obj in objs
        ),
        "function_lines": sum(
            _num_lines_of_function_code(obj)
            for obj in objs
            if isinstance(obj, FunctionType)
        ),
        "num_of_functions": sum(
            isinstance(obj, FunctionType) for obj in objs
        ),
        "num_of_classes": sum(isinstance(obj, type) for obj in objs),
    }


def modules_info_df(
        root, filepath_filt=only_py_ext, index_field=None, on_error=DFLT_ON_ERROR
):
    """
    A pandas DataFrame of stats of the root (package or directory thereof).
    :param root: module or directory path
    :param filepath_filt: filepath filter function or regular expression
    :param index_field: function or field string that should be used for the indexing of modules
    :param on_error: What to do when an error occurs when extracting information from a module.
        Values are 'ignore', 'print', or 'raise'
    :return: A DataFrame whose rows contain information for each module

    >>> import urllib
    >>> modules_info_df(urllib)
                        lines  empty_lines  ...  num_of_functions  num_of_classes
    urllib.error           78           18  ...                 0               3
    urllib.request       2743          404  ...                23              28
    urllib.__init__         1            1  ...                 0               0
    urllib.response        81           24  ...                 0               4
    urllib.robotparser    274           36  ...                 0               4
    urllib.parse         1166          199  ...                46              16
    <BLANKLINE>
    [6 rows x 7 columns]
    """

    import pandas as pd

    d = list(modules_info_gen(root, filepath_filt, on_error=on_error))

    if index_field is None:
        dirpath, dirname = _root_dir_and_name(root)
        root = os.path.join(dirpath, dirname)
        index_field = lambda x: _path_to_module_str(x.pop("filepath"), root)

    if isinstance(index_field, str):
        return pd.DataFrame(d).set_index(index_field)
    elif callable(index_field):
        index = [index_field(x) for x in d]
        return pd.DataFrame(index=index, data=d)


def modules_info_df_stats(
        root, filepath_filt=only_py_ext, index_field=None, on_error=DFLT_ON_ERROR
):
    """
    A pandas Series of statistics over all modules of some root (package or directory thereof).
    :param root: module or directory path
    :param filepath_filt: filepath filter function or regular expression
    :param index_field: function or field string that should be used for the indexing of modules
    :param on_error: What to do when an error occurs when extracting information from a module.
        Values are 'ignore', 'print', or 'raise'
    :return: A Series whose rows containing statistics

    >>> import json
    >>> modules_info_df_stats(json)
    lines                      1301.000000
    empty_lines                 178.000000
    comment_lines                50.000000
    docs_lines                  218.000000
    function_lines              585.000000
    num_of_functions             14.000000
    num_of_classes                3.000000
    empty_lines_ratio             0.136818
    comment_lines_ratio           0.038432
    function_lines_ratio          0.449654
    mean_lines_per_function      41.785714
    dtype: float64
    >>> modules_info_df_stats('collections.abc')
    lines                      1276.000000
    empty_lines                 190.000000
    comment_lines                73.000000
    docs_lines                  133.000000
    function_lines              138.000000
    num_of_functions              1.000000
    num_of_classes               34.000000
    empty_lines_ratio             0.148903
    comment_lines_ratio           0.057210
    function_lines_ratio          0.108150
    mean_lines_per_function     138.000000
    dtype: float64
    """
    df = modules_info_df(root, filepath_filt, index_field, on_error=on_error)
    df = df.sum()
    cols = set(df.index.values)
    for col in ["empty_lines", "comment_lines", "doc_lines", "function_lines"]:
        if {col, "lines"}.issubset(cols):
            df[f"{col}_ratio"] = df[col] / df["lines"]
    if {"num_of_functions", "function_lines"}.issubset(cols):
        df["mean_lines_per_function"] = (
                df["function_lines"] / df["num_of_functions"]
        )

    return df


def stats_of(
        modules,
        filepath_filt=only_py_ext,
        index_field=None,
        on_error=DFLT_ON_ERROR,
):
    """
    A dataframe of stats of the input modules.

    :param modules: list of importable names
    :param root: module or directory path
    :param filepath_filt: filepath filter function or regular expression
    :param index_field: function or field string that should be used for the indexing of modules
    :param on_error: What to do when an error occurs when extracting information from a module.
        Values are 'ignore', 'print', or 'raise'
    :return:

    >>> stats_of(['urllib', 'json', 'collections'])
                                  urllib         json  collections
    empty_lines_ratio           0.157034     0.136818     0.148903
    comment_lines_ratio         0.074142     0.038432     0.057210
    function_lines_ratio        0.213907     0.449654     0.108150
    mean_lines_per_function    13.463768    41.785714   138.000000
    lines                    4343.000000  1301.000000  1276.000000
    empty_lines               682.000000   178.000000   190.000000
    comment_lines             322.000000    50.000000    73.000000
    docs_lines                425.000000   218.000000   133.000000
    function_lines            929.000000   585.000000   138.000000
    num_of_functions           69.000000    14.000000     1.000000
    num_of_classes             55.000000     3.000000    34.000000
    """
    import pandas as pd

    if isinstance(modules, str):
        modules = [modules]
    df = pd.concat([modules_info_df_stats(x) for x in modules], axis=1)
    df.columns = modules
    put_at_the_end = [
        x for x in df.index if x.endswith("lines") or x.startswith("num")
    ]
    put_at_the_front = [x for x in df.index if x not in put_at_the_end]
    df = df.loc[put_at_the_front + put_at_the_end]
    return df


import collections

if __name__ == "__main__":
    from py2store.util import ModuleNotFoundErrorNiceMessage

    with ModuleNotFoundErrorNiceMessage():
        import argh

        argh.dispatch_commands(
            [modules_info_df, modules_info_df_stats, stats_of]
        )
