import numbers
from builtins import tuple as _tuple
import collections
from collections import abc
from distutils.util import strtobool

import wtfix.conf.global_settings
import wtfix.core.exceptions
from wtfix.conf import settings
from wtfix.core.exceptions import InvalidField
from ..protocol import common
from wtfix.core import utils


class FieldValue(abc.Sequence):
    """
    Used to store Field values (i.e. strings or bytes). Adds some convenience methods for making comparison
    checks easier.
    """

    def __init__(self, value):
        if utils.is_null(value):
            # Convert FIX negative limit values to Python equivalent (i.e. NoneType).
            value = None

        elif isinstance(value, FieldValue):
            # FieldValues should be terminal nodes - don't wrap FieldValues in other FieldValues
            value = value.value
        elif isinstance(value, bool):
            if value is True:
                value = "Y"
            else:
                value = "N"

        self._value = value

    def __getitem__(self, i: int):
        return self._value[i]

    def __len__(self) -> int:
        return len(self._value)

    def __eq__(self, other):
        """
        Allows comparison against a wide range of other types.

        :param other: The object to compare to.
        :return: If other is a boolean: True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
        are 'n', 'no', 'f', 'false', 'off', and '0'. If other is bytes: compares this FieldValue's decoded
        value with other. If other is str: compares this FieldValues's encoded value with other. Does standard
        comparison of this FieldValue's value against other in all other instances.
        :raises ValueError: if comparison cannot be made.
        """
        if self._value is None:
            return other is None

        if isinstance(other, bool):
            return strtobool(str(self._value)) == other

        if isinstance(other, bytes):
            return utils.encode(self._value) == other

        if isinstance(other, numbers.Integral):
            try:
                return int(self._value) == other
            except ValueError:
                # self._value is not a numbers.Integral
                return False

        return str(utils.decode(self._value)) == other

    def __str__(self):
        """
        :return: The decoded string representation of this FieldValue.
        """
        return str(utils.decode(self._value))

    def __contains__(self, item):
        return item in self._value

    def __iter__(self):
        return iter(self._value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if utils.is_null(value):
            value = None

        self._value = value

    @property
    def raw(self):
        """
        :return: The byte encoded value of this FieldValue
        """
        return utils.encode(self._value)


class Field(collections.namedtuple("Field", ["tag", "value_ref"])):
    """
    A FIX field implemented as a simple (tag, value) namedtuple for use in FieldSets and Messages.
    """

    UNKNOWN_TAG = "Unknown"

    def __new__(_cls, tag: numbers.Integral, value):
        """
        Create new instance of Field(tag, value)

        :param tag: The tag number of the Field. Must be an integer-like number.
        :param value: The tag value.
        :raises InvalidField if the tag is not an integer.
        """
        if not isinstance(tag, numbers.Integral):
            # Tag is not an integer. We might be able to convert it to one if it is
            # a str or bytes.
            try:
                tag = int(tag)
            except ValueError as e:
                raise InvalidField(f"Tag '{tag}' must be an integer.") from e

        return _tuple.__new__(_cls, (tag, FieldValue(value)))

    def __eq__(self, other):
        try:
            # Try to compare as Field
            return self.value_ref == other.value_ref
        except AttributeError:
            # Perhaps it is a tuple?
            if isinstance(other, tuple):
                return self.value_ref == other[1]
            else:
                # Fallback to comparing field values
                return self.value_ref == other

    def __repr__(self):
        """
        :return: (tag number, value)
        """
        return f"({self.tag}, {self.value_ref})"

    def __str__(self):
        """
        :return: 'tag name:value' if the tag has been defined in one of the specifications,
        'tag_number:value' otherwise.
        """
        if self.name == self.UNKNOWN_TAG:
            return f"{self.tag}:{self.value_ref}"

        return f"{self.name} ({self.tag}):{self.value_ref}"

    @property
    def name(self):
        """
        :return: The name of the tag as defined in one of the supported specifications, or 'Unknown' otherwise.
        """
        try:
            return common.Tag.get_name(self.tag)
        except wtfix.core.exceptions.UnknownTag:
            return self.UNKNOWN_TAG

    @property
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this Field.
        """
        return utils.encode(self.tag) + b"=" + self.value_ref.raw + settings.SOH

    @property
    def as_str(self):
        if self.value_ref.value is None:
            return None

        return str(self.value_ref)

    @property
    def as_int(self):
        value = self.as_str

        if value is None:
            return None

        return int(value)

    @property
    def as_bool(self):
        value = self.as_str

        if value is None:
            return None

        return strtobool(self.as_str) == 1
