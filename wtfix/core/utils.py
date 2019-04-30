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
from functools import singledispatch

from wtfix.conf import settings
from wtfix.core.exceptions import TagNotFound, ValidationError

null = -2_147_483_648  # FIX representation of 'null' or 'NoneType'


def index_tag(tag, data, start=0):
    """
    Finds a tag in an encoded message byte string.

    :param tag: The tag number to find.
    :param data: The encoded FIX message data to search.
    :param start: Optimization: position at which to start the search.
    :return: A tuple consisting of the tag value, the index at which the tag was found, and the index that
    denotes the end of the field in the byte string.
    :raises: TagNotFound if the tag could not be found in the encoded message data.
    """
    search_bytes = encode(tag) + b"="

    if data.startswith(search_bytes):
        start_of_field = 0
    else:
        # Ensure that the tag is prefixed by SOH to avoid partial matches.
        search_bytes = settings.SOH + search_bytes
        try:
            start_of_field = data.index(search_bytes, start)
        except ValueError as e:
            raise TagNotFound(tag, data) from e

    end_of_field = data.find(settings.SOH, start_of_field + 1)

    return (
        data[start_of_field + len(search_bytes) : end_of_field],
        start_of_field,
        end_of_field,
    )


def rindex_tag(tag, data, start=0):
    """
    Finds a tag in an encoded message byte string, searching from right to left.

    :param tag: The tag number to find.
    :param data: The encoded FIX message data to search.
    :param start: Optimization: position at which to start the search.
    :return: A tuple consisting of the tag value, the index at which the tag was found, and the index that
    denotes the end of the field in the byte string.
    :raises: TagNotFound if the tag could not be found in the encoded message data.
    """
    search_bytes = encode(tag) + b"="
    try:
        start_of_field = data.rindex(search_bytes, start)
    except ValueError as e:
        raise TagNotFound(tag, data) from e

    end_of_field = data.find(settings.SOH, start_of_field + 1)

    return (
        data[start_of_field + len(search_bytes) : end_of_field],
        start_of_field,
        end_of_field,
    )


def calculate_checksum(bytes_):
    """
    Calculates the checksum for bytes_.

    :param bytes_: A string of bytes representing the raw header and body of a FIX message.
    :return: The checksum value calculated over bytes_.
    """
    return sum(bytes_) % 256


@singledispatch
def encode(obj):
    """Encode an object to bytes"""
    if obj is None:
        return encode(null)

    return obj.encode(settings.ENCODING, errors=settings.ENCODING_ERRORS)


@encode.register(numbers.Integral)
def _(n):
    """Encode an numeric value"""
    return encode(str(n))


@encode.register(numbers.Real)
def _(r):
    """Encode a float value"""
    return encode(str(r))


@encode.register(bytes)
def _(b):
    """Bytes are already encoded"""
    return b


@encode.register(bytearray)
def _(ba):
    """Encode a bytearray"""
    return encode(bytes(ba))


@encode.register(bool)
def _(truth):
    """Convert boolean to Y/N"""
    return encode("Y") if truth is True else encode("N")


@singledispatch
def decode(obj):
    """Decode a bytes-like object to string"""
    if obj is None or is_null(obj):
        # Preserve None instead of converting it to the less useful 'None' string.
        return None

    return obj.decode(settings.ENCODING, errors=settings.ENCODING_ERRORS)


@decode.register(str)
def _(string):
    """
    Convert FIX 'null' values to the Python None type, which can be used more easily internally.
    """
    if is_null(string):
        return None

    return string


@decode.register(numbers.Integral)
def _(n):
    """
    Convert FIX 'null' values to the Python None type, which can be used more easily internally.
    """
    if is_null(n):
        return None

    return n


@decode.register(numbers.Real)
def _(r):
    """Floats do not need to be decoded"""
    return r


@singledispatch
def is_null(obj):
    """Return True if obj is equivalent to the FIX null representation (-2_147_483_648), False otherwise."""
    if obj is None:
        return obj


@is_null.register(str)
def _(string):
    return string == str(null)


@is_null.register(numbers.Integral)
def _(n):
    return n == null


@is_null.register(bytes)
def _(b):
    return b == encode(null)


@is_null.register(bytearray)
def _(ba):
    return ba == encode(null)


class GroupTemplateMixin:
    """
    Mixin for maintaining a dictionary of repeating group templates.
    """

    @property
    def group_templates(self):
        """
        :return: The dictionary of group templates that have been added for this object. Initializes the dictionary
        from the GROUP_TEMPLATES setting if it does not exist yet and only one SESSION has been configured.
        """
        try:
            return self._group_templates
        except AttributeError:
            self._init_group_templates()
            return self._group_templates

    @group_templates.setter
    def group_templates(self, value):
        self._group_templates = value

    def _init_group_templates(self):
        if settings.has_safe_defaults:
            self._group_templates = settings.default_connection.GROUP_TEMPLATES
        else:
            self._group_templates = {}

    def add_group_templates(self, templates):
        """
        Performs some basic validation checks when adding additional group templates.

        :param templates: A dictionary of templates in the format {identifier tag: [tag_1,...,tag_n]}
        """
        if len(templates) == 0 or len(list(templates.values())[0]) == 0:
            raise ValidationError(
                f"At least one group instance tag needs to be defined for group {templates}."
            )

        self.group_templates = {**self.group_templates, **templates}

    def remove_group_template(self, identifier_tag):
        """
        Safely remove a group template.

        :param identifier_tag: The identifier tag number of the group that should be removed.
        """
        del self.group_templates[identifier_tag]

    def is_template_tag(self, tag):
        """
        :return: True if the tag occurs in one of the group templates. False otherwise.
        """
        if tag in self.group_templates:
            return True

        for template in self.group_templates.values():
            return tag in template
