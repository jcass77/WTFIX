import pytest

from wtfix.conf import settings
from ..field import Field, FieldValue
from wtfix.core.exceptions import InvalidField


class TestFieldValue:
    def test_init_does_not_wrap_fieldvalue(self):
        fv = FieldValue(FieldValue("abc"))
        assert not isinstance(fv.value, FieldValue)

    def test_getitem(self):
        assert FieldValue("abc")[1] == "b"

    def test_len(self):
        assert len(FieldValue("abc")) == 3

    def test_eq_str(self):
        assert FieldValue("abc") == "abc"

    def test_eq_bytes(self):
        assert FieldValue(b"abc") == b"abc"

    def test_eq_int(self):
        assert FieldValue(1) == 1

    def test_eq_boolean(self):
        assert FieldValue("Y") == True

    def test_eq_str_string(self):
        assert str(FieldValue("abc")) == "abc"

    def test_eq_bytes_str(self):
        assert FieldValue(b"abc") == "abc"

    def test_eq_bytes_int(self):
        assert FieldValue(b"1") == 1

    def test_eq_str_bytes(self):
        assert FieldValue("abc") == b"abc"

    def test_eq_str_int(self):
        assert FieldValue("1") == 1

    def test_eq_fieldvalue(self):
        assert FieldValue("abc") == FieldValue(b"abc")

    def test_str_bytes(self):
        assert str(FieldValue(b"abc")) == "abc"

    def test_str_int(self):
        assert str(FieldValue(1)) == "1"

    def test_contains(self):
        assert "a" in FieldValue("abc")
        assert b"a" in FieldValue(b"abc")

    def test_iter(self):
        assert [i for i in iter(FieldValue("abc"))] == ["a", "b", "c"]

    def test_raw(self):
        assert FieldValue("abc").raw == b"abc"


class TestField:
    def test_new_validates_tag_is_int(self):
        with pytest.raises(InvalidField):
            Field("abc", "k")

    def test_int_value(self):
        assert Field(1, 2) == 2

    def test_eq_value(self):
        assert Field(1, "a") == "a"
        assert Field(1, 2) == 2
        assert Field(1, b"a") == b"a"

    def test_eq_field(self):
        assert Field(1, "a") == Field(1, "a")

    def test_repr(self):
        assert repr(Field(35, "k")) == "(35, k)"

    def test_str(self):
        assert str(Field(35, "k")) == "(MsgType (35), k)"

    def test_str_unknown_tag(self):
        assert str(Field(1234567890, "k")) == "(1234567890, k)"

    def test_name_getter(self):
        f = Field(35, "k")
        assert f.name == "MsgType"

    def test_name_getter_custom(self):
        f = Field(1234567890, "k")
        assert f.name == "Unknown"

    def test_raw_getter(self):
        f = Field(35, "k")
        assert f.raw == b"35=k" + settings.SOH
