from ..protocol import base, utils


class InvalidField(Exception):
    pass


class Field:
    """
    Convenience class for dealing with (tag, value) pairs in FieldSets and Messages.

    Performs basic type validation to ensure that fields are well formed.
    """
    UNKNOWN_TAG = "Unknown"

    def __init__(self, *elements):
        """
        :param elements: Can be a (tag, value) tuple, another Field instance, or tag and value arguments.
        NOTE: tags are always stored internally as integers.
        """
        self._tag, self.value = Field.validate(*elements)

    def __iter__(self):
        """
        Iterator over (tag, value) pairs.
        :return: Iterator for the (tag, value) list.
        """
        return iter([self.tag, self.value])

    def __eq__(self, other):
        """
        A Field can be compared to other Fields or to (tag, value) tuples.

        :param other: A Field or (tag, value) tuple
        :return: True if Fields are identical, or if the tuple being compared is equivalent to the Field's
        (tag, value) pair.
        """
        if isinstance(other, self.__class__):
            return self.tag == other.tag and self.value == other.value

        if type(other) is tuple:
            content = list(other)
            return (
                len(content) == 2
                and content[0] == self.tag
                and content[1] == self.value
            )

    def __repr__(self):
        """
        :return: (tag_number, value)
        """
        return f"({self.tag}, {self.value})"

    def __str__(self):
        """
        :return: (tag_name, value) if the tag has been defined in one of the specifications,
        (tag_number, value) otherwise.
        """
        if self.name == self.UNKNOWN_TAG:
            return f"({self.tag}, {self.value})"

        return f"({self.name}, {self.value})"

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, value):
        self._tag = value

    @property
    def name(self):
        """
        :return: The name of the tag as defined in one of the supported specifications, or 'Unknown' otherwise.
        """
        try:
            return base.Tag.get_name(self.tag)
        except base.UnknownTag:
            return self.UNKNOWN_TAG

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val

    @property
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this Field.
        """
        return utils.fix_tag(self.tag) + b"=" + utils.fix_val(self.value) + base.SOH

    @classmethod
    def validate(cls, *elements):
        """
        Checks whether 'elements' can be used to form a valid Field.

        :param elements: a tuple of (tag, value) or two tag, value arguments.
        :return: the verified tag and value pair extracted from elements.
        """
        try:
            tag_, value = list(*elements)
        except (TypeError, ValueError):
            # Not a tuple of (tag, value) pairs, try using arguments as-is
            try:
                tag_, value = elements
            except ValueError:
                raise InvalidField(
                    "'{}' should either consist of a tag / value pair, or "
                    "be a tuple of type (tag, value).".format(*elements)
                )

        return utils.int_val(tag_), value


class GroupIdentifier(Field):
    """
    A special type of Field that is used to identify repeating groups.
    """
    pass
