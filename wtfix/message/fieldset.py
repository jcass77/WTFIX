import collections
import itertools

from .field import Field, GroupIdentifier
from ..protocol.base import Tag, UnknownTag
from ..protocol import utils


class _FieldSetException(Exception):
    """
    Base class for exceptions related issues with the tags in a FieldSet.
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


class FieldSet:
    def __init__(self, *fields):
        """
        A FieldSet is a container for a one or more Fields.

        :param fields: List of Field or (tag, value) tuples.
        """
        self._fields = self._parse_fields(fields)

    def __add__(self, other):
        """
        Concatenate two FieldSets, add a Field to a Fieldset, or add a (tag, value) tuple to the FieldSet

        :return: A new FieldSet, which contains the concatenation of the FieldSet with other.
        """
        if isinstance(other, self.__class__):
            return self.__class__(*itertools.chain(self.fields, other.fields))

        if type(other) is tuple or isinstance(other, Field):
            return self.__class__(*self.fields, other)

    def __eq__(self, other):
        """
        Compares this FieldSet with another FieldSet, or this FieldSet with a list of (tag, value) tuples,
        to see if they are equivalent.

        :param other: The object to compare this FieldSet to. Supported values include FieldSet or a list
        of (tag, value) tuples.
        :return: True if equivalent, False otherwise.
        """
        if type(other) is self.__class__:
            return other._fields == self._fields
        if isinstance(other, list):
            return list(self.fields) == other

    def __iter__(self):
        return iter(self.fields)

    def __getitem__(self, key):
        """
        Return the (tag, value) in key position.

        :param key: position to be extracted.
        :return: a Field consisting of the (key, value) pair if single position, or a new message object
        if a range is given.
        """
        if type(key) is slice:
            return self.__class__(*list(self.fields)[key])

        return list(self.fields)[key]

    def __len__(self):
        """
        :return: Number of fields in message.
        """
        length = 0
        for value in self._fields.values():
            length += 1
            if isinstance(value, Group):
                length += len(value)
                length -= 1  # Deduct group identifier field already counted

        return length

    def __getattr__(self, name):
        """
        Convenience method for retrieving fields using the field name (e.g. field.MsgType will try to
        retrieve tag number 35).

        :param name: The tag name.
        :return: The Field in this FieldSet with name.
        :raises UnknownTag if name is not defined in one of the available FIX specifications.
        :raises TagNotFound if the tag name is valid, but no Field for that tag exists in the FieldSet.
        """
        try:
            # First, try to get the tag number associated with 'name'.
            tag = Tag.get_tag(name)
        except KeyError:
            # Not a known tag, abort
            raise UnknownTag(name)

        try:
            # Then, see if a Field with that tag number is available in this FieldSet.
            return self._fields[tag].value
        except KeyError:
            raise TagNotFound(tag, self, f"Tag {tag} not found in {self!r}. Perhaps you are looking"
                                         f"for a group tag? If so, use 'get_group' instead.")

    def __repr__(self):
        """
        :return: ((tag_1, value_1), (tag_2, value_2))
        """
        fields_repr = ""
        for field in self.fields:
            fields_repr += f"{repr(field)}, "
        else:
            fields_repr = fields_repr[:-2]

        return f"({fields_repr})"

    def __str__(self):
        """
        :return: ((tag_name_1, value_1), (tag_name_2, value_2))
        """
        fields_str = ""
        for field in self.fields:
            fields_str += f"{str(field)}, "

        else:
            fields_str = fields_str[:-2]

        return f"({fields_str})"

    @property
    def fields(self):
        """
        Get all Fields that form part of this FieldSet
        :return: A generator object for Fields.
        """
        return self._fields.values()

    @property
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this FieldSet.
        """
        buf = b""
        for field in self.fields:
            buf += field.raw

        return buf

    @classmethod
    def _parse_fields(cls, fields):
        """
        Turns fields into an ordered dictionary of Fields.

        :param fields: The Fields, or (tag, value) pairs.
        :return: An ordered dictionary of Fields for fields.
        :raises DuplicateTags if a Field for that tag already exists in the FieldSet.
        """
        parsed_fields = collections.OrderedDict()

        for field in fields:
            # For each field in the fieldset
            if isinstance(field, Group):
                # TODO: find a better way of dealing with this. Use singleentry?
                parsed_fields[field.tag] = field
                continue

            field = Field(field)  # Make sure that this is an actual, well-formed Field.

            if field.tag in parsed_fields:
                # Can't have repeating fields outside of a repeating group!
                raise DuplicateTags(field.tag, fields)

            parsed_fields[field.tag] = field

        return parsed_fields

    def get(self, tag, default=None):
        """
        Get the value of the Field with tag number.

        :param tag: tag number.
        :param default: Value to be returned if tag is not found. Must be a binary string.
        :return: The value of the Field in the FieldSet.
        :raises TagNotFound: if not found and default not set.
        """
        try:
            return self._fields[tag].value
        except KeyError:
            # Tag not found, apply default?
            if default is None:
                raise TagNotFound(tag, self)

            return default

    def set_group(self, group):
        """
        Sets the repeating Group of Fields for this FieldSet based on the tag number of the group's identifier Field.

        Overwrites any previous groups with the same tag number.
        :param group: a Group instance.
        :param group: a Group instance.
        """
        self._fields[group.identifier.tag] = group

    def get_group(self, tag):
        """
        Tries to retrieve the Group at the given tag number.
        :param tag: The tag number of the repeating Group's identifier.
        :return: The repeating Group for tag.
        :raises TagNotFound: if the Group does not exist.
        :raises InvalidGroup: if the Field at tag is not a Group instance.
        """
        try:
            group = self._fields[tag]
        except KeyError:
            raise TagNotFound(tag, self)

        if isinstance(group, Group):
            return group
        else:
            raise InvalidGroup(tag, self)


