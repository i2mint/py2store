from py2store.selectors.mongoquery import Query


class MgDfSelector:
    def __init__(self, _df):
        self._df = _df

    def __iter__(self):
        return (d.to_dict() for r, d in self._df.iterrows())

    def __len__(self):
        return len(self._df)

    def select(self, selector):
        selector_file_func = Query(selector).match
        lidx = list(map(selector_file_func, self._df.to_dict(orient='rows')))
        return self.__class__(self._df[lidx])

