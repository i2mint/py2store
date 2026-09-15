# py2store.test.util

utils for testing

### Functions

| [`random_dict_gen`](#py2store.test.util.random_dict_gen)([fields, word_size_range, ...])   | Random dict (of strings) generator                                                                                           |
|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [`random_formatted_str_gen`](#py2store.test.util.random_formatted_str_gen)([format_string, ...])    | Random formatted string generator                                                                                            |
| [`random_string`](#py2store.test.util.random_string)([length, alphabet])                 | Same as random_word, but it optimized for strings (5-10% faster for words of length 7, 25-30% faster for words of size 1000) |
| [`random_tuple_gen`](#py2store.test.util.random_tuple_gen)([tuple_length, ...])             | Random tuple (of strings) generator                                                                                          |
| [`random_word`](#py2store.test.util.random_word)(length, alphabet[, concat_func])      | Make a random word by concatenating randomly drawn elements from alphabet together                                           |
| [`random_word_gen`](#py2store.test.util.random_word_gen)([word_size_range, alphabet, n])   | Random string generator                                                                                                      |

### py2store.test.util.random_dict_gen(fields=('a', 'b', 'c'), word_size_range=(1, 10), alphabet='abcdefghijklmnopqrstuvwxyz', n=100)

Random dict (of strings) generator

* **Parameters:**
  * **fields** – Field names for the random dicts
  * **word_size_range** – An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
  * **alphabet** – A string or iterable defining the alphabet to draw from
  * **n** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – The number of elements the generator will yield
* **Returns:**
  Random dict (of strings) generator

### py2store.test.util.random_formatted_str_gen(format_string='root/{}/{}_{}.test', word_size_range=(1, 10), alphabet='abcdefghijklmnopqrstuvwxyz', n=100)

Random formatted string generator

* **Parameters:**
  * **format_string** – A format string
  * **word_size_range** – An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
  * **alphabet** – A string or iterable defining the alphabet to draw from
  * **n** – The number of elements the generator will yield
* **Returns:**
  Yields random strings of the format defined by format_string

### Examples

# >>> list(random_formatted_str_gen(‘root/{}/{}_{}.test’, (2, 5), ‘abc’, n=5))
[(‘root/acba/bb_abc.test’,),

> (‘root/abcb/cbbc_ca.test’,),
> (‘root/ac/ac_cc.test’,),
> (‘root/aacc/ccbb_ab.test’,),
> (‘root/aab/abb_cbab.test’,)]
```pycon
>>> # The following will be made not random (by restricting the constraints to "no choice"
>>> # ... this is so that we get consistent outputs to assert for the doc test.
>>>
>>> # Example with automatic specification
>>> list(random_formatted_str_gen('root/{}/{}_{}.test', (3, 4), 'a', n=2))
[('root/aaa/aaa_aaa.test',), ('root/aaa/aaa_aaa.test',)]
>>>
>>> # Example with manual specification
>>> list(random_formatted_str_gen('indexed field: {0}: named field: {name}', (2, 3), 'z', n=1))
[('indexed field: zz: named field: zz',)]
```

### py2store.test.util.random_string(length=7, alphabet='abcdefghijklmnopqrstuvwxyz')

Same as random_word, but it optimized for strings
(5-10% faster for words of length 7, 25-30% faster for words of size 1000)

### py2store.test.util.random_tuple_gen(tuple_length=3, word_size_range=(1, 10), alphabet='abcdefghijklmnopqrstuvwxyz', n=100)

Random tuple (of strings) generator

* **Parameters:**
  * **tuple_length** – The length of the tuples generated
  * **word_size_range** – An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
  * **alphabet** – A string or iterable defining the alphabet to draw from
  * **n** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – The number of elements the generator will yield
* **Returns:**
  Random tuple (of strings) generator

### py2store.test.util.random_word(length, alphabet, concat_func=<built-in function add>)

Make a random word by concatenating randomly drawn elements from alphabet together

* **Parameters:**
  * **length** – Length of the word
  * **alphabet** – Alphabet to draw from
  * **concat_func** – The concatenation function (e.g. + for strings and lists)

#### NOTE
Repeated elements in alphabet will have more chances of being drawn.

* **Returns:**
  A word (whose type depends on what concatenating elements from alphabet produces).

Not making this a proper doctest because I don’t know how to seed the global random temporarily

```pycon
>>> t = random_word(4, 'abcde');  # e.g. 'acae'
>>> t = random_word(5, ['a', 'b', 'c']);  # e.g. 'cabba'
>>> t = random_word(4, [[1, 2, 3], [40, 50], [600], [7000]]);  # e.g. [40, 50, 7000, 7000, 1, 2, 3]
>>> t = random_word(4, [1, 2, 3, 4]);  # e.g. 13 (because adding numbers...)
>>> # ... sometimes it's what you want:
>>> t = random_word(4, [2 ** x for x in range(8)]);  # e.g. 105 (binary combination)
>>> t = random_word(4, [1, 2, 3, 4], concat_func=lambda x, y: str(x) + str(y));  # e.g. '4213'
>>> t = random_word(4, [1, 2, 3, 4], concat_func=lambda x, y: int(str(x) + str(y)));  # e.g. 3432
```

### py2store.test.util.random_word_gen(word_size_range=(1, 10), alphabet='abcdefghijklmnopqrstuvwxyz', n=100)

Random string generator

* **Parameters:**
  * **word_size_range** – An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
  * **alphabet** – A string or iterable defining the alphabet to draw from
  * **n** – The number of elements the generator will yield
* **Returns:**
  Random string generator
