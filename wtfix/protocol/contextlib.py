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
from contextlib import contextmanager

from wtfix.conf import settings
from wtfix.core.klass import get_class_from_module_string
from wtfix.protocol.spec import ProtocolStub


class Singleton(type):
    """
    Meta class for creating and accessing a singleton instance.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            # Always re-initialize the class when it is accessed.
            cls._instances[cls].__init__(*args, **kwargs)

        return cls._instances[cls]


class ConnectionContext(metaclass=Singleton):
    """
    The ConnectionContext is used to keep track of the active connection and its associated protocol.
    """

    def __init__(self, name=None):
        self._name = name or "default"
        self._protocol = None  # Reset protocol every time name is changed.

    @property
    def name(self):
        return self._name

    @property
    def protocol(self):
        if self._protocol is None:
            try:
                self._protocol = get_class_from_module_string(
                    settings.CONNECTIONS[self._name]["PROTOCOL"]
                )
            except KeyError:
                return ProtocolStub  # Return a stub so long, in the hope that the connection will eventually be set.

        return self._protocol


connection = ConnectionContext()


@contextmanager
def connection_manager(name=None):
    # Context manager for switching between connections and protocols.
    prev_name = connection.name

    yield ConnectionContext(name)

    _ = ConnectionContext(prev_name)  # Revert to previous connection context
