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
from builtins import tuple as _tuple
import collections
from collections import abc
from distutils.util import strtobool

import wtfix.conf.global_settings
from wtfix.core import exceptions
from wtfix.conf import settings
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

        return self._equality_check("eq", other)

    def _equality_check(self, check_method, other):
        comparitor = None
        if isinstance(other, bool):
            comparitor = strtobool(str(self._value))

        elif isinstance(other, bytes):
            comparitor = utils.encode(self._value)

        elif isinstance(other, numbers.Integral):
            try:
                comparitor = int(self._value)
            except ValueError:
                # self._value is not a numbers.Integral
                return False

        elif isinstance(other, FieldValue):
            comparitor = self
            other = other._value

        else:
            comparitor = str(utils.decode(self._value))

        if check_method == "eq":
            check_method = comparitor.__eq__

        elif check_method == "lt":
            check_method = comparitor.__lt__

        elif check_method == "le":
            check_method = comparitor.__le__

        elif check_method == "gt":
            check_method = comparitor.__gt__

        elif check_method == "ge":
            check_method = comparitor.__ge__

        else:
            raise exceptions.ValidationError(
                f"Unknown equality operator '{check_method}'."
            )

        return check_method(other)

    def __lt__(self, other):
        return self._equality_check("lt", other)

    def __le__(self, other):
        return self._equality_check("le", other)

    def __gt__(self, other):
        return self._equality_check("gt", other)

    def __ge__(self, other):
        return self._equality_check("ge", other)

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
                raise exceptions.InvalidField(f"Tag '{tag}' must be an integer.") from e

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
