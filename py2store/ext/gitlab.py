import requests
import os
from warnings import warn
from operator import itemgetter

# if you want to use that environment variable
dflt_private_token = os.getenv('PY2STORE_GITLAB_API_TOKEN', None)

from py2store.util import lazyprop
from py2store import KvReader
from py2store.utils.uri_utils import mk_str_making_func

url_templates = dict(
    project_names='projects/',
    branche_names='projects/{project_id}/repository/branches',
    branch='projects/{project_id}/repository/branches/{branch_name}',
    commit_by_sha='projects/{project_id}/repository/commits/{commit_sha}',
    commit_message_by_sha='projects/{project_id}/repository/commits/{commit_sha}',
    commit_date_by_sha='projects/{project_id}/repository/commits/{commit_sha}',
    commit_diff_by_sha='projects/{project_id}/repository/commits/{commit_sha}/diff',
    file_from_repository='projects/{project_id}/repository/files/{file_path}',
    file_from_repository_raw='projects/{project_id}/repository/files/{file_path}/raw',
    project_files='projects/{project_id}/repository/tree',
    tags_list='projects/{project_id}/repository/tags'
)


def mk_url_factory(base_url):
    if not base_url.endswith('/'):
        base_url = base_url + '/'

    class url_for:
        pass

    for name, format in url_templates.items():
        func = mk_str_making_func(base_url + format, module=__name__, name=name)
        setattr(url_for, name, staticmethod(func))

    return url_for()


#
#     for k, v in Formats.__dict__.items():
#         def url(self):
#             return self.base_url + v
#         locals()['get_'  + k] = lazyprop(lambda self: self.base_url + getattr(self, k))


class GitlabProjectReader(KvReader):
    api_url_format = '{base_url}/api/v4/'

    def __init__(self, base_url, private_token=dflt_private_token):
        if dflt_private_token is None:
            warn("No private_token was given. "
                 "Provide it at instance creation time "
                 "or as the PY2STORE_GITLAB_API_TOKEN environment, "
                 "or however you wish (and if you're silly, you'll know who to blame!)")

        self.base_url = base_url
        self._private_token = private_token
        self._git_api_url = self.api_url_format.format(base_url=base_url)


