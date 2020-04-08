from py2store import KvReader
from py2store import Store, Persister
from github import GithubException
from py2store.util import lazyprop
from py2store.trans import cache_iter
from py2store.key_mappers.paths import PathGetMixin
from github import Github

from py2store.util import format_invocation


# @cache_iter(iter_to_container=sorted)
# @cache_iter

def check_credentials(account_name, access_token):
    if access_token is None:
        raise Exception('An access_token must be provided')
    return account_name


# @kv_decorator
class GitHubStore(KvReader):
    """
    a Store that can access a GitHub account
    """

    def __init__(self, account_name=None, access_token=None, access_kwargs=None):
        account_name = check_credentials(account_name, access_token)
        _source_obj = Github(login_or_token=access_token)
        self._access_kwargs = access_kwargs
        self._source_obj = _source_obj.get_user(account_name) if account_name else _source_obj.get_user()

    def __iter__(self):
        for x in self._source_obj.get_repos():
            org, name = x.full_name.split('/')
            if org == self._source_obj.login:
                yield name

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

    def __repr__(self):
        return format_invocation(self.__class__.__name__, (self._source_obj,))


class Branches(KvReader):
    def __init__(self, repository_obj):
        self._source_obj = repository_obj
        # self._con = repository_obj  # same as this.

    def __iter__(self):
        yield from (x.name for x in self._source_obj.get_branches())

    def __getitem__(self, k):
        # return self._source_obj.get_branch(k) # should not give only the branch
        # return self._source_obj.get_contents("", ref = k)
        return BranchContent(self._source_obj, k)

    def __repr__(self):
        return format_invocation(self.__class__.__name__, (self._source_obj,))


class BranchContent(KvReader):
    def __init__(self, repository_obj, branch_name):
        self._source_obj = repository_obj
        self.branch_name = branch_name

    def __iter__(self):
        yield from (x.name for x in self._source_obj.get_contents("", ref=self.branch_name))

    def __getitem__(self, k):
        return self._source_obj.get_contents(k)

    def __repr__(self):
        return format_invocation(self.__class__.__name__, (self._source_obj, self.branch_name))
        # return f"{self.__class__.__name__}({self._source_obj}, {self.branch_name})"

# from py2store import KvReader
# from py2store import Store, Persister
# from github import GithubException
# from py2store.util import lazyprop
# from py2store.trans import cache_iter
# from py2store.key_mappers.paths import PathGetMixin
#
#
# # @cache_iter(iter_to_container=sorted)
# # @cache_iter
#
# def check_credentials(account_name, access_token):
#     if access_token is None:
#         raise Exception('An access_token must be provided')
#     return account_name
#
#
# # @kv_decorator
# class GitHubStore(KvReader):
#     """
#     a Store that can access a GitHub account
#     """
#
#     def __init__(self, account_name=None, access_token=None, access_kwargs=None):
#         account_name = check_credentials(account_name, access_token)
#         _source_obj = Github(login_or_token=access_token)
#         self._access_kwargs = access_kwargs
#         self._source_obj = _source_obj.get_user(account_name) if account_name else _source_obj.get_user()
#
#     def __iter__(self):
#         for x in self._source_obj.get_repos():
#             org, name = x.full_name.split('/')
#             if org == self._source_obj.login:
#                 yield name
#
#     def __getitem__(self, k):
#         """Retrieves a given repository
#         :param k: str
#         :rtype: :class:`github.Repository.Repository`
#         """
#         try:
#             repository = self._source_obj.get_repo(k)
#         except GithubException as e:
#             raise KeyError(f"Key doesn't exist: {k}")
#         return Branches(repository)
#
#
# class Branches(KvReader):
#     def __init__(self, repository_obj):
#         self._source_obj = repository_obj
#         # self._con = repository_obj  # same as this.
#
#     def __iter__(self):
#         yield from (x.name for x in self._source_obj.get_branches())
#
#     def __getitem__(self, k):
#         # return self._source_obj.get_branch(k) # should not give only the branch
#         # return self._source_obj.get_contents("", ref = k)
#         return BranchContent(self._source_obj, k)
#
#
# class BranchContent(KvReader):
#     def __init__(self, repository_obj, branch_name):
#         self._source_obj = repository_obj
#         self.branch_name = branch_name
#
#     def __iter__(self):
#         yield from (x.name for x in self._source_obj.get_contents("", ref=self.branch_name))
#
#     def __getitem__(self, k):
#         return self._source_obj.get_contents(k)


# from py2store import KvReader
# from py2store import Store, Persister
# from github import GithubException
# from py2store.util import lazyprop
# from py2store.trans import cache_iter
# from github import Github
#
#
# # @cache_iter(iter_to_container=sorted)
# # @cache_iter
# class GitHubStore(KvReader):
#     """
#     a Store that can access a GitHub account
#     """
#
#     def __init__(self, access_token, access_kwargs=None):
#         _source_obj = Github(login_or_token=access_token)
#         self._access_kwargs = access_kwargs
#         self._source_obj = _source_obj.get_user()
#
#     def __iter__(self):
#         for x in self._source_obj.get_repos():
#             org, name = x.full_name.split('/')
#             if org == self._source_obj.login:
#                 yield name
#
#     #         yield from (x.full_name.split('/')[-1] for x in self._source_obj.get_repos())
#
#     def __getitem__(self, k):
#         """Retrieves a given repository
#         :param k: str
#         :rtype: :class:`github.Repository.Repository`
#         """
#         try:
#             repository = self._source_obj.get_repo(k)
#         except GithubException as e:
#             raise KeyError(f"Key doesn't exist: {k}")
#
#         return Branches(repository)
#
#
# class Branches(KvReader):
#     def __init__(self, repository_obj):
#         self._source_obj = repository_obj
#         # self._con = repository_obj  # same as this.
#
#     def __iter__(self):
#         yield from (x.name for x in self._source_obj.get_branches())
#
#     def __getitem__(self, k):
#         return self._source_obj.get_branch(k)
