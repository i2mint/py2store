"""Tests for py2store.key_mappers.tuples, utils.uri_utils and utils.cache_descriptors."""

import re
from dataclasses import dataclass

import pytest

from py2store.errors import KeyValidationError
from py2store.key_mappers.tuples import (
    dict_of_str,
    dict_of_tuple,
    dsv_of_list,
    list_of_dsv,
    mk_obj_of_str,
    mk_str_of_obj,
    str_of_dict,
    str_of_tuple,
    tuple_of_dict,
    tuple_of_str,
)
from py2store.utils.cache_descriptors import (
    CachedProperty,
    Lazy,
    cachedIn,
    readproperty,
)
from py2store.utils.uri_utils import build_uri, mk_str_making_func, parse_uri


# ---- key_mappers.tuples ----------------------------------------------------------


def test_tuple_and_dict_conversions_roundtrip():
    fields = ("a", "b")
    assert tuple_of_dict({"b": 2, "a": 1}, fields) == (1, 2)
    assert dict_of_tuple((1, 2), fields) == {"a": 1, "b": 2}
    assert dict_of_tuple(tuple_of_dict({"a": 1, "b": 2}, fields), fields) == {
        "a": 1,
        "b": 2,
    }


def test_size_mismatch_raises_key_validation_error():
    with pytest.raises(KeyValidationError):
        tuple_of_dict({"a": 1}, ("a", "b"))
    with pytest.raises(KeyValidationError):
        dict_of_tuple((1,), ("a", "b"))


def test_str_conversions():
    assert str_of_tuple(("x", "y"), "{}/{}") == "x/y"
    assert str_of_dict({"a": 1, "b": 2}, "{a}-{b}") == "1-2"
    with pytest.raises(KeyValidationError):
        str_of_tuple(("x",), "{}/{}")
    with pytest.raises(KeyValidationError):
        str_of_dict({"a": 1}, "{a}-{b}")

    rx = re.compile(r"(\w+)/(\w+)")
    assert tuple_of_str("x/y", rx) == ("x", "y")
    rxd = re.compile(r"(?P<a>\w+)/(?P<b>\w+)")
    assert dict_of_str("x/y", rxd) == {"a": "x", "b": "y"}
    with pytest.raises(KeyValidationError):
        tuple_of_str("nope", rx)
    with pytest.raises(KeyValidationError):
        dict_of_str("nope", rxd)


def test_mk_str_of_obj_and_obj_of_str():
    @dataclass
    class A:
        foo: int
        bar: str

    assert mk_str_of_obj(["foo", "bar"])(A(0, "rin"), "ST{foo}/{bar}/G") == "ST0/rin/G"

    seen = {}
    obj_of_str = mk_obj_of_str(lambda **kw: seen.update(kw))
    obj_of_str("1/2", re.compile(r"(?P<x>\d)/(?P<y>\d)"))
    assert seen == {"x": "1", "y": "2"}


@pytest.mark.xfail(
    reason="mk_obj_of_str's obj_of_str does not return the constructed object",
    strict=True,
)
def test_mk_obj_of_str_returns_the_object():
    obj_of_str = mk_obj_of_str(lambda **kw: kw)
    assert obj_of_str("1", re.compile(r"(?P<x>\d)")) == {"x": "1"}


def test_dsv_roundtrip_including_empty():
    for parts in (["a", "b", "c"], ["solo"], []):
        assert list_of_dsv(dsv_of_list(parts, sep="|"), sep="|") == parts


# ---- utils.uri_utils -------------------------------------------------------------


def test_parse_and_build_uri():
    uri = "mongodb://user:pw@example.org:27017/mydb"
    assert parse_uri(uri) == {
        "scheme": "mongodb",
        "database": "mydb",
        "username": "user",
        "password": "pw",
        "hostname": "example.org",
        "port": 27017,
    }
    assert build_uri("mongodb", "mydb", "user", "pw", "example.org", 27017) == uri
    assert parse_uri("http://host")["database"] == ""


def test_mk_str_making_func():
    f = mk_str_making_func("{a}/{b}", name="f", module="m")
    assert f("x", "y") == "x/y"
    assert f("x", b="y") == "x/y"
    assert (f.__module__, f.__qualname__) == ("m", "f")
    with pytest.raises(ValueError, match="too many"):
        f("x", "y", "z")
    with pytest.raises(ValueError, match="too few"):
        f("x")

    g = mk_str_making_func("{a}", input_trans=lambda a: {"a": a.upper()})
    assert g("q") == "Q"

    class C:
        make = mk_str_making_func("{a}-{b}", method=True)

    assert C().make(1, 2) == "1-2"
    with pytest.raises(ValueError):
        C().make(1)


# ---- utils.cache_descriptors -----------------------------------------------------


def test_cached_property_with_dependencies():
    class C:
        n = 1
        calls = 0

        @CachedProperty("n")
        def double(self):
            C.calls += 1
            return self.n * 2

    c = C()
    assert (c.double, c.double, C.calls) == (2, 2, 1)
    c.n = 5  # a dependency changed: recomputed
    assert (c.double, C.calls) == (10, 2)
    assert isinstance(C.double, type(C.__dict__["double"]))  # class access returns it


def test_cached_property_forms():
    class C:
        calls = 0

        @CachedProperty
        def bare(self):
            C.calls += 1
            return 1

        @CachedProperty()
        def called(self):
            C.calls += 1
            return 2

    c = C()
    assert (c.bare, c.bare, c.called, c.called, C.calls) == (1, 1, 2, 2, 2)


def test_lazy_readproperty_cachedin():
    class C:
        n = 0

        @Lazy
        def lazy(self):
            C.n += 1
            return C.n

        @readproperty
        def fresh(self):
            C.n += 1
            return C.n

        @cachedIn("_cache")
        def cached(self):
            C.n += 1
            return C.n

    c = C()
    assert c.lazy == c.lazy == 1  # stored on the instance after first access
    assert c.fresh != c.fresh  # recomputed every time
    first = c.cached
    assert c.cached == first
    assert C.lazy.__name__ == "lazy" and C.fresh.__name__ == "fresh"
