"""The py2store wrapper to nltk.corpus.wordnet. Your no fuss gateway to (English) words.

The easiest way to get nltk.corpus.wordnet is

```
pip install nltk
```
in your terminal, and then in a python console:

```
>>> import nltk; nltk.download('wordnet')  # doctest: +SKIP
```

If you don't like that way, [see here](https://www.nltk.org/install.html) for other ways to get wordnet.

The central construct of this module is the Synset (a set of synonyms that share a common meaning).
To see a few things you can do with Synsets, naked, [see here](https://www.nltk.org/howto/wordnet.html).

Here we put a py2store wrapper around this stuff.

What is WordNet? https://wordnet.princeton.edu/

"""
import re

from i2.signatures import Sig

from py2store.mixins import ReadOnlyMixin
from py2store.util import ModuleNotFoundErrorNiceMessage
from py2store.sources import Attrs
from py2store import Store, KvReader, cached_keys, add_ipython_key_completions

with ModuleNotFoundErrorNiceMessage("""You don't seem to have nltk.corpus.wordnet. 
If you don't have nltk already, do ``pip install nltk``, and if it's that 
you don't have wordnet downloaded, do ``import nltk; nltk.download('wordnet');``
"""):
    from nltk.corpus import wordnet as wn
    from nltk.corpus.reader.wordnet import Synset, Lemma


def callable_attr_names(obj):
    """Set of attributes that are not callable"""
    return {name for name, a in Attrs(obj).items() if not callable(a.src)}


def fully_defaulted_method_names(obj):
    """Set of method names whose arguments all have defaults (so are callable without arguments)."""
    return {
        name for name, a in Attrs(obj).items()
        if callable(a.src) and len(Sig(a.src)) - len(Sig(a.src).defaults) == 1}


def keyable_attr_names(obj):
    """Set of attribute names of object that can be used as keys (because not callable, or callable without args)."""
    return callable_attr_names(obj) | fully_defaulted_method_names(obj)


# lemma_names_of_non_callable_attrs = callable_attr_names(Lemma)
# lemma_fully_defaulted_method_names = fully_defaulted_method_names(Lemma)
#
# synset_names_of_non_callable_attrs = callable_attr_names(Synset)
# synset_fully_defaulted_method_names = fully_defaulted_method_names(Synset)

# kv_synset_key_names = synset_names_of_non_callable_attrs | synset_fully_defaulted_method_names


def wordnet_element_store_base(element_cls, __module__=__name__):
    @add_ipython_key_completions
    @cached_keys(keys_cache=keyable_attr_names(element_cls), __module__=__module__)
    class _WordnetElementStore(Store):
        _from_name = None

        # def __new__(cls, *args, **kwargs):
        #     if len(args) > 0 and isinstance(args[0], str):
        #         return cls.from_name(args[0])
        #     else:
        #         return super().__new__(*args, **kwargs)

        @classmethod
        def from_name(cls, name):
            return cls(cls._from_name(name))

        def dict_of_non_empty_values(self):
            return {k: v for k, v in self.items() if not isinstance(v, list) or len(v) > 0}

        def __getitem__(self, k):
            attr = getattr(self, k)
            if callable(attr):
                attr = attr()
            return attr

        def __repr__(self):
            return f"{self.__class__.__name__}('{self._name}')"

    _WordnetElementStore._from_name = {Lemma: wn.lemma, Synset: wn.synset}.get(element_cls, None)

    return _WordnetElementStore


# Parsing method from nltk.corpus.reader.wordnet.Lemma's documentation.
# Documentation states "These methods all return lists of Lemmas"
lemma_methods_returning_lemmas = set(re.findall("\w+", """
    - antonyms
    - hypernyms, instance_hypernyms
    - hyponyms, instance_hyponyms
    - member_holonyms, substance_holonyms, part_holonyms
    - member_meronyms, substance_meronyms, part_meronyms
    - topic_domains, region_domains, usage_domains
    - attributes
    - derivationally_related_forms
    - entailments
    - causes
    - also_sees
    - verb_groups
    - similar_tos
    - pertainyms
"""))


