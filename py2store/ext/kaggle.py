from kaggle.api import KaggleApi
from py2store import KvReader, FilesOfZip
from py2store.util import lazyprop

DFLT_MAX_ITEMS = 200
DFLT_MAX_PAGES = 10


class DataInfoPaggedItems:
    def __init__(self):
        self.pages = []
        self.ref_to_idx = dict()

    def append(self, page_contents):
        # TODO: Atomize this code so it can't be broken by async
        page = self.n_pages()
        for i, v in enumerate(page_contents):
            ref = v.get('ref', None)
            if ref is not None:
                self.ref_to_idx[ref] = (page, i)
        self.pages.append(page_contents)

    def __getitem__(self, ref):
        page, i = self.ref_to_idx[ref]
        return self.pages[page][i]

    def __len__(self):
        return len(self.ref_to_idx)

    def get_page_contents(self, page):
        return self.pages[page]

    def n_pages(self):
        return len(self.pages)


class KaggleDatasetInfoReader(KvReader):
    """
    A KvReader to access Kaggle resources.

    Prerequisites:
        pip install kaggle
        Having a kaggle api token where the kaggle library will be looking for it
            (see https://github.com/Kaggle/kaggle-api#api-credentials)

    You seed a Reader by specifying any combination of things like search terms, groups, filetypes etc.
    See `kaggle.api` for more information.
    Additional (and specific to py2store reader) arguments are
        start_page (default 0, but useful for paging),
        max_n_pages (to not hit the API too hard if your query is large), and
        warn_if_there_are_more_items if you want to be warned if there's more items than what you see

    >>> ka = KaggleDatasetInfoReader(search='coronavirus covid')
    >>> ka = KaggleDatasetInfoReader(user='sudalairajkumar', start_page=1, max_n_pages=2)

    """

    def __init__(self, *, group=None, sort_by=None, filetype=None, license=None,
                 tagids=None, search=None, user=None,
                 start_page=0, max_n_pages=DFLT_MAX_PAGES,
                 warn_if_there_are_more_items=False,
                 **kwargs):
        """
        :param async_req bool
        :param str group: Display datasets by a particular group
        :param str sort_by: Sort the results
        :param str filetype: Display datasets of a specific file type
        :param str license: Display datasets with a specific license
        :param str tagids: A comma separated list of tags to filter by
        :param str search: Search terms
        :param str user: Display datasets by a specific user or organization
        :param int start_page: Page to start at (default is 0)
        :param int max_n_pages: Maximum number of pages the container should hold (to avoid API overuse)
        :param bool warn_if_there_are_more_items: To be warned if there's more items than what you see
        :param int max_size: Max Dataset Size (bytes)
        :param int min_size: Max Dataset Size (bytes)
        :param kwargs:
        """
        explicit_fields = {'group', 'sort_by', 'filetype', 'license', 'tagids', 'search', 'user'}
        locs = locals()
        kwargs.update(**{k: locs[k] for k in explicit_fields if locs[k] is not None})
        self.dataset_filt = kwargs
        self._source = KaggleApi()
        self._source.authenticate()
        self.start_page = start_page
        self.max_n_pages = max_n_pages
        self.warn_if_there_are_more_items = warn_if_there_are_more_items
        self.last_page = None
        self.max_pages_reached = None

    def _info_items_gen(self):
        page_num = self.start_page
        while (page_num - self.start_page) < self.max_n_pages:
            new_page_contents = self._source.datasets_list(page=page_num, **self.dataset_filt)
            if len(new_page_contents) > 0:
                yield from new_page_contents
                page_num += 1
            else:
                self.max_pages_reached = True
                break
        self.last_page = page_num

    @lazyprop
    def info_of_ref(self):
        return {item['ref']: item for item in self.cached_info_items}

    @lazyprop
    def cached_info_items(self):
        return list(self._info_items_gen())

    def __iter__(self):
        yield from self.info_of_ref

    def __getitem__(self, k):
        """
        Get information (a dict) about a dataset, given its ref (a 'user_slug/dataset_slug' string).
        Note: Allows to access all valid references. Not just those within the current container.
        """
        return self.info_of_ref[k]

    def __len__(self):
        n = len(self.info_of_ref)
        self._warn_reached_max(n)
        return n

    def _warn_reached_max(self, n):
        if self.max_pages_reached and self.warn_if_there_are_more_items:
            from warnings import warn
            warn(f"The container has {n} items, but the max number of pages"
                 f"({self.max_n_pages}) was reached, so there may be more on kaggle than what you see! "
                 "If you want more, set max_items to something higher (but beware of overusing your API rights)")


# TODO: Make it less wasteful to get from a KaggleDatasetInfoReader to KaggleDatasetReader.
#   For example, by having a from_info_reader classmethod constructor, or putting both together.
class KaggleBinaryDatasetReader(KaggleDatasetInfoReader):
    def __getitem__(self, k):
        """
        Download a dataset, given its ref (a 'user_slug/dataset_slug' string).
        Will return the binary of the dataset, which should be saved to a file to be persisted.
        Note: Allows to access all valid references. Not just those within the current container.
        """
        owner_slug, dataset_slug = k.split('/')
        response = self._source.process_response(
            self._source.datasets_download_with_http_info(owner_slug=owner_slug,
                                                          dataset_slug=dataset_slug,
                                                          _preload_content=False))
        return response.read()


class KaggleDatasetReader(KaggleBinaryDatasetReader):
    def __getitem__(self, k):
        """
        Download a dataset, given its ref (a 'user_slug/dataset_slug' string).
        Will return the binary of the dataset, which should be saved to a file to be persisted.
        Note: Allows to access all valid references. Not just those within the current container.
        """
        return FilesOfZip(super().__getitem__(k))

#
# dataset = 'sudalairajkumar/novel-corona-virus-2019-dataset'
#
# owner_slug, dataset_slug = dataset.split('/')
# # path=None,
# # force=False,
# # quiet=True,
# # unzip=False):
# """ download all files for a dataset
#
#     Parameters
#     ==========
#     dataset: the string identified of the dataset
#              should be in format [owner]/[dataset-name]
#     path: the path to download the dataset to
#     force: force the download if the file already exists (default False)
#     quiet: suppress verbose output (default is True)
#     unzip: if True, unzip files upon download (default is False)
# """
#
# # if path is None:
# #     effective_path = self.get_default_download_dir(
# #         'datasets', owner_slug, dataset_slug)
# # else:
# #     effective_path = path
#
# response = self.process_response(
#     self.datasets_download_with_http_info(owner_slug=owner_slug,
#                                           dataset_slug=dataset_slug,
#                                           _preload_content=False))
