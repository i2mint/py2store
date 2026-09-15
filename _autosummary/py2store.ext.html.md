# py2store.ext

py2store Extensions, Add-ons, etc.
We kept py2store purely dependency-less, using only built-ins for everything but storage system connectors.

That said, in order to provide the user with more power, and show him/her how py2store tools can be used to build
powerful data accessors, we provide specialized modules that do require more than builtins. These dependencies are
not listed in the setup.py module, but we wrap their imports with informative ImportError handlers.

### Modules

| [`dataframes`](py2store.ext.dataframes.html.md#module-py2store.ext.dataframes)   | Data as `pandas.DataFrame` from various sources   |
|----------------------------------------------------------------------------------------------|---------------------------------------------------|
| [`docx`](py2store.ext.docx.html.md#module-py2store.ext.docx)               | Simple access to docx (Word Doc) elements.        |
| [`github`](py2store.ext.github.html.md#module-py2store.ext.github)           | a data object layer for github                    |
| [`gitlab`](py2store.ext.gitlab.html.md#module-py2store.ext.gitlab)           | Stores to talk to gitlab, using requests.         |
| [`hdf`](py2store.ext.hdf.html.md#module-py2store.ext.hdf)                 | a data object layer for HDF files                 |
| [`matlab`](py2store.ext.matlab.html.md#module-py2store.ext.matlab)           | a data object layer for matlab                    |
| [`wordnet`](py2store.ext.wordnet.html.md#module-py2store.ext.wordnet)         | This moved to lexis project                       |
