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

"""
Global wtfix exceptions and warning classes.
"""


class ImproperlyConfigured(Exception):
    """wtfix is somehow improperly configured"""

    pass


class ParsingError(Exception):
    pass


class ValidationError(Exception):
    pass


class MessageProcessingError(Exception):
    """
    Used to signal an abnormal interrupt while a message is being processed. This exception will not cause the
    pipeline to be stopped and the default implementation will just log the error before proceeding to the next
    message.
    """

    pass


class StopMessageProcessing(Exception):
    """
    Used to stop a message from propagating further up or down the pipeline.

    This should be used to interrupt message processing during normal operation (i.e. as part of an optimization
    or if the message is not relevant to other applications in the pipeline.
    """

    pass


class InvalidField(Exception):
    pass


class SessionError(Exception):
    """
    Fatal session error from which no recovery is possible. A SessionError exception won't be handled by the
    pipeline and will cause an abnormal termination.
    """

    pass


class _TagException(Exception):
    """
    Base class for exceptions that are related to issues with tags.
    """

    def __init__(self, tag, data, message):
        self.tag = tag
        self.data = data
        super().__init__(tag, data, message)


class TagNotFound(_TagException):
    def __init__(self, tag, data, message=None):
        if message is None:
            message = f"Tag {tag} not found in {data!r}."
        super().__init__(tag, data, message)


class DuplicateTags(_TagException):
    def __init__(self, tag, data, message=None):
        if message is None:
            message = f"Tag {tag} repeated in {data!r}."
        super().__init__(tag, data, message)


class UnknownType(Exception):
    def __init__(self, type_):
        self.type_ = type_

        super().__init__(
            f"Type '{type_}' not found in any of the supported FIX specifications."
        )


class UnknownTag(Exception):
    def __init__(self, tag):
        self.tag = tag

        super().__init__(
            f"Tag '{tag}' not found in any of the supported FIX specifications."
        )
