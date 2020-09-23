import os
from configparser import ConfigParser
from setuptools import find_packages
from pack import read_configs


def my_setup(print_params=True, **setup_kwargs):
    from setuptools import setup
    if print_params:
        import json
        print("Setup params -------------------------------------------------------")
        print(json.dumps(setup_kwargs, indent=2))
        print("--------------------------------------------------------------------")
    setup(**setup_kwargs)


# read the config file (get a dict with it's contents)
root_dir = os.path.dirname(__file__)
config_file = os.path.join(root_dir, 'setup.cfg')
configs = read_configs(config_file, section='metadata')

# parse out name and root_url
name = configs['name']
root_url = configs['root_url']
version = configs.get('version', None)

# Note: if version is not in config, version will be None,
#  resulting in bumping the version or making it be 0.0.1 if the package is not found (i.e. first deploy)

meta_data_dict = {k: v for k, v in configs.items()}

# make the setup_kwargs
setup_kwargs = dict(
    meta_data_dict,
    # You can add more key=val pairs here if they're missing in config file
)

# import os
# name = os.path.split(os.path.dirname(__file__))[-1]

if version is None:
    try:
        from pack import next_version_for_package

        version = next_version_for_package(name)  # when you want to make a new package
    except Exception as e:
        print(f"Got an error trying to get the new version of {name} so will try to get the version from setup.cfg...")
        print(f"{e}")
        version = configs.get('version', None)
        if version is None:
            raise ValueError(f"Couldn't fetch the next version from PyPi (no API token?), "
                             f"nor did I find a version in setup.cfg (metadata section).")


def text_of_readme_md_file():
    try:
        with open('README.md') as f:
            return f.read()
    except:
        return ""


ujoin = lambda *args: '/'.join(args)

if root_url.endswith('/'):
    root_url = root_url[:-1]

dflt_kwargs = dict(
    name=f"{name}",
    version=f'{version}',
    url=f"{root_url}/{name}",
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    long_description=text_of_readme_md_file(),
    long_description_content_type="text/markdown",
)

setup_kwargs = dict(dflt_kwargs, **setup_kwargs)

##########################################################################################
# Diagnose setup_kwargs
_, containing_folder_name = os.path.split(os.path.dirname(__file__))
if setup_kwargs['name'] != containing_folder_name:
    print(f"!!!! containing_folder_name={containing_folder_name} but setup name is {setup_kwargs['name']}")

##########################################################################################
# Okay... set it up alright!
my_setup(**setup_kwargs)
