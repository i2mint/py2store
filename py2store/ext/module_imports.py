import os
from types import ModuleType
from functools import wraps
from importlib import import_module

try:
    from findimports import ModuleGraph
except ModuleNotFoundError:
    from ut.util.code.findimports import ModuleGraph
except ModuleNotFoundError:
    raise ModuleNotFoundError("You'll need the findimports module for that! Try `pip install findimports`")

from py2store import Collection, KvReader, lazyprop, wrap_kvs


class MyModuleGraph(ModuleGraph):
    def __init__(self, root,
                 trackUnusedNames=False,
                 all_unused=False,
                 external_dependencies=True,
                 warn_about_duplicates=False,
                 verbose=False):
        super().__init__()
        self._root = root
        if isinstance(root, str) and not os.path.exists(root):
            root = import_module(root)
        if isinstance(root, ModuleType):
            root = root.__file__
            if root.endswith('__init__.py'):
                root = os.path.dirname(root)
        assert isinstance(root, str) and os.path.exists(root)
        self._rootpath = root

        self.trackUnusedNames = trackUnusedNames
        self.all_unused = all_unused
        self.external_dependencies = external_dependencies
        self.warn_about_duplicates = warn_about_duplicates
        self.verbose = verbose

        self.parsePathname(self._rootpath)


class ModulesColl(Collection):
    @wraps(MyModuleGraph.__init__)
    def __init__(self, *args, **kwargs):
        self._source = MyModuleGraph(*args, **kwargs)

    @lazyprop
    def _modules(self):
        return {module: module.modname for module in self._source.listModules()}

    @lazyprop
    def _modobj_of_modname(self):
        return {modname: module for module, modname in self._modules.items()}

    def __len__(self):
        return len(self._modules)

    def __contains__(self, k):
        return k in self._modules

    def __iter__(self):
        for module in self._modules:
            yield module


class ModuleImportsBase(KvReader, ModulesColl):
    @staticmethod
    def _key_to_val(k):
        return k.imported_names

    def __getitem__(self, k):
        return self._key_to_val(k)


def modobj_to_modname(self, modobj):
    return self.store._modules[modobj]


def modname_to_modobj(self, modname):
    return self.store._modobj_of_modname[modname]


@wrap_kvs(name='ModuleImports', key_of_id=modobj_to_modname, id_of_key=modname_to_modobj, __module__=__name__)
class ModuleImports(ModuleImportsBase):
    @staticmethod
    def _key_to_val(k):
        return k.imports


# A few useful applications #####################################################################################

standard_lib_dir = os.path.dirname(os.__file__)


def standard_lib_names_gen(include_underscored=True):
    """
    Generates names of standard libs from python environment it was called from.

    :param include_underscored: Whether to include names that start with underscore or not.


    >>> standard_lib_names = set(standard_lib_names_gen(include_underscored=True))
    >>> # verify that a few known libs are there (including three folders and three py files)
    >>> assert {'collections', 'asyncio', 'os', 'dis', '__future__'}.issubset(standard_lib_names)
    >>> # verify that other decoys are not in there
    >>> assert {'__pycache__', 'LICENSE.txt', 'config-3.8-darwin', '.DS_Store'}.isdisjoint(standard_lib_names)
    """
    import os
    yield from {'itertools', 'sys'}  # exceptions that don't have a .py or package
    for filename in os.listdir(standard_lib_dir):
        if not include_underscored and filename.startswith('_'):
            continue
        if filename == 'site-packages':
            continue
        filepath = os.path.join(standard_lib_dir, filename)
        name, ext = os.path.splitext(filename)
        if filename.endswith('.py') and os.path.isfile(filepath):
            if str.isidentifier(name):
                yield name
        elif os.path.isdir(filepath) and '__init__.py' in os.listdir(filepath):
            yield name


standard_lib_names_gen.standard_lib_dir = standard_lib_dir

standard_lib_names = set(standard_lib_names_gen(include_underscored=True))

import builtins

builtin_names = set(dir(builtins))

python_names = builtin_names | standard_lib_names


def imports_for(root, post=set):
    """

    :param root:
    :param post: Postprocess iterable. For example:
        `set`, when order and repetition doesn't matter
        `collections.Counter`, to count number of modules where the module is imported,
        `lambda module: set(x.split('.')[0] for x in module)` if you only care about the top level package
    :return:

    >>> import wave
    >>> assert imports_for(wave) == {'warnings', 'builtins', 'sys', 'audioop', 'chunk', 'struct', 'collections'}
    """
    import itertools
    m = ModuleImports(root)
    imports_gen = itertools.chain.from_iterable(tuple(v) for v in m.values())
    if callable(post):
        return post(imports_gen)
    else:
        return imports_gen


from functools import partial
from collections import Counter

imports_for.set = partial(imports_for, post=set)
imports_for.counter = partial(imports_for, post=Counter)
imports_for.most_common = partial(imports_for, post=lambda x: Counter(x).most_common())
imports_for.first_level = partial(imports_for, post=lambda x: set(xx.split('.')[0] for xx in x))
imports_for.first_level_count = partial(imports_for, post=lambda x: Counter(xx.split('.')[0] for xx in x))
imports_for.third_party = partial(
    imports_for,
    post=lambda module: set(xx.split('.')[0] for xx in module if xx.split('.')[0] not in standard_lib_names))
