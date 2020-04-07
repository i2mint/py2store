from py2store import KvReader
from py2store import Store, Persister
from github import GithubException
from py2store.util import lazyprop
from py2store.trans import cache_iter
from github import Github


# @cache_iter(iter_to_container=sorted)
# @cache_iter
class GitHubStore(KvReader):
    """
    a Store that can access a GitHub account
    """

    def __init__(self, access_token, access_kwargs=None):
        _source_obj = Github(login_or_token=access_token)
        self._access_kwargs = access_kwargs
        self._source_obj = _source_obj.get_user()

    def __iter__(self):
        for x in self._source_obj.get_repos():
            org, name = x.full_name.split('/')
            if org == self._source_obj.login:
                yield name

    #         yield from (x.full_name.split('/')[-1] for x in self._source_obj.get_repos())

    def __getitem__(self, k):
        """Retrieves a given repository
        :param k: str
        :rtype: :class:`github.Repository.Repository`
        """
        try:
            repository = self._source_obj.get_repo(k)
        except GithubException as e:
            raise KeyError(f"Key doesn't exist: {k}")

        return Branches(repository)


class Branches(KvReader):
    def __init__(self, repository_obj):
        self._source_obj = repository_obj
        # self._con = repository_obj  # same as this.

    def __iter__(self):
        yield from (x.name for x in self._source_obj.get_branches())

    def __getitem__(self, k):
        return self._source_obj.get_branch(k)
