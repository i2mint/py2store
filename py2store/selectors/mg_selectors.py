""" Selectors that use the mongo-query interface """

from typing import Iterator

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import pandas as pd  # only used for pd.isnull (other option?)

from py2store.selectors.mongoquery import Query


def _print_docs(docs):
    for doc in iter(docs):
        print(doc)


class Selection:
    def __iter__(self) -> Iterator:
        raise NotImplementedError("Needs to be implemented by a concrete class")

    def __len__(self):
        count = 0
        for _ in self.__iter__():
            count += 1
        return count


class Selector(Selection):
    def select(self, selector) -> Selection:
        raise NotImplementedError("Need to implement in concrete class")


class FiltSelector(Selector):
    def __init__(self, _docs, _filt=None):
        self._docs = _docs
        self._filt = _filt

    def _filt_conjunction(self, filt: callable):
        if self._filt is None:
            return filt
        else:
            return lambda x: self._filt(x) and filt(x)

    def __iter__(self):
        return filter(self._filt, self._docs.__iter__())

    def select(self, filt: callable) -> Selection:
        return self.__class__(_docs=self._docs, _filt=self._filt_conjunction(filt))


class MgDfSelector(Selector):
    """
    >>> _docs = [
    ...  {'bt': 0, 'tt': 5, 'tag': 'small'},
    ...  {'bt': 10, 'tt': 15, 'tag': 'small'},
    ...  {'bt': 20, 'tt': 25, 'tag': 'small'},
    ...  {'bt': 30, 'tt': 35, 'tag': 'big'},
    ...  {'bt': 40, 'tt': 45, 'tag': 'big'},
    ...  {'bt': 50, 'tt': 55, 'tag': 'big'}]
    >>> df_selector = MgDfSelector(_docs)
    >>> len(df_selector)
    6
    >>> jdict = df_selector.to_jdict()
    >>> import json
    >>> json_str = json.dumps(jdict)
    >>> df_selector_2 = MgDfSelector(json.loads(json_str))
    >>> len(df_selector_2)
    6
    >>> next(iter(df_selector))
    {'bt': 0, 'tag': 'small', 'tt': 5}
    >>> next(iter(df_selector_2))
    {'bt': 0, 'tag': 'small', 'tt': 5}
    """
    def __init__(self, _df):
        if isinstance(_df, list) and isinstance(_df[0], dict):
            _df = pd.DataFrame(_df)
        self._df = _df

    def __iter__(self):
        return ({k: v for k, v in d.items() if not pd.isnull(v)} for r, d in self._df.iterrows())

    def __len__(self):
        return len(self._df)

    def __contains__(self, item):
        item = {k: v for k, v in item.items() if not pd.isnull(v)}
        for existing_item in self:
            if existing_item == item:
                return True
        return False

    def select(self, selector) -> Selector:
        """

        :param selector: A mongo-like query of the underlying dataframe
        :return:
        >>> _docs = [
        ...  {'bt': 0, 'tt': 5, 'tag': 'small'},
        ...  {'bt': 10, 'tt': 15, 'tag': 'small'},
        ...  {'bt': 20, 'tt': 25, 'tag': 'small'},
        ...  {'bt': 30, 'tt': 35, 'tag': 'big'},
        ...  {'bt': 40, 'tt': 45, 'tag': 'big'},
        ...  {'bt': 50, 'tt': 55, 'tag': 'big'}]
        >>> import pandas as pd
        >>> selector = MgDfSelector(_df=pd.DataFrame(_docs))
        >>> len(selector)
        6
        >>> selection = selector.select({"tag": {"$eq": 'small'}})
        >>> len(selection)
        3
        >>> _print_docs(selection)
        {'bt': 0, 'tag': 'small', 'tt': 5}
        {'bt': 10, 'tag': 'small', 'tt': 15}
        {'bt': 20, 'tag': 'small', 'tt': 25}
        >>> selection = selector.select({'bt': {"$gte": 20}, 'tt': {"$lt": 45}})
        >>> _print_docs(selection)
        {'bt': 20, 'tag': 'small', 'tt': 25}
        {'bt': 30, 'tag': 'big', 'tt': 35}
        """
        selector_file_func = Query(selector).match
        lidx = list(map(selector_file_func, self._df.to_dict(orient='rows')))
        return self.__class__(self._df[lidx])
        # Below are just ideas towards a more general (source, selector, selection) framework
        # selection = self.__class__(self._df[lidx])
        # selection._selector = selector
        # return selection

    def to_jdict(self):
        return list(self.__iter__())

    @classmethod
    def from_jdict(cls, jdict):
        return cls(_df=pd.DataFrame(jdict))