# https://docs.gitlab.com/ce/api/README.html
class GitLabAccessor(object):
    api_url_format = '{base_url}/api/v4/'

    def __init__(self, base_url="http://git.otosense.ai/",
                 project_name=None, private_token=dflt_private_token):

        self.git_api_url = self.api_url_format.format(base_url=base_url)

        self.project_name = project_name
        self._headers = {'content-type': 'application/json'}
        self._private_token = private_token
        if self._private_token:
            self._headers['Private-Token'] = self._private_token

        self._set_project_id()
        self.request = get_request_constructor()

    def _get_stuff_from_url(self, url, output_trans=None, response_attr='json', params=None):
        response = requests.get(url, headers=self._headers, params=params)
        if response_attr == 'json':
            x = response.json()
        elif response_attr == 'content':
            x = response.content
        else:
            raise ValueError(f'Unknown response_attr: {response_attr}')

        if response.status_code != 200:
            raise Exception(f"{response.json()}")

        if output_trans is not None:
            return output_trans(x)
        else:
            return x

    def _get_json_from_url(self, url, output_trans=None, params=None):
        if isinstance(output_trans, str):
            field = output_trans
            output_trans = itemgetter(field)
        return self._get_stuff_from_url(url, output_trans, response_attr='json', params=params)

    def set_project(self, project_name=None):
        if project_name is None:
            warn("You need to specify a project_name. I'm returning a list of project_name for ya.")
            return self.get_project_names()
        else:
            self.project_name = project_name
            self._set_project_id()

    def _set_project_id(self):
        url = '{}/projects/'.format(self.git_api_url)
        params = {'search': self.project_name}
        response = requests.get(url, params=params, headers=self._headers)

        if response.status_code != 200:
            raise Exception(f"{response.json()}")
        else:
            projects = response.json()

            if len(projects) == 0:
                raise Exception('No Projects with name {} found.'.format(self.project_name))

            self.project_id = projects[0]['id']

    def get_project_names(self):
        url = '{}projects/'.format(self.git_api_url)
        return self._get_json_from_url(url, output_trans=lambda jdict: [x['name'] for x in jdict])
        # response = requests.get(url, headers=self._headers)
        # return [x['name'] for x in response.json()]

    def get_branch_names(self):
        url = '{}projects/{}/repository/branches'.format(self.git_api_url, self.project_id)
        return self._get_json_from_url(url, output_trans=lambda jdict: [x['name'] for x in jdict])
        # response = requests.get(url, headers=self._headers)
        # return [x['name'] for x in response.json()]

    def get_branch(self, branch_name=None):
        if branch_name is None:
            warn("You need to specify a branch. I'm returning a list of branches for ya.")
            return self.get_branch_names()
        else:
            url = '{}projects/{}/repository/branches/{}'.format(self.git_api_url, self.project_id, branch_name)
            return self._get_json_from_url(url)
            #
            # response = requests.get(url, headers=self._headers)
            # branch = response.json()
            #
            # return branch

    def get_commit_by_sha(self, commit_sha):
        url = '{}projects/{}/repository/commits/{}'.format(self.git_api_url, self.project_id, commit_sha)
        return self._get_json_from_url(url)
        #
        # response = requests.get(url, headers=self._headers)
        #
        # commit = response.json()
        #
        # return commit

    def get_commit_message_by_sha(self, commit_sha):
        url = '{}projects/{}/repository/commits/{}'.format(self.git_api_url, self.project_id, commit_sha)
        return self._get_json_from_url(url, output_trans='message')
        # response = requests.get(url, headers=self._headers)
        #
        # commit = response.json()
        #
        # return commit['message']

    def get_commit_date_by_sha(self, commit_sha):
        url = '{}projects/{}/repository/commits/{}'.format(self.git_api_url, self.project_id, commit_sha)
        return self._get_json_from_url(url, output_trans='date')
        # response = requests.get(url, headers=self._headers)
        #
        # commit = response.json()
        #
        # return commit['date']

    def get_commit_diff_by_sha(self, commit_sha):
        url = '{}projects/{}/repository/commits/{}/diff'.format(self.git_api_url, self.project_id, commit_sha)
        return self._get_json_from_url(url)
        #
        # response = requests.get(url, headers=self._headers)
        #
        # diff = response.json()
        #
        # return diff

    def get_file_from_repository(self, file_path, ref='master', raw=False):
        url = '{}projects/{}/repository/files/{}'.format(self.git_api_url, self.project_id,
                                                         file_path.replace('/', '%2F').replace('.', '%2E'))
        if raw:
            url = '{}projects/{}/repository/files/{}/raw'.format(self.git_api_url, self.project_id, file_path)

        params = {'ref': ref}
        return self._get_stuff_from_url(url, output_trans=None, response_attr='content', params=params)
        # response = requests.get(url, params=params, headers=headers)
        # file = response.content
        # return file

    def get_project_files(self):

        url = '{}projects/{}/repository/tree'.format(self.git_api_url, self.project_id)
        return self._get_json_from_url(url)
        # response = requests.get(url, headers=self._headers)
        #
        # files = response.json()
        #
        # return files

    def get_tags_list(self):

        url = '{}projects/{}/repository/tags'.format(self.git_api_url, self.project_id)
        return self._get_json_from_url(url)
        # response = requests.get(url, headers=self._headers)
        #
        # tags = response.json()
        #
        # return tags


def get_request_constructor():
    pass


if __name__ == "__main__":
    ogl = GitLabAccessor(base_url='http://git.otosense.ai/', project_name=None)

    print(ogl.get_project_names())  # prints all project names
    ogl.set_project('ssofnad')  # sets the project to ssofnad
    print(ogl.get_branch_names())  # gets the branch names of current project (as set previously)
    print(ogl.get_branch('master'))  # gets a json of information about the master branch of current project.
