from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='py2store',
    version='0.0.1',
    description='Interfacing with stored data through python.',
    long_description=readme(),
    url='https://github.com/i2mint/py2store',
    author='Thor Whalen',
    license='Apache',
    packages=find_packages(),
    install_requires=[],
    include_package_data=True,
    zip_safe=False,

    download_url='https://github.com/i2mint/py2store/archive/v0.0.1.zip',
    keywords=['storage', 'interface'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        # Either
        # "3 - Alpha",
        # "4 - Beta" or
        # "5 - Production/Stable" as the current state.

        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