########################################################################################################################
# Other versions of MgDfSelector that are more amenable to generalization...

class MgDfSelector2(Selector):
    """

    :param selector: A mongo-like query of the underlying dataframe
    :return:
    >>> _docs = [
    ...  {'bt': 0, 'tt': 5, 'tag': 'small'},
    ...  {'bt': 10, 'tt': 15, 'tag': 'small'},
    ...  {'bt': 20, 'tt': 25, 'tag': 'small'},
    ...  {'bt': 30, 'tt': 35, 'tag': 'big'},
    ...  {'bt': 40, 'tt': 45, 'tag': 'big'},
    ...  {'bt': 50, 'tt': 55, 'tag': 'big'}]
    >>> import pandas as pd
    >>> selector = MgDfSelector2(pd.DataFrame(_docs))
    >>> len(selector)
    6
    >>> selection = selector.select({"tag": {"$eq": 'small'}})
    >>> len(selection)
    3
    >>> _print_docs(selection)
    {'bt': 0, 'tag': 'small', 'tt': 5}
    {'bt': 10, 'tag': 'small', 'tt': 15}
    {'bt': 20, 'tag': 'small', 'tt': 25}
    >>> selection = selector.select({'bt': {"$gte": 20}, 'tt': {"$lt": 45}})
    >>> _print_docs(selection)
    {'bt': 20, 'tag': 'small', 'tt': 25}
    {'bt': 30, 'tag': 'big', 'tt': 35}
    """

    def __init__(self, _docs, _filt=None):
        self._docs = _docs

    def __iter__(self):
        return (d.to_dict() for r, d in self._docs.iterrows())

    def __len__(self):
        return len(self._docs)

    def select(self, selector) -> Selector:
        selector_file_func = Query(selector).match
        lidx = list(map(selector_file_func, self._docs.to_dict(orient='rows')))
        return self.__class__(self._docs[lidx])


class LidxSelector(Selector):
    """ See LidxSelectorDf for a 'concrete' subclass """

    def __init__(self, _docs):
        self._docs = _docs

    def __getitem__(self, k):
        return self._docs.__getitem__(k)

    def _selector_func(self, selector):
        return Query(selector).match

    def to_dict(self):
        return dict(self._docs)  # probably want to override

    def _selection_lidx(self, selector_file_func):
        return list(map(selector_file_func, self.to_dict()))

    def select(self, selector):
        selector_func = self._selector_func(selector)
        selection_lidx = self._selection_lidx(selector_func)
        return self.__class__(self[selection_lidx])


class LidxSelectorDf(LidxSelector):
    """

    :param selector: A mongo-like query of the underlying dataframe
    :return:
    >>> _docs = [
    ...  {'bt': 0, 'tt': 5, 'tag': 'small'},
    ...  {'bt': 10, 'tt': 15, 'tag': 'small'},
    ...  {'bt': 20, 'tt': 25, 'tag': 'small'},
    ...  {'bt': 30, 'tt': 35, 'tag': 'big'},
    ...  {'bt': 40, 'tt': 45, 'tag': 'big'},
    ...  {'bt': 50, 'tt': 55, 'tag': 'big'}]
    >>> import pandas as pd
    >>> selector = LidxSelectorDf(pd.DataFrame(_docs))
    >>> len(selector)
    6
    >>> selection = selector.select({"tag": {"$eq": 'small'}})
    >>> len(selection)
    3
    >>> _print_docs(selection)
    {'bt': 0, 'tag': 'small', 'tt': 5}
    {'bt': 10, 'tag': 'small', 'tt': 15}
    {'bt': 20, 'tag': 'small', 'tt': 25}
    >>> selection = selector.select({'bt': {"$gte": 20}, 'tt': {"$lt": 45}})
    >>> _print_docs(selection)
    {'bt': 20, 'tag': 'small', 'tt': 25}
    {'bt': 30, 'tag': 'big', 'tt': 35}
    """

    def __len__(self):
        return len(self._docs)

    def __iter__(self):
        return (d.to_dict() for r, d in self._docs.iterrows())

    def to_dict(self):
        return self._docs.to_dict(orient='rows')

    def _selector_func(self, selector):
        return Query(selector).match
