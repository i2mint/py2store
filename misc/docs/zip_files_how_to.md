
# A reader of multiple zip files

You'll find the main zip file handling stuff in module: `py2store.slib.s_zipfile`.


Let's assume the most common case where your zips are in a folder (and possibly subfolders). 
The three following objects should cover most of your cases:

```python
from py2store.slib.s_zipfile import ZipFilesReader, FlatZipFilesReader, mk_flatzips_store
```

That's in order of dependency ( `mk_flatzips_store` uses `FlatZipFilesReader` uses `ZipFilesReader`).


## ZipFilesReader

Gives you a reader whose keys are full paths to zip files and values are `ZipReader` objects (by default, but customizable).

```python
z = ZipFilesReader(zipdir)
k, v = z.head()  # get a key and a value to see what this store is about
print(f"{k=}")
print(f"{type(v)=} {len(v)=}")
```

```
k='/Users/data/zips/some_zip_file.zip'
type(v)=<class 'py2store.slib.s_zipfile.ZipReader'> len(v)=45
```

The length of `v` is the number of files in the `some_zip_file.zip` zip file.


## FlatZipFilesReader

With `ZipFilesReader` you get access to zips of a folder, and contents of the zips through the values it provides. 
But sometimes you want to have direct access to the contents of multiple zips. 
`FlatZipFilesReader` will provide you with that. 

It's keys are `(relative_zip_filepath, key_within_that_zip_file)` pairs and it's values are bytes of the zip content the key is pointing to.

```python
z = FlatZipFilesReader(zipdir)
k, v = z.head()  # get a key and a value to see what this store is about
print(f"{k=}")
print(f"{type(v)=} {len(v)=}")
```

```
k=('some_zip_file.zip', 'some_folder_in_zip/a_subfolder/a_file.xlsx')
type(v)=<class 'bytes'> len(v)=19430710
```

The length here is the number of bytes that `a_file.xlsx` has.

## mk_flatzips_store

Sometimes using `(relative_zip_filepath, key_within_that_zip_file)` as keys is not practical. 
When you don't like the key language, you can always change it. 
You have `trans.wrap_kvs` to help with that, as well as several specialized tools like `key_mappers.naming`, etc.

In our current case, one practical key to use would be to just use the second element of the pair: The key of the particular zip file. 
This isn't a problem as long as they are all unique (amongst the multiple zip files). 
The `mk_flatzips_store` does that work for you -- checking for unicity and giving you a reader that uses such simpler keys:

```python
z = mk_flatzips_store(zipdir)
k, v = z.head()  # get a key and a value to see what this store is about
print(f"{k=}")
print(f"{type(v)=} {len(v)=}")
```

```
k='some_folder_in_zip/a_subfolder/a_file.xlsx'
type(v)=<class 'bytes'> len(v)=1893
```

