import pytest

from ...protocol import base
from ..field import Field, InvalidField


class TestField:
    def test_iter(self):
        f = Field((1, "a"))

        fi = iter(f)
        assert next(fi) == 1
        assert next(fi) == "a"

        with pytest.raises(StopIteration):
            next(fi)

    def test_eq_field(self):
        f1 = f2 = Field((1, "a"))
        assert f1 == f2

    def test_not_eq_field(self):
        f1 = Field((1, "a"))
        f2 = Field((1, "b"))

        assert f1 != f2

    def test_eq_tuple(self):
        t = (1, "a")
        f = Field(t)
        assert t == f

    def test_repr(self):
        assert repr(Field((35, "k"))) == "(35, k)"

    def test_str(self):
        assert str(Field((35, "k"))) == "(MsgType, k)"

    def test_str_unknown_tag(self):
        assert str(Field((1234567890, "k"))) == "(1234567890, k)"

    def test_tag_getter_int(self):
        assert Field(1, "a").tag == 1

    def test_tag_getter_str(self):
        assert Field("1", "a").tag == 1

    def test_tag_getter_byte(self):
        assert Field("1", "a").tag == 1

    def test_name_getter(self):
        f = Field((35, "k"))
        assert f.name == "MsgType"

    def test_name_getter_custom(self):
        f = Field((1234567890, "k"))
        assert f.name == "Unknown"

    def test_raw_getter(self):
        f = Field((35, "k"))
        assert f.raw == b"35=k" + base.SOH

    def test_validate_tuple(self):
        tag, value = Field.validate((1, "a"))
        assert tag == 1
        assert value == "a"

    def test_validate_args(self):
        tag, value = Field.validate(1, "a")
        assert tag == 1
        assert value == "a"

    def test_validate_field(self):
        tag, value = Field.validate(Field(1, "a"))
        assert tag == 1
        assert value == "a"

    def test_validate_invalid(self):
        with pytest.raises(InvalidField):
            Field.validate("Not a tuple")  # Invalid

        with pytest.raises(InvalidField):
            Field.validate(1, "a", "b")  # Tuple too long
