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


class _FieldSetException(Exception):
    """
    Base class for exceptions that are related to issues with the tags in a FieldSet.
    """

    def __init__(self, tag, fieldset, message):
        self.tag = tag
        self.fieldset = fieldset
        super().__init__(tag, fieldset, message)


class TagNotFound(_FieldSetException):
    def __init__(self, tag, fieldset, message=None):
        if message is None:
            message = f"Tag {tag} not found in {fieldset!r}."
        super().__init__(tag, fieldset, message)


class DuplicateTags(_FieldSetException):
    def __init__(self, tag, fieldset, message=None):
        if message is None:
            message = f"Tag {tag} repeated in {fieldset!r}."
        super().__init__(tag, fieldset, message)


class InvalidGroup(_FieldSetException):
    def __init__(self, tag, fieldset, message=None):
        if message is None:
            message = f"{tag} is not a group tag in {fieldset!r}."
        super().__init__(tag, fieldset, message)


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