class KvLemma(wordnet_element_store_base(Lemma)):
    """
    >>> lm = KvLemma.from_name('vocal.a.01.vocal')
    >>> assert len(lm) == len(dict(lm)) == 33
    >>> sorted(lm.dict_of_non_empty_values().items()) #doctest: +NORMALIZE_WHITESPACE
    [('antonyms', [KvLemma('instrumental.a.01.instrumental')]),
     ('count', 1),
     ('derivationally_related_forms', [KvLemma('vocalize.v.02.vocalize')]),
     ('key', 'vocal%3:01:02::'),
     ('lang', 'eng'),
     ('name', 'vocal'),
     ('pertainyms', [KvLemma('voice.n.02.voice')]),
     ('synset', KvSynset('vocal.a.01')),
     ('syntactic_marker', None)]
    """

    def __getitem__(self, k):
        attr = super().__getitem__(k)
        if k in lemma_methods_returning_lemmas:
            return list(map(KvLemma, attr))
        elif k == 'synset':
            return KvSynset(attr)
        else:
            return attr

    def __repr__(self):
        tup = type(self).__name__, self._synset._name, self._name
        return "%s('%s.%s')" % tup


# Parsing method from nltk.corpus.reader.wordnet.Synset's documentation.
# Documentation states "These methods all return lists of Synsets"
synset_methods_returning_synsets = set(re.findall("\w+", """
    - hypernyms, instance_hypernyms
    - hyponyms, instance_hyponyms
    - member_holonyms, substance_holonyms, part_holonyms
    - member_meronyms, substance_meronyms, part_meronyms
    - attributes
    - entailments
    - causes
    - also_sees
    - verb_groups
    - similar_tos
"""))

synset_methods_returning_list_of_lists_of_synsets = {'hypernym_paths', 'hyponym_paths'}


# @add_ipython_key_completions
# @cached_keys(keys_cache=keyable_attr_names(Synset), __module__=__name__)
class KvSynset(wordnet_element_store_base(Synset)):
    """A thin layer on top of nltk.corpus.reader.wordnet.Synset that will give us a dict-like interface of it.

    Think of "synset" as a "concept".
    For a list (or rather "dict") of these, checkout ``py2store.ext.wordnet.Synsets``

    >>> ss = KvSynset.from_name('sound.n.01')
    >>> ss
    KvSynset('sound.n.01')

    ``ss`` is a Mapping (meaning "dict-like")

    >>> from typing import Mapping
    >>> assert isinstance(ss, Mapping)

    So let's list it's keys:

    >>> print(*sorted(ss)) #doctest: +NORMALIZE_WHITESPACE
    also_sees attributes causes definition entailments examples frame_ids hypernym_distances hypernym_paths hypernyms
    hyponyms in_region_domains in_topic_domains in_usage_domains instance_hypernyms instance_hyponyms lemma_names
    lemmas lexname max_depth member_holonyms member_meronyms min_depth name offset part_holonyms part_meronyms pos
    region_domains root_hypernyms similar_tos substance_holonyms substance_meronyms topic_domains usage_domains
    verb_groups

    So lots of info about that concept.

    >>> ss['definition']
    'the particular auditory effect produced by a given cause'
    >>> ss['examples']
    ['the sound of rain on the roof', 'the beautiful sound of music']
    >>> ss['lemma_names']  # a.k.a. "words used for that concept"
    ['sound']


    Retrieve everything at once:

    >>> d = dict(ss)
    >>> len(d.keys() & {'definition', 'also_sees', 'hypernyms'})
    3

    Display items for non-empty values
    >>> for k, v in sorted(ss.items()): # doctest: +SKIP
    ...     if v:
    ...         print(f"{k}: {v}")
    definition: the particular auditory effect produced by a given cause
    examples: ['the sound of rain on the roof', 'the beautiful sound of music']
    hypernym_distances: {(KvSynset('attribute.n.02'), 3), (KvSynset('sound_property.n.01'), 1),
    ...     (KvSynset('property.n.02'), 2), (KvSynset('entity.n.01'), 5), (KvSynset('sound.n.01'), 0),
    ...     (KvSynset('abstraction.n.06'), 4)}
    hypernym_paths: [[KvSynset('entity.n.01'), KvSynset('abstraction.n.06'), KvSynset('attribute.n.02'),
    ...     KvSynset('property.n.02'), KvSynset('sound_property.n.01'), KvSynset('sound.n.01')]]
    hypernyms: [KvSynset('sound_property.n.01')]
    hyponyms: [KvSynset('noisiness.n.01'), KvSynset('ring.n.01'), KvSynset('unison.n.03'), KvSynset('voice.n.01')]
    lemma_names: ['sound']
    lemmas: [KvLemma('sound.n.01.sound')]
    lexname: noun.attribute
    max_depth: 5
    min_depth: 5
    name: sound.n.01
    offset: 4981139
    pos: n
    root_hypernyms: [Synset('entity.n.01')]
    """

    def __getitem__(self, k):
        attr = super().__getitem__(k)
        if k in synset_methods_returning_synsets:
            return list(map(KvSynset, attr))
        elif k in synset_methods_returning_list_of_lists_of_synsets:
            return [list(map(KvSynset, x)) for x in attr]
        elif k == 'hypernym_distances':
            return {(KvSynset(ss), dist) for ss, dist in attr}
        elif k == 'lemmas':
            return [KvLemma(lemma) for lemma in attr]
        else:
            return attr