class GroupInstance(FieldSet):
    """
    A special type of Fieldset used to denote the unique sequence of Fields that form part of a repeating Group.

    All of the fields in the GroupInstance together form one 'instance'.
    """
    pass


class Group(collections.UserList):
    """
    A repeating group of GroupInstances that form the Group.
    """
    def __init__(self, identifier, *fields):
        """

        :param identifier: A Field that identifies the repeating Group. The value of the 'identifier' Field
        indicates the number of times that GroupInstance repeats in this Group.
        :param fields: A GroupInstance or list of (tag, value) tuples.
        """
        super().__init__()
        self.identifier = GroupIdentifier(identifier)

        instance_length = len(fields) / self.size  # The number of fields in each group instance

        if not instance_length.is_integer():
            # Not enough fields to construct the required number of group instances
            raise InvalidGroup(self.identifier.tag, fields, f"Not enough fields in {fields} to make {self.size} "
                                                            f"instances that are each {instance_length} fields long.")

        instance_length = int(instance_length)
        for idx in range(0, len(fields), instance_length):  # Loop over group instances
            self.append(GroupInstance(*fields[idx:idx + instance_length]))

    def __len__(self):
        length = 1  # Count identifier field
        for instance in self:
            # Count all fields in each group instance
            length += len(instance)

        return length

    def __repr__(self):
        """
        :return: (identifier_tag, b'num_instances'):((tag_1, value_1), (tag_2, value_2)), ((tag_1, value_1), (tag_2, value_2))
        """
        group_instances_repr = ""
        for instance in self:
            group_instances_repr += f"{repr(instance)}, "
        else:
            group_instances_repr = group_instances_repr[:-2]

        return f"{repr(self.identifier)}:{group_instances_repr}"

    def __str__(self):
        """
        :return: (identifier_tag_name, b'num_instances'):((tag_1_name, value_1), (tag_2_name, value_2)), ((tag_1_name, value_1), (tag_2_name, value_2))
        """
        group_instances_str = ""
        for instance in self:
            group_instances_str += f"{str(instance)}, "
        else:
            group_instances_str = group_instances_str[:-2]

        return f"{str(self.identifier)}:{group_instances_str}"

    @property
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this Group.
        """
        buf = b""
        for instance in self:
            buf += instance.raw

        return self.identifier.raw + buf

    @property
    def tag(self):
        """
        :return: The tag number of the Field that identifies this group.
        """
        return self.identifier.tag

    @property
    def value(self):
        """
        :return: The bytestring value of the identifier Field for this group.
        """
        return self.identifier.value

    @property
    def size(self):
        """
        :return: The number of GroupInstances in this group.
        """
        return utils.int_val(self.value)
