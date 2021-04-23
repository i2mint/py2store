"""
Stores to talk to gitlab, using requests.

Example:
```
ogl = GitLabAccessor(base_url="http://...", project_name=None)

print(ogl.get_project_names())  # prints all project names
ogl.set_project("PROJECT_NAME")  # sets the project to "PROJECT_NAME"
print(
    ogl.get_branch_names()
)  # gets the branch names of current project (as set previously)
print(
    ogl.get_branch("master")
)  # gets a json of information about the master branch of current project.
```

"""

from contextlib import suppress

with suppress(ModuleNotFoundError, ImportError):
    from git2py.gitlab import *