@add_ipython_key_completions
class Synsets(ReadOnlyMixin, Store):
    """
    >>> s = Synsets()
    >>> len(s)
    117659
    >>> list(s)[:5]
    ['able.a.01', 'unable.a.01', 'abaxial.a.01', 'adaxial.a.01', 'acroscopic.a.01']
    >>> ss = s['sound.n.01']
    >>> ss
    KvSynset('sound.n.01')

    And what can you do with a KvSynset?
    Well, you'll just have to check out it's documentation!

    """

    def __init__(self, pos=None):
        super().__init__(store={ss.name(): ss for ss in wn.all_synsets(pos=pos)})

    def __getitem__(self, k):
        return KvSynset(self.store[k])

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@cached_keys(keys_cache=set)
class Lemmas(KvReader):
    def __iter__(self):
        return wn.all_lemma_names()

    def __getitem__(self, k):
        return {ss.name(): KvSynset(ss) for ss in wn.synsets(k)}


import numpy as np
import io
import pandas as pd
import itertools
from collections import Counter


def print_word_definitions(word):
    print(word_definitions_string(word))


def word_definitions_string(word):
    return '\n'.join(['%d: %s (%s)'
                      % (i, x.definition(), x.name()) for i, x in enumerate(wn.synsets(word))])


def print_word_lemmas(word):
    t = Counter([l.name for s in wn.synsets(word) for l in s.lemmas])
    print(pd.Series(index=list(t.keys()), data=list(t.values())).sort(inplace=False, ascending=False))


def _lemma_names_str(syn):
    return '(' + ', '.join(syn.lemma_names) + ')'


def print_hypos_with_synset(syn, tab=''):
    print(tab + syn.name)
    h = syn.hyponyms()
    if len(h) > 0:
        for hi in h:
            print_hypos_with_synset(hi, tab + '  ')
    else:
        print(tab + '  ' + _lemma_names_str(syn))


def pprint_hypos(syn, tab=''):
    print(tab + _lemma_names_str(syn))
    h = syn.hyponyms()
    if len(h) > 0:
        for hi in h:
            pprint_hypos(hi, tab + '  ')


class iTree(object):
    def __init__(self, value=None):
        self.value = value
        self.children = []
        self.default_node_2_str = lambda node: str(node.value)

    def __iter__(self):
        for v in itertools.chain(*map(iter, self.children)):
            yield v
        yield self

    def tree_info_str(self,
                      node_2_str=None,  # default info is node value
                      tab_str=2 * ' ',  # tab string
                      depth=0
                      ):
        node_2_str = node_2_str or self.default_node_2_str
        s = depth * tab_str + node_2_str(self) + '\n'
        new_depth = depth + 1
        for child in self.children:
            s += child.tree_info_str(node_2_str, tab_str, new_depth)
        return s


