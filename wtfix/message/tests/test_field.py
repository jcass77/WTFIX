import copy
from decimal import Decimal

import pytest

from wtfix.conf import settings
from wtfix.core import utils
from ..field import Field
from wtfix.core.exceptions import InvalidField, ParsingError


class TestField:
    def test_constructing_with_string_tag_that_cannot_be_converted_to_int_raises_exception(
        self,
    ):
        with pytest.raises(InvalidField):
            Field("abc", "k")

    def test_can_construct_with_integer_tag_in_string_format(self):
        f = Field("1", "k")
        assert f.tag == 1

    def test_can_construct_with_tag_in_bytes_format(self):
        f = Field(b"1", "k")
        assert f.tag == 1

    def test_constructing_with_float_tag_raises_exception(self):
        with pytest.raises(InvalidField):
            Field(1.23, "k")

    def test_constructing_with_decimal_tag_raises_exception(self):
        with pytest.raises(InvalidField):
            Field(Decimal(1.23), "k")

    def test_constructing_with_more_than_two_parameters_raises_exception(self):
        with pytest.raises(TypeError):
            Field(1, 2, 3)

    def test_constructing_with_fix_null_value(self):
        assert Field(1, utils.encode(utils.null)) == None  # noqa
        assert Field(1, utils.encode(utils.null)).value is None

        assert Field(1, utils.null) == None  # noqa
        assert Field(1, utils.null).value is None

        assert Field(1, str(utils.null)) == None  # noqa
        assert Field(1, str(utils.null)).value is None

        assert Field(1, None) == None  # noqa
        assert Field(1, None).value is None

    def test_can_construct_from_dictionary(self):
        f = Field(**{"tag": 1, "value": "k"})
        assert f.tag == 1
        assert str(f) == "k"

    def test_tag_setter_wrong_numeric_type_raises_exception(self):
        f = Field(1, "abc")
        with pytest.raises(InvalidField):
            f.tag = 1.0
        with pytest.raises(InvalidField):
            f.tag = "1.0"

    def test_tag_setter_cannot_cast_to_numeric_type_raises_exception(self):
        with pytest.raises(InvalidField):
            f = Field(1, "abc")
            f.tag = "a"

    def test_value_setter_decodes_values(self):
        f = Field(1, "abc")
        f.value = b"def"

        assert f.value == "def"

    def test_value_setter_preserves_no_byte_types(self):
        f = Field(1, "abc")
        f.value = 123

        assert type(f[1]) == int

    def test_name_getter(self):
        f = Field(35, "k")
        assert f.name == "MsgType"

    def test_name_getter_unknown(self):
        f = Field(1234567890, "k")
        assert f.name == Field.UNKNOWN_TAG

    def test_make_from_iterable(self):
        assert Field._make([1, "abc"]) == Field(1, "abc")
        assert Field._make((1, "abc")) == Field(1, "abc")

    def test_make_from_iterable_iterable_wrong_length_raises_exception(self):
        with pytest.raises(InvalidField):
            Field._make((1, "abc", "def"))

    def test_fields_frombytes(self):
        f1 = Field(1, "abc")
        byte_sequence = bytes(f1)

        f2 = next(Field.fields_frombytes(byte_sequence))

        assert f2 == f1
        assert type(f2) is Field

        assert next(Field.fields_frombytes(b"1234=abcdef" + settings.SOH)) == (
            1234,
            "abcdef",
        )

    def test_fields_frombytes_complex(self):
        # Split a long byte string into fields
        raw_msg = b"8=FIX.4.4\x019=3589\x0135=W\x0134=44\x0149=market_data\x0152=20181214-14:04:51.228\x0156=J_TRADER\x0148=1000000058\x01262=0\x01263=h\x01267=1\x01269=h\x01268=168\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=11:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=12:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=13:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=14:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=15:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=16:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=17:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=18:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=19:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=20:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=21:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=22:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181213\x01273=23:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=01:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=02:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=03:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=04:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=05:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=06:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=07:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=08:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=09:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=11:00:00\x01269=4\x01270=-2147483648\x01269=7\x01270=-2147483648\x01269=8\x01270=-2147483648\x01269=5\x01270=-2147483648\x01269=B\x01270=0\x01269=v\x01270=0\x01269=s\x01272=20181214\x01273=12:00:00\x019960=1\x019961=1\x0110046=100\x0110=126\x01"  # noqa
        fields = Field.fields_frombytes(raw_msg)
        assert len(list(fields)) == 377

    def test_fields_frombytes_no_equals_raises_exception(self):
        with pytest.raises(ParsingError):
            next(Field.fields_frombytes(b"1abc" + settings.SOH))

    def test_frombytes_no_soh_raises_exception(self):
        with pytest.raises(ParsingError):
            next(Field.fields_frombytes(b"1=abc"))

    def test_frombytes_multiple_fields_raises_exception(self):
        with pytest.raises(ParsingError):
            Field.frombytes(b"1=abc" + settings.SOH + b"2=def" + settings.SOH)

    def test_len(self):
        assert len(Field(1, "abc")) == 2

    def test_contains(self):
        assert "a" in Field(1, "abc")
        assert "a" in Field(1, b"abc")

    def test_getitem_slice_returns_new_field(self):
        f = Field(1, "abc")
        slice_ = f[:]

        assert type(slice_) is Field
        assert slice_ == Field(1, "abc")
        assert id(f) != id(slice_)

    def test_getitem_int_0_returns_tag(self):
        f = Field(1, "abc")
        assert f[0] is f.tag == 1  # noqa

    def test_getitem_int_1_returns_value(self):
        f = Field(1, "abc")
        assert f[1] is f.value == "abc"  # noqa

    def test_getitem_index_out_of_bounds_raises_exception(self):
        with pytest.raises(IndexError):
            f = Field(1, "abc")
            f[3]

    def test_getitem_wrong_index_type_raises_exception(self):
        with pytest.raises(TypeError):
            f = Field(1, "abc")
            f[1.0]

    def test_setitem_int_0_sets_tag(self):
        f = Field(1, "abc")
        f[0] = 2
        assert f[0] is f.tag == 2  # noqa

    def test_setitem_int_1_sets_value(self):
        f = Field(1, "abc")
        f[1] = "def"
        assert f[1] is f.value == "def"  # noqa

    def test_setitem_index_out_of_bounds_raises_exception(self):
        with pytest.raises(IndexError):
            f = Field(1, "abc")
            f[3] = "def"

    def test_setitem_wrong_index_type_raises_exception(self):
        with pytest.raises(TypeError):
            f = Field(1, "abc")
            f[1.0] = "def"

    # -- NOTE: these tests confirm that implicit Python standard operations are still supported.
    def test_copy(self):
        f1 = Field(1, "abc")
        f2 = copy.copy(f1)
        f3 = f1[:]

        assert f3 == f2 == f1
        assert id(f3) != id(f2) != id(f1)

    def test_unpack_to_tuple(self):
        tag, value = Field(1, "abc")

        assert tag == 1
        assert value == "abc"

    def test_iter(self):
        f = Field(1, "abc")
        assert next(iter(f)) == 1

    def test_null_value_casting(self):
        assert Field(1, utils.null) == None  # noqa
        assert Field(1, str(utils.null)) == None  # noqa
        assert Field(1, utils.encode(utils.null)) == None  # noqa

    def test_deletion_raises_exception(self):
        with pytest.raises(TypeError):
            f = Field(1, "abc")
            del f[0]

    def test_insertion_raises_exception(self):
        with pytest.raises(TypeError):
            f = Field(1, "abc")
            f.insert(1, "abc")

    # --- NOTE: All of the 'compare' methods below are proxies for testing _validated_operand ---
    def test_implicit_type_conversion(self):
        f = Field(1, "abc")
        assert f == "abc"

        assert f[0] == 1  # noqa
        assert f[1] == "abc"  # noqa

    def test_compare_field_true(self):
        assert Field(1, "abc") == Field(1, "abc")
        assert Field(1, b"abc") == Field(1, "abc")
        assert Field(1, "abc") == Field(1, b"abc")
        assert Field(1, b"abc") == Field(1, b"abc")

        assert Field(1, 2) == Field(1, 2)

    def test_compare_tuple_true(self):
        assert Field(1, "abc") == (1, "abc")
        assert Field(1, b"abc") == (1, "abc")
        assert Field(1, "abc") == tuple([1, "abc"])

    def test_ne_tuple_different_lengths_cannot_be_equal(self):
        assert Field(1, "abc") != (1, "abc", "xyz")

    def test_compare_str_value_true(self):
        # Strings
        assert Field(1, "a") == "a"
        assert Field(1, b"a") == "a"
        assert str(Field(1, 2)) == "2"

    def test_compare_int_value_true(self):
        # Integers
        assert Field(1, 2) == 2
        assert int(Field(1, "2")) == 2
        assert int(Field(1, b"2")) == 2

    def test_compare_bool_value_true(self):
        # Boolean
        assert Field(1, True) == True  # noqa
        assert bool(Field(1, b"Y")) == True  # noqa
        assert bool(Field(1, "Y")) == True  # noqa

    def test_compare_str_value_false(self):
        # Strings
        assert Field(1, "a") != b"a"
        assert Field(1, b"a") != b"a"
        assert Field(1, 2) != "2"

    def test_compare_int_value_false(self):
        # Integers
        assert Field(1, "2") != 2
        assert Field(1, b"2") != 2
        assert Field(1, b"2") != b"2"

    def test_compare_bool_value_false(self):
        # Boolean
        assert Field(1, b"Y") != True  # noqa
        assert Field(1, "Y") != True  # noqa
        assert Field(1, True) != "Y"
        assert Field(1, True) != b"Y"
        assert Field(1, b"Y") != b"Y"
        assert Field(1, b"Y") != "True"

    def test_compare_boolean_str_values_true(self):
        true_vals = ("y", "yes", "t", "true", "on", "1")
        assert all(bool(Field(1, value)) == True for value in true_vals)  # noqa

        false_vals = ("n", "no", "f", "false", "off", "0")
        assert all(bool(Field(1, value)) == False for value in false_vals)  # noqa

    def test_compare_boolean_str_values_false(self):
        true_vals = ("y", "yes", "t", "true", "on", "1")
        assert all(bool(Field(1, value)) != False for value in true_vals)  # noqa

        false_vals = ("n", "no", "f", "false", "off", "0")
        assert all(bool(Field(1, value)) != True for value in false_vals)  # noqa

    def test_abs(self):
        assert abs(Field(1, -123)) == 123
        assert abs(Field(1, -123)) == 123

    def test_arithmetic_tuple_longer_than_2_raises_exception(self):
        with pytest.raises(TypeError):
            Field(1, "abc") + (1, "abc", "def")

    def test_arithmetic_tuple_different_tags_raises_exception(self):
        with pytest.raises(TypeError):
            Field(1, "abc") + Field(2, "def")

        with pytest.raises(TypeError):
            Field(1, "abc") + (2, "def")

    def test_arithmetic_literal(self):
        assert Field(1, "abc") + "def" == "abcdef"
        assert Field(1, 10) + 10 == 20

    def test_iarithmetic_literal(self):
        f = Field(1, "abc")
        f += "def"

        assert f == Field(1, "abcdef")
        assert f == (1, "abcdef")

    def test_arithmetic_field(self):
        assert Field(1, "abc") + Field(1, "def") == "abcdef"

    def test_iarithmetic_field(self):
        f = Field(1, "abc")
        f += Field(1, "def")

        assert f == Field(1, "abcdef")
        assert f == (1, "abcdef")

    def test_arithmetic_tuple(self):
        assert Field(1, "abc") + (1, "def") == "abcdef"
        assert Field(1, "abc") + (1, "def") == "abcdef"

    def test_iarithmetic_tuple(self):
        f = Field(1, "abc")
        f += (1, "def")

        assert f == Field(1, "abcdef")
        assert f == (1, "abcdef")

    def test_unsupported_set_operations_raises_exception(self):
        with pytest.raises(TypeError):
            Field(1, "abc") & Field(1, "abc")

        with pytest.raises(TypeError):
            Field(1, "abc") | Field(1, "abc")

        with pytest.raises(TypeError):
            Field(1, "abc") - Field(1, "abc")

    def test_add(self):
        assert Field(1, 2) + Field(1, 3) == 5
        assert Field(1, 2) + (1, 3) == 5
        assert Field(1, 2) + 3 == 5

    def test_floor_div(self):
        assert Field(1, 2.2) // Field(1, 2) == 1.0
        assert Field(1, 2.2) // Field(1, 2) == 1.0
        assert Field(1, 2.2) // 2 == 1.0

    def test_invert(self):
        assert ~Field(1, 123) == ~123

    def test_lshift(self):
        assert Field(1, 123) << Field(1, 1) == 246
        assert Field(1, 123) << (1, 1) == 246
        assert Field(1, 123) << 1 == 246

    def test_mod(self):
        assert Field(1, 123) % Field(1, 2) == 1
        assert Field(1, 123) % (1, 2) == 1
        assert Field(1, 123) % 2 == 1

    def test_mul(self):
        assert Field(1, 123) * Field(1, 2) == 246
        assert Field(1, 123) * (1, 2) == 246
        assert Field(1, 123) * 2 == 246

    def test_neg(self):
        assert -Field(1, 123) == -123

    def test_pos(self):
        assert +Field(1, -123) == -123

    def test_pow(self):
        assert Field(1, 123) ** Field(1, 2) == 15129
        assert Field(1, 123) ** (1, 2) == 15129
        assert Field(1, 123) ** 2 == 15129

    def test_rshift(self):
        assert Field(1, 123) >> Field(1, 1) == 61
        assert Field(1, 123) >> (1, 1) == 61
        assert Field(1, 123) >> 1 == 61

    def test_sub(self):
        assert Field(1, 5) - Field(1, 3) == 2
        assert Field(1, 5) - (1, 3) == 2
        assert Field(1, 5) - 3 == 2

    def test_truediv(self):
        assert Field(1, 4) / Field(1, 2) == 2
        assert Field(1, 4) / (1, 2) == 2
        assert Field(1, 4) / 2 == 2

    def test_iadd_raises_exception(self):
        f = Field(1, "abc")
        f += "xyz"
        assert f == Field(1, "abcxyz")

    def test_ifloordiv_raises_exception(self):
        f = Field(1, 132)
        f //= 2
        assert f == Field(1, 66)

    def test_ilshift_raises_exception(self):
        f = Field(1, 132)
        f <<= 1
        assert f == Field(1, 264)

    def test_imod_raises_exception(self):
        f = Field(1, 132)
        f %= 2
        assert f == Field(1, 0)

    def test_imul_raises_exception(self):
        f = Field(1, 132)
        f *= 2
        assert f == Field(1, 264)

    def test_ipow_raises_exception(self):
        f = Field(1, 132)
        f **= 2
        assert f == Field(1, 17424)

    def test_irshift_raises_exception(self):
        f = Field(1, 132)
        f >>= 2
        assert f == Field(1, 33)

    def test_isub_raises_exception(self):
        f = Field(1, 132)
        f -= 2
        assert f == Field(1, 130)

    def test_itruediv_raises_exception(self):
        f = Field(1, 132)
        f /= 2
        assert f == Field(1, 66)

    def test_int(self):
        f = Field(1, "123")
        assert int(f) == 123

    def test_int_decimal(self):
        f = Field(1, 123.456)
        assert int(f) == 123

    def test_int_decimal_string(self):
        f = Field(1, "123.456")
        assert int(f) == 123

    def test_int_decimal_string_not_a_number(self):
        with pytest.raises(ValueError):
            f = Field(1, "abc")
            int(f)

    def test_float(self):
        f = Field(1, "123.45")
        assert float(f) == 123.45

    def test_bool_converts_strings_to_bool(self):
        true_values = ("y", "yes", "t", "true", "on", "1")
        assert all(bool(Field(1, value)) is True for value in true_values)

        false_values = ("n", "no", "f", "false", "off", "0")
        assert all(bool(Field(1, value)) is False for value in false_values)

    def test_bool_none_is_false(self):
        assert bool(Field(1, None)) is False

    def test_bytes_encodes_field(self):
        f = Field(35, "k")
        assert bytes(f) == b"35=k" + settings.SOH

    def test_bytes_encodes_field_bool_true(self):
        f = Field(1, True)
        assert bytes(f) == b"1=Y" + settings.SOH

    def test_bytes_encodes_field_bool_false(self):
        f = Field(1, False)
        assert bytes(f) == b"1=N" + settings.SOH

    def test_bytes_converts_none_to_null(self):
        f = Field(1, None)
        assert bytes(f) == b"1=" + utils.encode(utils.null) + settings.SOH

    def test_format_value(self):
        assert "{:s}".format(Field(35, "k")) == "k"

    def test_format_pretty_print_tags(self):
        assert "{:t}".format(Field(35, "k")) == "MsgType (35): k"

    def test_format_pretty_print_tags_multiple_options(self):
        assert "{:t0.2f}".format(Field(35, 123)) == "MsgType (35): 123.00"

    def test_format_unknown(self):
        assert "{:t}".format(Field(1234567890, "k")) == "1234567890: k"

    def test_str(self):
        assert str(Field(35, "k")) == "k"

    def test_repr_output(self):
        f = Field(35, "k")
        assert repr(f) == "Field(35, 'k')"

    def test_repr_eval(self):
        f = Field(35, "k")
        assert eval(repr(f)) == f
