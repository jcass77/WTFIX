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
    pass


class StopMessageProcessing(Exception):
    pass


class InvalidMessage(Exception):
    pass


class SignalStop(Exception):
    pass


class WaitTimeout(BaseException):
    pass


class InvalidField(Exception):
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


class InvalidGroup(_TagException):
    def __init__(self, tag, data, message=None):
        if message is None:
            message = f"{tag} is not a group tag in {data!r}."
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
