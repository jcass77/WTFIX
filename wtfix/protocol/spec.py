# This file is a part of WTFIX.
#
# Copyright (C) 2018-2020 John Cass <john.cass77@gmail.com>
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

import inspect
from functools import lru_cache

from wtfix.core.exceptions import ValidationError


class Side:
    Buy = "1"
    Sell = "2"


class MetaProtocol(type):
    @property
    def MsgType(cls):
        return cls._msg_types

    @property
    def Tag(cls):
        return cls._tags


class BaseProtocol(metaclass=MetaProtocol):
    """
    The BaseProtocol allows easy access to any MsgTypes and Tags that have been configured for a
    particular protocol specification.
    """

    name = None
    version = None
    _msg_types = None
    _tags = None


class NoneAttribute:
    """
    An attribute stub that always returns 'None'.

    Its main purpose is to replace the 'MsgType' and 'Tag' attributes of stubbed-out protocols at import time.
    """

    def __getattr__(self, item):
        return None


class ProtocolStub:
    """
    The ProtocolStub returns 'None' for any MsgType or Tag lookups.

    It is not of any practical use apart from allowing Python files that contain dynamic protocol references like
    the '@on(connection.protocol.MsgType)' decorator to be imported even if no protocol has been configured.
    """

    name = "Stub"
    version = "none"
    MsgType = NoneAttribute()
    Tag = NoneAttribute()


class AttributeValueMappingsMixin:
    """
    Utility class for doing quick lookups based on class attribute values. This can be used to look up tags or
    message types used in the FIX specification more easily.
    """

    @classmethod
    @lru_cache(maxsize=2)
    def get_attribute_value_mappings(cls):
        """
        Create a reverse mapping of all of the attributes that have been defined in this class.
        """
        attributes = inspect.getmembers(cls, lambda a: not (inspect.isroutine(a)))
        # Skip attributes that start with an underscore
        mappings = {
            attribute[1]: attribute[0]
            for attribute in attributes
            if attribute[0][0] != "_"
        }

        # Won't be able to look up names reliably if duplicate attribute values exist
        if len(mappings.keys()) != len(set(mappings.keys())):
            raise ValidationError(
                "Class attribute values must be unique in order for mapping to be consistent."
            )

        return mappings

    @classmethod
    def get_name(cls, value):
        """
        Given an attribute value, retrieve the attribute name.
        :param value: a class attribute value
        :return: the attribute name corresponding to that value
        """
        return cls.get_attribute_value_mappings()[value]

    @classmethod
    def get_value(cls, name):
        """
        Given a type name, retrieve the corresponding value from the FIX specification.
        :param name: a type name
        :return: the value associated with the type name.
        """
        return cls.__dict__[name]
