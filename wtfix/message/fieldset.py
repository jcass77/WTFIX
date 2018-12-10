import collections
import itertools

from wtfix.core.exceptions import TagNotFound, InvalidGroup, UnknownTag, DuplicateTags
from .field import Field
from ..protocol import common


class FieldSet(collections.OrderedDict):
    def __init__(self, *fields):
        """
        A FieldSet is a container for a one or more Fields.

        :param fields: List of Field or (tag, value) tuples.
        """
        super().__init__((field.tag, field) for field in self._parse_fields(fields))

    def __add__(self, other):
        """
        Concatenate two FieldSets, add a Field to a Fieldset, or add a (tag, value) tuple to the FieldSet.

        :param other: Another FieldSet, Field, (tag, value) tuple, or list of these.
        :return: A new FieldSet, which contains the concatenation of the FieldSet with other.
        """
        try:
            return self.__class__(*itertools.chain(self.values(), other.values()))
        except AttributeError:
            # Other is not a valid Fieldset, explode list of fields to construct
            if isinstance(other, tuple):
                other = [other]

            fields = list(self.values()) + other
            return self.__class__(*fields)

    def __len__(self):
        """
        :return: Number of fields in this FieldSet, including all fields in repeating groups.
        """
        length = 0
        for field in self.values():
            length += 1
            if isinstance(field, Group):
                length += (
                    len(field) - 1
                )  # Deduct group identifier field already counted

        return length

    def __getitem__(self, tag):
        """
        Tries to retrieve a Field with the given tag number from this FieldSet.

        Translates 'KeyErrors' into 'TagNotFound' errors.

        :param tag: The tag number of the Field to look up.
        :return: A Field object.
        :raises: TagNotFound if a Field with the specified tag number could not be found.
        """
        try:
            return super().__getitem__(tag)
        except KeyError as e:
            raise TagNotFound(tag, self) from e

    def __setitem__(self, tag, value):
        """
        Sets a Field in the FieldSet with the specified tag number and value..

        :param tag: The tag number to set in the FieldSet.
        :param value: The value of the Field.
        :return:
        """
        if not (isinstance(value, Field) or isinstance(value, Group)):
            # Create a new Field if value is not a Field or Group already.
            value = Field(tag, value)

        return super().__setitem__(tag, value)

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
            tag = common.Tag.get_tag(name)
        except UnknownTag as e:
            # No tag
            raise AttributeError(f"{self.__class__.__name__} instance has no attribute '{name}'.") from e

        try:
            # Then, see if a Field with that tag number is available in this FieldSet.
            return self[tag].value_ref
        except KeyError as e:
            raise TagNotFound(
                tag,
                self,
                f"Tag {tag} not found in {self!r}. Perhaps you are looking"
                f"for a group tag? If so, use 'get_group' instead.",
            ) from e

    def __repr__(self):
        """
        :return: (tag_1, value_1), (tag_2, value_2)
        """
        fields_repr = ""
        for field in self.values():
            fields_repr += f"{repr(field)}, "
        else:
            fields_repr = fields_repr[:-2]

        return f"{fields_repr}"

    def __str__(self):
        """
        :return: (tag_name_1, value_1), (tag_name_2, value_2)
        """
        fields_str = ""
        for field in self.values():
            fields_str += f"{str(field)}, "

        else:
            fields_str = fields_str[:-2]

        return f"{fields_str}"

    @property
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this FieldSet.
        """
        buf = b""
        for field in self.values():
            buf += field.raw

        return buf

    @classmethod
    def _parse_fields(cls, fields):
        """
        Creates a list of Fields from the provided (tag, value) pairs.

        :param fields: Any combination of (tag, value) pairs or other Field objects.
        :return: An list of Fields.
        """
        parsed_fields = []
        tags_seen = set()

        for field in fields:
            # For each field in the fieldset
            if isinstance(field, Field) or isinstance(field, Group):
                # Add field as-is
                if field.tag in tags_seen:
                    raise DuplicateTags(field.tag, *fields)

                parsed_fields.append(field)
                tags_seen.add(field.tag)
                continue

            # Add new field
            if field[0] in tags_seen:
                raise DuplicateTags(field[0], fields)

            parsed_fields.append(
                Field(*field)  # Make sure that this is an actual, well-formed Field.
            )
            tags_seen.add(field[0])

        return parsed_fields

    def get_field(self, item):
        return

    def set_group(self, group):
        """
        Sets the repeating Group of Fields for this FieldSet based on the tag number of the group's identifier Field.

        Overwrites any previous groups with the same tag number.
        :param group: a Group instance.
        :param group: a Group instance.
        """
        self[group.identifier.tag] = group

    def get_group(self, tag):
        """
        Tries to retrieve the Group at the given tag number.
        :param tag: The tag number of the repeating Group's identifier.
        :return: The repeating Group for tag.
        :raises TagNotFound: if the Group does not exist.
        :raises InvalidGroup: if the Field at tag is not a Group instance.
        """
        try:
            group = self[tag]
        except KeyError as e:
            raise TagNotFound(tag, self) from e

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
        self.identifier = Field(*identifier)

        instance_length = (
            len(fields) / self.size
        )  # The number of fields in each group instance

        if not instance_length.is_integer():
            # Not enough fields to construct the required number of group instances
            raise InvalidGroup(
                self.identifier.tag,
                fields,
                f"Not enough fields in {fields} to make {self.size} "
                f"instances that are each {instance_length} fields long.",
            )

        instance_length = int(instance_length)
        for idx in range(0, len(fields), instance_length):  # Loop over group instances
            self.append(GroupInstance(*fields[idx : idx + instance_length]))

    def __len__(self):
        length = 1  # Count identifier field
        for instance in self:
            # Count all fields in each group instance
            length += len(instance)

        return length

    def __repr__(self):
        """
        :return: (identifier tag, num instances):((tag_1, value_1), (tag_2, value_2)), ((tag_1, value_1), (tag_2, value_2))
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
        :return: The value of the identifier Field for this group.
        """
        return self.identifier.value_ref.value

    @property
    def size(self):
        """
        :return: The number of GroupInstances in this group.
        """
        return self.identifier.as_int
