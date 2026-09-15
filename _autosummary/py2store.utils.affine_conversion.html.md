# py2store.utils.affine_conversion

utils to carry out affine transformations (of indices)

### Functions

| [`get_affine_converter_and_inverse`](#py2store.utils.affine_conversion.get_affine_converter_and_inverse)([scale, ...])   | Getting two affine functions with given scale and offset, that are inverse of each other. Namely (for input val)::.   |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|

### Classes

| [`AffineConverter`](#py2store.utils.affine_conversion.AffineConverter)([scale, offset])   | Getting a callable that will perform an affine conversion. Note, it does it as     (val - offset) \* scale.   |
|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|

### *class* py2store.utils.affine_conversion.AffineConverter(scale=1.0, offset=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Getting a callable that will perform an affine conversion.
Note, it does it as

> (val - offset) \* scale

(Note slope-intercept style (though there is the .from_slope_and_intercept constructor method for that)

Inverse is available through the inv method, performing:

```default
val / scale + offset
```

```pycon
>>> convert = AffineConverter(scale=0.5, offset=1)
>>> convert(0)
-0.5
>>> convert(10)
4.5
>>> convert.inv(4)
9.0
>>> convert.inv(4.5)
10.0
```

### py2store.utils.affine_conversion.get_affine_converter_and_inverse(scale=1, offset=0, source_type_cast=None, target_type_cast=None)

Getting two affine functions with given scale and offset, that are inverse of each other. Namely (for input val):

```default
(val - offset) * scale and val / scale + offset
```

Note this is not “slope intercept” style!!

The source_type_cast and target_type_case (optional), allow the user to specify if these transformations need to
be further cast to a given type.

* **Parameters:**
  * **scale**
  * **offset**
  * **source_type_cast** – function to apply to input
  * **target_type_cast** – function to apply to output
* **Returns:**
  Two single val functions: affine_converter, inverse_affine_converter

#### NOTE
Code is a lot more complex than the basic operations it performs. The reason was a worry of efficiency since
the functions that are returned are intended to be used in long loops.

#### SEE ALSO
ocore.utils.conversion.AffineConverter

```pycon
>>> affine_converter, inverse_affine_converter = get_affine_converter_and_inverse(scale=0.5,offset=1)
>>> affine_converter(0)
-0.5
>>> affine_converter(10)
4.5
>>> inverse_affine_converter(4)
9.0
>>> inverse_affine_converter(4.5)
10.0
>>> affine_converter, inverse_affine_converter = get_affine_converter_and_inverse(scale=0.5,offset=1,target_type_cast=int)
>>> affine_converter(10)
4
```
