from py2store import KvReader
from github import GithubException

# from py2store.util import lazyprop
# from py2store.trans import cache_iter
# from py2store.key_mappers.paths import PathGetMixin
from github import Github, ContentFile

from py2store.util import format_invocation


#
# from py2store.utils.signatures import update_signature_with_signatures_from_funcs
#
# # Just meant to be used for it's signature:
# def _account_name(account_name): ...

# @cache_iter(keys_cache=sorted)
# @cache_iter


def decoded_contents(content_file):
    return content_file.decoded_content
    # from base64 import b64decode
    # return b64decode(content_file.content).decode()


# TODO: use signature arithmetic
# @kv_decorator
class GitHubReader(KvReader):
    """
    a Store that can access a GitHub account
    """

    def __init__(
            self,
            account_name: str = None,
            content_file_extractor=decoded_contents,
            login_or_token=None,
            password=None,
            jwt=None,
            base_url="https://api.github.com",
            timeout=15,
            client_id=None,
            client_secret=None,
            user_agent="PyGithub/Python",
            per_page=30,
            verify=True,
            retry=None,
    ):

        assert isinstance(
            account_name, str
        ), "account_name must be given (and a str)"

        _github = Github(
            login_or_token=login_or_token,
            password=password,
            jwt=jwt,
            base_url=base_url,
            timeout=timeout,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            per_page=per_page,
            verify=verify,
            retry=retry,
        )
        self._github = _github
        self._source_obj = (
            _github.get_user(account_name)
            if account_name
            else _github.get_user()
        )
        self.content_file_extractor = content_file_extractor

    def __iter__(self):
        for x in self._source_obj.get_repos():
            org, name = x.full_name.split("/")
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
        return Branches(repository, self.content_file_extractor)

    def __repr__(self):
        return format_invocation(
            self.__class__.__name__,
            (self._source_obj, self.content_file_extractor),
        )


class Branches(KvReader):
    def __init__(
            self, repository_obj, content_file_extractor=decoded_contents
    ):
        self._source_obj = repository_obj
        self.content_file_extractor = content_file_extractor
        # self._con = repository_obj  # same as this.

    def __iter__(self):
        yield from (x.name for x in self._source_obj.get_branches())

    def __getitem__(self, k):
        # return self._source_obj.get_branch(k) # should not give only the branch
        # return self._source_obj.get_contents("", ref = k)
        return BranchDir(
            self._source_obj,
            branch_name=k,
            path="",
            content_file_extractor=self.content_file_extractor,
        )

    def __repr__(self):
        return format_invocation(
            self.__class__.__name__,
            (self._source_obj, self.content_file_extractor),
        )


class BranchDir(KvReader):
    def __init__(
            self,
            repository_obj,
            branch_name,
            path="",
            content_file_extractor=decoded_contents,
    ):
        self._source_obj = repository_obj
        self.branch_name = branch_name
        self.path = path
        self.content_file_extractor = content_file_extractor

    def __iter__(self):
        yield from (
            self.path + "/" + x.name
            for x in self._source_obj.get_contents(
            self.path, ref=self.branch_name
        )
        )
        # yield from (x.name for x in self._source_obj.get_contents(self.subpath, ref=self.branch_name))

    def __getitem__(self, k):
        t = self._source_obj.get_contents(k)
        # TODO: There is an inefficiency here in the isinstance(t, list) case
        if isinstance(
                t, list
        ):  # TODO: ... you already have the content_files in t, so don't need to call API again.
            return self.__class__(
                self._source_obj,
                self.branch_name,
                k,
                self.content_file_extractor,
            )
        else:
            return self.content_file_extractor(t)

    def __repr__(self):
        return format_invocation(
            self.__class__.__name__,
            (
                self._source_obj,
                self.branch_name,
                self.path,
                self.content_file_extractor,
            ),
        )
        # return f"{self.__class__.__name__}({self._source_obj}, {self.branch_name})"


# Not used, but for principle:


def _content_file_isfile(content_file):
    return content_file.type == "file"


def _content_file_isdir(content_file):
    return content_file.type == "dir"

# from py2store import kv_wrap
#
# BranchContent = kv_wrap.outcoming_vals(lambda x: x.contents if isinstance(x, ))


# class GitDir:
#     def __init__(self, content_files):
#         self.content_files = content_files

# @update_signature_with_signatures_from_funcs(Github.__init__, _account_name)
# def __init__(self, account_name, *args, **kwargs):
#     if len(args) > 0:
#         account_name = args[0]
#     else:
#         account_name = kwargs.pop('account_name', None)
#     assert isinstance(account_name, str), "account_name must be given (and a str)"
#
#     _source_obj = Github(*args, **kwargs)
#     self._access_args = (args, kwargs)
#     self._source_obj = _source_obj.get_user(account_name) if account_name else _source_obj.get_user()

# from py2store import KvReader
# from py2store import Store, Persister
# from github import GithubException
# from py2store.util import lazyprop
# from py2store.trans import cache_iter
# from py2store.key_mappers.paths import PathGetMixin
#
#
# # @cache_iter(keys_cache=sorted)
# # @cache_iter
#
# def check_credentials(account_name, access_token):
#     if access_token is None:
#         raise Exception('An access_token must be provided')
#     return account_name
#
#
# # @kv_decorator
# class GitHubReader(KvReader):
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
# # @cache_iter(keys_cache=sorted)
# # @cache_iter
# class GitHubReader(KvReader):
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
