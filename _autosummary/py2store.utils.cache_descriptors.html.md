# py2store.utils.cache_descriptors

descriptors to cache data

### Functions

| [`CachedProperty`](#py2store.utils.cache_descriptors.CachedProperty)(\*args)   | CachedProperties.   |
|---------------------------------------------------------------------------|---------------------|

### Classes

| [`Lazy`](#py2store.utils.cache_descriptors.Lazy)(func[, name])       | Lazy Attributes.                            |
|---------------------------------------------------------------------------|---------------------------------------------|
| [`cachedIn`](#py2store.utils.cache_descriptors.cachedIn)(attribute_name) | Cached property with given cache attribute. |
| `readproperty`(func)                                                      |                                             |

### py2store.utils.cache_descriptors.CachedProperty(\*args)

CachedProperties.
This is usable directly as a decorator when given names, or when not. Any of these patterns
will work:

* `@CachedProperty`
* `@CachedProperty()`
* `@CachedProperty('n','n2')`
* def thing(self: …; thing = CachedProperty(thing)
* def thing(self: …; thing = CachedProperty(thing, ‘n’)

### *class* py2store.utils.cache_descriptors.Lazy(func, name=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Lazy Attributes.

### *class* py2store.utils.cache_descriptors.cachedIn(attribute_name)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Cached property with given cache attribute.