class HyponymTree(iTree):
    def __init__(self, value=None):
        if isinstance(value, str):
            value = wn.synset(value)
        super(HyponymTree, self).__init__(value=value)
        for hypo in value.hyponyms():
            self.children.append(HyponymTree(hypo))
        self.set_default_node_2_str('name')

    def __str__(self):
        return self.value.name()

    def __repr__(self):
        return self.value.name()

    def print_lemmas(self, tab=''):
        print(tab + _lemma_names_str(self.value))
        for c in self.children:
            pprint_hypos(c, tab + '  ')

    def leafs(self):
        return [x for x in self]

    @classmethod
    def of_hyponyms(cls, syn):
        tree = cls(syn)
        for hypo in syn.hyponyms():
            tree.children.append(cls.of_hyponyms(hypo))
        return tree

    @staticmethod
    def get_node_2_str_function(method='name', **kwargs):
        """
        returns a node_2_str function (given it's name)
        method could be
            * 'name': The synset name (example sound.n.01)
            * 'lemma_names': A parenthesized list of lemma names
            * 'name_and_def': The synset name and it's definition
            * 'lemmas_and_def': The lemma names and definition
        """
        if method == 'name':
            return lambda node: \
                node.value.name
        elif method == 'lemma_names' or method == 'lemmas':
            lemma_sep = kwargs.get('lemma_sep', ', ')
            return lambda node: \
                '(' + lemma_sep.join(node.value.lemma_names) + ')'
        elif method == 'name_and_def':
            return lambda node: \
                node.value.name + ': ' + node.value.definition
        elif method == 'lemmas_and_def':
            lemma_sep = kwargs.get('lemma_sep', ', ')
            def_sep = kwargs.get('def_sep', ': ')
            return lambda node: \
                '(' + lemma_sep.join(node.value.lemma_names) + ')' \
                + def_sep + node.value.definition
        elif method == 'all':
            lemma_sep = kwargs.get('lemma_sep', ', ')
            def_sep = kwargs.get('def_sep', ': ')
            return lambda node: \
                '(' + lemma_sep.join(node.value.lemma_names) + ')' \
                + def_sep + node.value.name \
                + def_sep + node.value.definition
        else:
            raise ValueError("Unknown node_2_str_function method")

    def set_default_node_2_str(self, method='name'):
        """
        will set the default string representation of a synset
        (used as a default ny the tree_info_str function for example)
        from the name of the method to use
        (see get_node_2_str_function(method))
        method could be
            * 'name': The synset name (example sound.n.01)
            * 'lemma_names': A parenthesized list of lemma names
            * 'name_and_def': The synset name and it's definition
            * 'lemmas_and_def': The lemma names and definition
        """
        self.default_node_2_str = HyponymTree.get_node_2_str_function(method)

    def _df_for_excel_export(self, method='all', method_args={}):
        method_args['def_sep'] = ':'
        method_args['tab_str'] = method_args.get('tab_str', '* ')
        s = ''
        # s = 'lemmas' + method_args['def_sep'] + 'synset' + method_args['def_sep'] + 'definition' + '\n'
        s += self.tree_info_str(node_2_str=self.get_node_2_str_function(method=method),
                                tab_str=method_args['tab_str'])
        return pd.DataFrame.from_csv(io.StringIO(str(s)),
                                     sep=method_args['def_sep'], header=None, index_col=None)

    def export_info_to_excel(self, filepath, sheet_name='hyponyms', method='all', method_args={}):
        d = self._df_for_excel_export(method=method, method_args=method_args)
        d.to_excel(filepath, sheet_name=sheet_name, header=False, index=False)


class HyponymForest(object):
    def __init__(self, tree_list):
        assert len(tree_list) == len(set(tree_list)), "synsets in list must be unique"
        for i, ss in enumerate(tree_list):
            if not isinstance(ss, HyponymTree):
                tree_list[i] = HyponymTree(ss)
        self.tree_list = tree_list

    def leafs(self):
        return {xx for x in self.tree_list for xx in x.leafs()}

    def export_info_to_excel(self, filepath, sheet_name='hyponyms', method='all', method_args={}):
        d = pd.DataFrame()
        for dd in self.tree_list:
            d = pd.concat([d, dd._df_for_excel_export(method=method, method_args=method_args)])
        d.to_excel(filepath, sheet_name=sheet_name, header=False, index=False)
