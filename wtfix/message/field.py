# This file is a part of WTFIX.
#
# Copyright (C) 2018,2019 John Cass <john.cass77@gmail.com>
#
# WTFIX is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# WTFIX is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numbers
import collections
from distutils.util import strtobool
import operator
from typing import Callable, Union

from wtfix.core import exceptions
from wtfix.conf import settings
from wtfix.core.exceptions import ParsingError
from wtfix.protocol import common
from wtfix.core import utils


class Field(collections.abc.MutableSequence):
    """
    A FIX field representation for use in FieldMaps and Messages.

    We think of fields as simple (tag, value) tuples that have been optimized using __slots__ to ensure
    the smallest possible memory footprint.

    Fields are implemented using the 'unicode sandwich' convention, so if 'value' is a byte sequence
    it will always be decoded to a string when the Field is instantiated.

    Because Fields are essentially just a means for adding a tag number to a Python built-in type, and users will
    usually spend more time manipulating Field values than tags, this class implements a range of operations
    from the standard 'operator' module that can be performed directly on the field's 'value'.

    This makes arithmetic operations on fields a lot simpler:

    >>> from wtfix.message.field import Field
    >>> f = Field(1, 123)
    >>> f == 123
    True
    >>> f + 1
    124
    >>> f += 1
    >>> f
    Field(1, 124)
    """

    UNKNOWN_TAG = "Unknown"

    # Use slots instead of __dict__ for storing instance attributes - more memory efficient.
    __slots__ = ("_tag", "_value", "__weakref__")

    def __init__(
        self,
        tag: Union[numbers.Integral, str, bytes],
        value: Union[numbers.Integral, bool, str, bytes, None],
    ):
        """
        Create new instance of Field(tag, value)

        :param tag: The tag number of the Field. Must be an integer-like object (i.e. an integer, string, or bytes that
        can be converted to an integer).
        :param value: The tag value. Usually one of the built-in Python types.
        :raises InvalidField if 'tag' cannot be converted to an integer.
        """
        self.tag = tag
        self.value = value

    @property
    def tag(self) -> int:
        return self._tag

    @tag.setter
    def tag(self, value: int):

        tag_error_msg = f"Tag '{value}' must be an integer, not {type(value).__name__}."
        if isinstance(value, numbers.Number) and not isinstance(
            value, numbers.Integral
        ):
            # Don't implicitly convert floats or Decimals to tag numbers.
            raise exceptions.InvalidField(tag_error_msg)
        try:
            self._tag = int(value)
        except ValueError as e:
            raise exceptions.InvalidField(tag_error_msg) from e

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value_):
        self._value = utils.decode(value_)

    @property
    def name(self):
        """
        :return: The name of the tag for this Field as defined in one of the supported specifications,
        or 'Unknown' otherwise.
        """
        try:
            return common.Tag.get_name(self.tag)
        except exceptions.UnknownTag:
            return self.UNKNOWN_TAG

    @classmethod
    def _make(cls, iterable) -> "Field":
        """
        Based on namedtuple._make() - creates a new Field from the iterable provided.

        Allows constructing large collections of fields from tuples or lists more easily:

        >>> from wtfix.message.collections import FieldList

        >>> fl = FieldList((1, "abc"), (2, 123))  # <-- More concise than fl = FieldList(Field(1, "abc"), Field(2, 123))
        >>> fl.data
        [Field(1, 'abc'), Field(2, '123')]

        :param iterable: An iterable of length 2
        :return: a new Field instance, with tag = iterable[0] and value = iterable[1]
        :raises: InvalidField if iterable is the wrong length or the (tag, value) pair does not pass validation.
        """
        if len(iterable) != 2:
            raise exceptions.InvalidField(
                f"{cls.__name__} can only be constructed from iterables with length 2."
            )

        return cls(*iterable)

    @classmethod
    def fields_frombytes(cls, octets):
        """
        Parses the raw byte sequence of encoded field pairs into Field instances.

        :param octets: A byte sequence that containing one or more fields in format b'tag=valueSOH'
        :return: A generator of parsed Field objects.
        """
        if octets[-1] != settings.SOH_INT:
            raise ParsingError(
                f"Could not parse {octets} into a new Field: No SOH found at end of byte sequence!"
            )

        # Remove last SOH at end of byte stream and split into fields
        raw_pairs = octets.rstrip(settings.SOH).split(settings.SOH)

        for raw_pair in raw_pairs:
            try:
                tag, value = raw_pair.split(b"=", maxsplit=1)
            except ValueError as e:
                raise ParsingError(f"Could not parse {octets}: {e}.") from e

            yield Field(tag, value)

    @classmethod
    def frombytes(cls, octets):
        """
        Construct a new Field from a byte sequence that represents a single FIX (tag, value) pair.

        :param octets:  A byte sequence that contains exactly one field in format b'tag=valueSOH'
        :return: A newly constructed Field instance.
        :raises: ParsingError if the byte sequence could not be parsed or contains more than one
        encoded fields.
        """
        fields = cls.fields_frombytes(octets)
        field = next(fields)

        try:
            next(fields)
            # Should not reach here - ensures that octets contains only one field
            raise ParsingError(f"Byte sequence {octets} contains more than one field.")

        except StopIteration:
            # Expected - ignore
            pass

        return field

    def _perform_operation(self, operation: Callable, *args, **kwargs):
        """
        Utility method for wrapping arithmetic and other operations so that they can be performed
        directly on this Field's 'value'.

        Allows us to treat a Field as just another a built-in type for most operations:

            a.) if args[0] is a Field or (tag, value) tuple, then convert Field to a tuple and
                make use of the standard operations between two tuples.

                >>> Field(1, "abc") == (1, "abc")  # Equivalent to (1, "abc") == (1, "abc").
                True

                >>> Field(1, "abc") == (2, "abc")
                False

            b.) in all other instances, return the results of performing the operation on this Field's value:

                >>> Field(1, "abc") == "abc"
                True

        :param operation: The operation to perform on the Field. Must be a callable.
        :param args: args will be passed as-is to 'operation'.
        :param kwargs: kwargs will be passed as-is to 'operation'.
        :return: The result of 'operation' applied to the Field or it's value.
        """
        try:
            if args and len(args[0]) == 2 and not isinstance(args[0], str):
                # Sequence with length 2. We create a new, temporary tuple
                # so that we can leverage the standard operators for tuples.
                return operation((self.tag, self.value), *args, **kwargs)
        except TypeError:
            # Not a suitable sequence. Continue processing as-is
            pass

        # If arg is not a tuple, then perform the operation based on this Field's
        # value. Allows us to do quick comparisons like Field(1, "abc") == "abc".
        return operation(self.value, *args, **kwargs)

    def _validated_operand(self, operand: Union["Field", tuple]):
        """
        To perform operations on other Fields, the tags need to match first.

        To perform operations using other tuples, the tuples should be exactly two elements
        long and share a common tag element at index 0.

        :param operand: The Field or tuple that the operation should be performed on.
        :return: The object that the operation should be performed on. Usually a built-in literal.
        """
        if isinstance(operand, str):
            # Always perform operations directly on strings.
            return operand

        try:
            # Check if we are performing the operation on a sequence.
            operand_length = len(operand)
        except TypeError:
            # Cannot be a sequence. Use as-is.
            return operand

        if operand_length == 2 and operand[0] != self.tag:
            raise (
                TypeError(
                    f"Cannot perform arithmetic operation on different tag numbers: "
                    f"{self.tag} and {operand[0]}."
                )
            )
        if operand_length > 2:
            raise (
                TypeError(
                    f"Cannot perform arithmetic operation with {operand} - "
                    f"sequence contains more than 2 elements."
                )
            )

        return operand[1]

    def __len__(self):
        return 2  # A field can only ever consist of a (tag, value) pair

    def __contains__(self, item):
        return self._perform_operation(operator.contains, item)

    def __getitem__(self, item):
        cls = type(self)
        if isinstance(item, slice):  # Slice, return a new Field
            slice_ = (self.tag, self.value)[item]
            return cls(*slice_)

        elif isinstance(item, numbers.Integral):  # int, return element at key
            if item == 0:
                return self.tag
            elif item == 1:
                return self.value
            raise IndexError(f"{cls.__name__} index out of range")
        else:
            raise TypeError(
                f"{cls.__name__} indices must be integers or slices, not {type(item).__name__}."
            )

    def __setitem__(self, key, value):
        if isinstance(key, numbers.Number) and not isinstance(key, numbers.Integral):
            raise TypeError(
                f"{type(self).__name__} indices must be integers, not {type(key).__name__}."
            )

        if isinstance(key, numbers.Integral):
            if key == 0:
                self.tag = value
            elif key == 1:
                self.value = value
            else:
                raise IndexError(f"{type(self).__name__} index out of range")
        else:
            raise TypeError(
                f"{type(self).__name__} indices must be integers, not {type(key).__name__}."
            )

    def __lt__(self, other):
        return self._perform_operation(operator.lt, other)

    def __le__(self, other):
        return self._perform_operation(operator.le, other)

    def __eq__(self, other):
        return self._perform_operation(operator.eq, other)

    def __ne__(self, other):
        return self._perform_operation(operator.ne, other)

    def __ge__(self, other):
        return self._perform_operation(operator.ge, other)

    def __gt__(self, other):
        return self._perform_operation(operator.gt, other)

    def __abs__(self):
        return self._perform_operation(operator.abs)

    def __add__(self, other):
        return self._perform_operation(operator.add, self._validated_operand(other))

    def __floordiv__(self, other):
        return self._perform_operation(
            operator.floordiv, self._validated_operand(other)
        )

    def __invert__(self):
        return self._perform_operation(operator.invert)

    def __lshift__(self, other):
        return self._perform_operation(operator.lshift, self._validated_operand(other))

    def __mod__(self, other):
        return self._perform_operation(operator.mod, self._validated_operand(other))

    def __mul__(self, other):
        return self._perform_operation(operator.mul, self._validated_operand(other))

    def __neg__(self):
        return self._perform_operation(operator.neg)

    def __pos__(self):
        return self._perform_operation(operator.pos)

    def __pow__(self, power, modulo=None):
        return self._perform_operation(operator.pow, self._validated_operand(power))

    def __rshift__(self, other):
        return self._perform_operation(operator.rshift, self._validated_operand(other))

    def __sub__(self, other):
        return self._perform_operation(operator.sub, self._validated_operand(other))

    def __truediv__(self, other):
        return self._perform_operation(operator.truediv, self._validated_operand(other))

    def __iadd__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.add, self._validated_operand(other)),
        )

    def __ifloordiv__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.floordiv, self._validated_operand(other)),
        )

    def __ilshift__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.lshift, self._validated_operand(other)),
        )

    def __imod__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.mod, self._validated_operand(other)),
        )

    def __imul__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.mul, self._validated_operand(other)),
        )

    def __ipow__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.pow, self._validated_operand(other)),
        )

    def __irshift__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.rshift, self._validated_operand(other)),
        )

    def __isub__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.sub, self._validated_operand(other)),
        )

    def __itruediv__(self, other):
        return Field(
            self.tag,
            self._perform_operation(operator.truediv, self._validated_operand(other)),
        )

    def __int__(self):
        """
        :return: the value of this Field cast to an integer.
        """
        try:
            return int(self.value)
        except ValueError:
            # See if this might be a float / decimal encoded as a string
            return int(self.value.split(".")[0])

    def __float__(self):
        """
        :return: the value of this Field cast to a float.
        """
        return float(self.value)

    def __bool__(self):
        """
        :return: the value of this Field cast to a boolean.
        """
        if self.value is None:
            return bool(self.value)

        try:
            return strtobool(str(self)) == 1
        except ValueError:
            return len(self) > 0

    def __bytes__(self):
        """
        Convert this Field to a byte sequence that is ready to be transmitted over the wire.

        :return: The FIX-compliant, raw byte sequence for this Field.
        """
        return utils.encode(self.tag) + b"=" + utils.encode(self.value) + settings.SOH

    def __format__(self, format_spec):
        """
        Introduces the custom format option 't', which adds user-friendly tag names to the output.

        :param format_spec: specification in Format Specification Mini-Language format.
        :return: A formatted string representation this Field.
        """
        if "t" in format_spec:
            if self.name == self.UNKNOWN_TAG:
                return f"{self.tag}: {self.value}"
            return f"{self.name} ({self.tag}): {{:{format_spec.replace('t', '')}}}".format(
                self.value
            )
        else:
            return self.value.__format__(format_spec)

    def __str__(self):
        """
        :return: the value of this Field as a decoded string.
        """
        return str(utils.decode(self.value))

    def __repr__(self):
        """
        :return: 'tag name:value' if the tag has been defined in one of the specifications,
        'tag_number:value' otherwise.
        """
        return f"{type(self).__name__}({self.tag}, '{self.value}')"

    # Unsupported ABC methods.
    insert = None
    __delitem__ = None
