import pytest

from ...protocol import base
from ..field import Field, InvalidField


class TestField:
    def test_iter(self):
        f = Field((1, b"a"))

        fi = iter(f)
        assert next(fi) == 1
        assert next(fi) == b"a"

        with pytest.raises(StopIteration):
            next(fi)

    def test_eq_field(self):
        f1 = f2 = Field((1, b"a"))
        assert f1 == f2

    def test_not_eq_field(self):
        f1 = Field((1, b"a"))
        f2 = Field((1, b"b"))

        assert f1 != f2

    def test_eq_tuple(self):
        t = (1, b"a")
        f = Field(t)
        assert t == f

    def test_repr(self):
        assert repr(Field((35, b"k"))) == "(35, b'k')"

    def test_str(self):
        assert str(Field((35, b"k"))) == "(MsgType, b'k')"

    def test_str_unknown_tag(self):
        assert str(Field((1234567890, b"k"))) == "(1234567890, b'k')"

    def test_tag_getter_int(self):
        assert Field(1, b"a").tag == 1

    def test_tag_getter_str(self):
        assert Field("1", b"a").tag == 1

    def test_tag_getter_byte(self):
        assert Field(b"1", b"a").tag == 1

    def test_name_getter(self):
        f = Field((35, b"k"))
        assert f.name == "MsgType"

    def test_name_getter_custom(self):
        f = Field((1234567890, b"k"))
        assert f.name == "Unknown"

    def test_raw_getter(self):
        f = Field((35, b"k"))
        assert f.raw == b"35=k" + base.SOH

    def test_validate_tuple(self):
        tag, value = Field.validate((1, b"a"))
        assert tag == 1
        assert value == b"a"

    def test_validate_args(self):
        tag, value = Field.validate(1, b"a")
        assert tag == 1
        assert value == b"a"

    def test_validate_field(self):
        tag, value = Field.validate(Field(1, b"a"))
        assert tag == 1
        assert value == b"a"

    def test_validate_invalid(self):
        with pytest.raises(InvalidField):
            Field.validate("Not a tuple")  # Invalid

        with pytest.raises(InvalidField):
            Field.validate(1, b"a", b"b")  # Tuple too long

        with pytest.raises(InvalidField):
            Field.validate(1, u"a")  # Value is not a bytestring

        with pytest.raises(InvalidField):
            Field.validate(1, 2)  # Value is not a bytestring

        with pytest.raises(InvalidField):  # Value has a 1 separator value in it
            Field.validate(1, b"a" + base.SOH)
