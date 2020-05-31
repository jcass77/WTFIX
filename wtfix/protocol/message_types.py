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

from wtfix.core.exceptions import UnknownType
from wtfix.protocol.spec import AttributeValueMappingsMixin


class _BaseMsgType(AttributeValueMappingsMixin):
    """
    This class contains all of the message type definitions that are available for the supported protocol.

    It is intended to be accessed dynamically via the pipeline instead of directly.
    """

    @classmethod
    def get_name(cls, value):
        """Wrapper for backwards compatibility"""
        try:
            return super().get_name(value)
        except KeyError as e:
            # Not a known type
            raise UnknownType(value) from e

    @classmethod
    def get_type(cls, type_name):
        """Wrapper for backwards compatibility"""
        try:
            return super().get_value(type_name)
        except KeyError as e:
            # Not a known tag
            raise UnknownType(type_name) from e
