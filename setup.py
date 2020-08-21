from setuptools import setup, find_packages


def readme():
    try:
        with open("README.md") as f:
            return f.read()
    except:
        return ""


ujoin = lambda *args: "/".join(args)

root_url = "https://github.com/i2mint"
name = "py2store"
version = "0.0.7"

assert not root_url.endswith(
    "/"
), f"root_url should not end with /: {root_url}"

setup(
    name="py2store",
    version=f"{version}",
    description="DAO for Python: Tools to create simple and consistent "
                "interfaces to complicated and varied data sources.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url=f"{root_url}/{name}",
    author="Thor Whalen",
    license="Apache",
    packages=find_packages(),
    install_requires=[],
    include_package_data=True,
    zip_safe=False,
    download_url=f"{root_url}/{name}/archive/v{version}.zip",
    keywords=["storage", "interface"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        # Either
        # "3 - Alpha",
        # "4 - Beta" or
        # "5 - Production/Stable" as the current state.
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.7",
    ],
)
