import pytest

from wtfix.conf import settings
from wtfix.core import utils
from ..field import Field, FieldValue
from wtfix.core.exceptions import InvalidField


class TestFieldValue:
    def test_init_does_not_wrap_fieldvalue(self):
        fv = FieldValue(FieldValue("abc"))
        assert not isinstance(fv.value, FieldValue)

    def test_init_converts_booleans_true(self):
        fv = FieldValue(True)
        assert fv.value == "Y"

    def test_init_converts_booleans_false(self):
        fv = FieldValue(False)
        assert fv.value == "N"

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
        true_vals = ("y", "yes", "t", "true", "on", "1")
        assert all(FieldValue(value) == True for value in true_vals)

        false_vals = ("n", "no", "f", "false", "off", "0")
        assert all(FieldValue(value) == False for value in false_vals)

    def test_eq_boolean_inverse(self):
        true_vals = ("y", "yes", "t", "true", "on", "1")
        assert all(FieldValue(value) != False for value in true_vals)

        false_vals = ("n", "no", "f", "false", "off", "0")
        assert all(FieldValue(value) != True for value in false_vals)

    def test_eq_str_string_true(self):
        assert str(FieldValue("abc")) == "abc"

    def test_eq_str_string_false(self):
        assert str(FieldValue("abc")) != "123"

    def test_eq_str_bytes_true(self):
        assert FieldValue("abc") == b"abc"

    def test_eq_str_bytes_false(self):
        assert FieldValue("abc") != b"123"

    def test_eq_str_int_true(self):
        assert FieldValue("1") == 1

    def test_eq_str_int_false(self):
        assert FieldValue("2") != 1

    def test_eq_bytes_str_true(self):
        assert FieldValue(b"abc") == "abc"

    def test_eq_bytes_str_false(self):
        assert FieldValue(b"abc") != "123"

    def test_eq_bytes_int_true(self):
        assert FieldValue(b"1") == 1

    def test_eq_bytes_int_false(self):
        assert FieldValue(b"1") != "2"

    def test_int_str_true(self):
        assert FieldValue(1) == "1"

    def test_int_str_false(self):
        assert FieldValue(1) != "2"

    def test_int_str_wrong_type(self):
        assert FieldValue(1) != "abc"

    def test_eq_fieldvalue(self):
        assert FieldValue("abc") == FieldValue(b"abc")

    def test_contains(self):
        assert "a" in FieldValue("abc")
        assert b"a" in FieldValue(b"abc")

    def test_iter(self):
        assert [i for i in iter(FieldValue("abc"))] == ["a", "b", "c"]

    def test_value_setter(self):
        fv = FieldValue(123)
        fv.value = 456

        assert fv.value == 456

    def test_value_setter_converts_null(self):
        fv = FieldValue(123)
        assert fv.value == 123

        fv.value = utils.null
        assert fv.value is None

        fv.value = utils.encode(utils.null)
        assert fv.value is None

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

    def test_eq_tuple(self):
        assert Field(1, "a") == (1, "a")

    def test_repr(self):
        assert repr(Field(35, "k")) == "(35, k)"

    def test_str(self):
        assert str(Field(35, "k")) == "MsgType (35):k"

    def test_str_unknown_tag(self):
        assert str(Field(1234567890, "k")) == "1234567890:k"

    def test_name_getter(self):
        f = Field(35, "k")
        assert f.name == "MsgType"

    def test_name_getter_custom(self):
        f = Field(1234567890, "k")
        assert f.name == "Unknown"

    def test_raw_getter(self):
        f = Field(35, "k")
        assert f.raw == b"35=k" + settings.SOH

        f = Field(1, None)
        assert f.raw == b"1=" + utils.encode(utils.null) + settings.SOH

    def test_as_str(self):
        f = Field(1, 123)
        assert f.as_str == "123"

    def test_as_int(self):
        f = Field(1, "123")
        assert f.as_int == 123

    def test_as_bool(self):
        true_values = ("y", "yes", "t", "true", "on", "1")
        assert all(Field(1, value).as_bool is True for value in true_values)

        false_values = ("n", "no", "f", "false", "off", "0")
        assert all(Field(1, value).as_bool is False for value in false_values)

    def test_null_valueref_is_converted_to_none(self):
        f = Field(1, utils.null)
        assert f.as_str is None
        assert f.as_int is None
        assert f.as_bool is None

        f = Field(1, str(utils.null))
        assert f.as_str is None
        assert f.as_int is None
        assert f.as_bool is None
