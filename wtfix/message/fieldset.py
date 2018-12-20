import abc
import collections
import itertools
import numbers

from wtfix.core.exceptions import (
    TagNotFound,
    InvalidGroup,
    UnknownTag,
    DuplicateTags,
)
from wtfix.core.utils import GroupTemplateMixin
from wtfix.message.field import Field
from wtfix.protocol import common


class FieldSet(abc.ABC):
    """
    A FieldSet is a collection of a one or more Fields. This class provides the interface that all FieldSets
    should implement in order to support the Python builtins that are typically used for collections.
    """
    @abc.abstractmethod
    def __add__(self, other):
        """
        Concatenate two FieldSets, add a Field to a Fieldset, or add a (tag, value) tuple to the FieldSet.

        :param other: Another FieldSet, Field, (tag, value) tuple, or list of these.
        :return: A new FieldSet, which contains the concatenation of the FieldSet with other.
        """

    def __eq__(self, other):
        """
        Compare this FieldSet to other.
        :param other: Another Fieldset, tuple, or list of tuples.
        :return: True if other is equivalent to this FieldSet, False otherwise.
        """
        if len(self) == len(other):
            if isinstance(other, FieldSet):
                return self.fields == other.fields
            if isinstance(other, tuple):
                return all(field in self for field in other)
            if isinstance(other, list):
                return self.fields == other

        return False

    def __len__(self):
        """
        :return: Number of fields in this FieldSet, including all fields in repeating groups.
        """
        return len(self.fields)

    @abc.abstractmethod
    def __setitem__(self, tag, value):
        """
        Sets a Field in the FieldSet with the specified tag number and value..

        :param tag: The tag number to set in the FieldSet.
        :param value: The value of the Field.
        :return:
        """

    @abc.abstractmethod
    def __getitem__(self, tag):
        """
        Tries to retrieve a Field with the given tag number from this FieldSet.

        :param tag: The tag number of the Field to look up.
        :return: A Field object.
        :raises: TagNotFound if a Field with the specified tag number could not be found.
        """

    @abc.abstractmethod
    def __delitem__(self, tag):
        """
        Tries to remove a Field with the given tag number from this FieldSet.

        :param tag: The tag number of the Field to remove.
        :raises: TagNotFound if a Field with the specified tag number could not be found.
        """

    def __contains__(self, tag):
        """
        :return: True if the Fieldset contains a Field with the given tag number, False otherwise.
        """
        if isinstance(tag, numbers.Integral):
            for elem in self.fields:
                if elem[0] == tag:
                    return True

        return False

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
            raise AttributeError(
                f"{self.__class__.__name__} instance has no attribute '{name}'."
            ) from e

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

    @abc.abstractmethod
    def append(self, field):
        """
        Append a field to the FieldSet
        :param field: The Field to append
        :return: a new FieldSet containing field.
        """

    @property
    @abc.abstractmethod
    def fields(self):
        """
        :return: A list of Fields that this FieldSet contains
        """

    @property
    @abc.abstractmethod
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this FieldSet.
        """

    def _repr(self, fields):
        """
        Shared implementation for printing a list of fields
        :param fields: The list of Fields to render
        :return: repr(Field) separated by |
        """
        fields_repr = ""
        for field in fields:
            fields_repr += f"{repr(field)}, "
        else:
            fields_repr = fields_repr[:-2]

        return f"{fields_repr}"

    def _str(self, fields):
        """
        Shared implementation for printing a list of fields
        :param fields: The list of Fields to render
        :return: str(Field) separated by |
        """
        fields_str = ""
        for field in fields:
            fields_str += f"{str(field)} | "

        else:
            fields_str = fields_str[:-3]

        return f"{fields_str}"

    # TODO: cache this result until the message changes.
    def _fields(self, fields):
        """
        Shared implementation for returning a list of all Fields within the FieldSet. Group fields will be
        unpacked into their constituent Fields.
        :param fields: The list of Fields to unpack
        :return: a list of Field instances
        """
        all_fields = []
        for field in fields:
            if isinstance(field, Group):
                all_fields = all_fields + [field.identifier] + field.fields
            else:
                all_fields.append(field)

        return all_fields

    @abc.abstractmethod
    def _parse_fields(cls, fields, **kwargs):
        """
        Creates a list of Fields from the provided (tag, value) pairs.

        :param fields: Any combination of (tag, value) pairs or other Field objects.
        :return: An list of Fields.
        """

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

    def __repr__(self):
        """
        :return: (tag_1, value_1), (tag_2, value_2)
        """

    def __str__(self):
        """
        :return: 'tag_name_1:value_1 | tag_name_2:value_2'
        """


class ListFieldSet(FieldSet):
    def __init__(self, *fields, **kwargs):
        """
        A simple FieldSet that stores all of its Fields in a list.

        This type of FieldSet is easy to instantiate as it does not require any knowledge of the intended
        message structure. The downside is that the internal list structure is not very efficient when it comes
        to performing Field lookups.

        :param fields: List of Field or (tag, value) tuples.
        :param kwargs: Unused.
        """
        self._fields = self._parse_fields(fields)

    def __add__(self, other):
        try:
            return self.__class__(*itertools.chain(self._fields, other.fields))
        except AttributeError:
            # Other is not a valid ListFieldset, explode list of fields to construct
            if isinstance(other, tuple):
                other = [other]
            elif not isinstance(other, list):
                raise TypeError(
                    f"Can only concatenate tuples, lists of tuples, or other Fieldsets, not {type(other).__name__}."
                )

            fields = self._fields + other
            return self.__class__(*fields)

    def __setitem__(self, tag, value):
        if not (isinstance(value, Field) or isinstance(value, Group)):
            # Create a new Field if value is not a Field or Group already.
            value = Field(tag, value)

        if tag in self:
            # Update value, retaining the Field's position in the list
            self._fields = [
                value if field.tag == tag else field for field in self._fields
            ]
        else:
            self._fields.append(value)

        return self

    def __getitem__(self, tag):
        for field in self._fields:
            if field.tag == tag:
                return field

        raise TagNotFound(tag, self)

    def __delitem__(self, tag):
        idx = 0
        for field in self._fields:
            if field.tag == tag:
                del self._fields[idx]
                return
            idx += 1

        raise TagNotFound(tag, self)

    @property
    def fields(self):
        return super()._fields(self._fields)

    @property
    def raw(self):
        buf = b""
        for field in self._fields:
            buf += field.raw

        return buf

    def append(self, field):
        return self.__setitem__(field[0], field[1])

    @classmethod
    def _parse_fields(cls, fields, **kwargs):
        parsed_fields = []
        for field in fields:
            # For each field in the fieldset
            if isinstance(field, Field) or isinstance(field, Group):
                # Add field as-is
                parsed_fields.append(field)
                continue

            # Add new field
            parsed_fields.append(
                Field(*field)  # Make sure that this is an actual, well-formed Field.
            )

        return parsed_fields

    def __repr__(self):
        """
        :return: [(tag_1, value_1), (tag_2, value_2)]
        """
        return f"[{FieldSet._repr(self, self._fields)}]"

    def __str__(self):
        """
        :return: '[tag_name_1:value_1 | tag_name_2:value_2]'
        """
        return f"[{FieldSet._str(self, self._fields)}]"


class OrderedDictFieldSet(FieldSet, GroupTemplateMixin):
    def __init__(self, *fields, **kwargs):
        """
        A FieldSet that stores all of its Fields in an OrderedDict.

        This type of FieldSet should be faster at doing Field lookups and manipulating the FieldSet in general.

        If 'fields' contain one or more repeating groups then you *have* to provide the corresponding repeating group
        template(s) in order for the FieldSet to know how to parse and store those groups.

        :param fields: List of Field or (tag, value) tuples.
        :param kwargs: Should contain a 'group_templates' keyword argument that defines the templates that can be
        used to parse repeating groups in the format group_templates={identifier_tag: [instance_tag_1,..instance_tag_n]}.
        :raises: DuplicateTags if 'fields' contain repeating Fields for which no group_template has been provided.
        """
        group_templates = kwargs.get("group_templates", {})
        if len(group_templates) > 0:
            self.add_group_templates(group_templates)

        self._fields = collections.OrderedDict(
            (field.tag, field) for field in self._parse_fields(fields)
        )

    def __add__(self, other):
        try:
            return self.__class__(*itertools.chain(self._fields.values(), other.fields))
        except AttributeError:
            # Other is not a valid OrderedDictFieldSet, explode list of fields to construct
            if isinstance(other, tuple):
                other = [other]
            elif not isinstance(other, list):
                raise TypeError(
                    f"Can only concatenate tuples, lists of tuples, or other Fieldsets, not {type(other).__name__}."
                )

            fields = list(self._fields.values()) + other
            return self.__class__(*fields)

    def __setitem__(self, tag, value):
        if not (isinstance(value, Field) or isinstance(value, Group)):
            # Create a new Field if value is not a Field or Group already.
            value = Field(tag, value)

        self._fields[tag] = value
        return self

    def __getitem__(self, tag):
        try:
            return self._fields[tag]
        except KeyError as e:
            raise TagNotFound(tag, self) from e

    def __delitem__(self, tag):
        try:
            del self._fields[tag]
        except KeyError:
            raise TagNotFound(tag, self)

    def __contains__(self, tag):
        # Optimization, look for tag in dictionary first
        if isinstance(tag, numbers.Integral):
            if tag in self._fields:
                return True

            # Fallback, might be a group tag - search in list
            return FieldSet.__contains__(self, tag)

        return False

    @property
    def fields(self):
        return super()._fields(list(self._fields.values()))

    @property
    def raw(self):
        buf = b""
        for field in self._fields.values():
            buf += field.raw

        return buf

    def append(self, field):
        return self.__setitem__(field[0], field[1])

    # TODO: refactor and simplify!
    def _parse_fields(self, fields, **kwargs):
        """
        Parses the list of field tuples recursively into Field instances.

        :param fields: A list of (tag, value) tuples
        :return: A list of parsed Field and repeating Group objects.
        :raises: DuplicateTags if 'fields' contain repeating Fields for which no group_template has been provided.
        """
        parsed_fields = []
        tags_seen = set()
        idx = 0
        template = []
        group_index = kwargs.get("group_index", None)

        if group_index is not None:
            # Parsing a repeating group - skip over previously parsed pairs.
            idx = group_index
            group_identifier = Field(fields[idx][0], fields[idx][1])

            # Retrieve the template for this repeating group
            template = self.group_templates[group_identifier.tag]

            # Add the group identifier as the first field in the list.
            parsed_fields.append(group_identifier)
            idx += 1  # Skip over identifier tag that was just processed.

        template_tags = iter(template)

        while idx < len(fields):
            tag, value = fields[idx][0], fields[idx][1]
            tag = int(tag)
            if tag in tags_seen and tag not in template:
                raise DuplicateTags(
                    tag,
                    fields[idx],
                    f"No repeating group template defined for duplicate tag {tag} in {fields}.",
                )

            if tag in self.group_templates:
                # Tag denotes the start of a new repeating group.
                group_fields = self._parse_fields(fields, group_index=idx)
                group = Group(group_fields[0], *group_fields[1:])

                parsed_fields.append(group)
                # Skip over all of the fields that were processed as part of the group.
                idx += len(group)
                continue

            if group_index is not None:
                # Busy parsing a template, see if the current tag forms part of it.
                if tag == next(template_tags):
                    parsed_fields.append(Field(tag, value))
                    if tag == template[-1]:
                        # We've reached the last tag in the template, reset iterator
                        # so that it is ready to parse next group instance (if any).
                        template_tags = iter(template)
                else:
                    # All group fields processed - done.
                    break
            else:
                # Busy parsing a non-group tag.
                parsed_fields.append(Field(tag, value))
                tags_seen.add(tag)

            idx += 1

        return parsed_fields

    def __repr__(self):
        """
        :return: {(tag_1, value_1), (tag_2, value_2)}
        """
        return f"{{{FieldSet._repr(self, self._fields.values())}}}"

    def __str__(self):
        """
        :return: '{tag_name_1:value_1 | tag_name_2:value_2}'
        """
        return f"{{{FieldSet._str(self, self._fields.values())}}}"


class GroupInstance(ListFieldSet):
    """
    A special type of Fieldset used to denote the unique sequence of Fields that form part of a repeating Group.

    All of the fields in the GroupInstance together form one 'instance'.
    """

    pass


class Group:
    """
    A repeating group of GroupInstances that form the Group.
    """

    def __init__(self, identifier, *fields, **kwargs):
        """
        :param identifier: A Field that identifies the repeating Group. The value of the 'identifier' Field
        indicates the number of times that GroupInstance repeats in this Group.
        :param fields: A GroupInstance or list of (tag, value) tuples.
        """
        self._instances = []
        self.identifier = Field(*identifier)

        num_fields = len(fields)

        tags = set()
        for field in fields:
            try:
                tags.add(field[0])
            except TypeError:
                # Must be a nested group, add the identifier's tag.
                tags.add(field.tag)

        instance_length = len(tags)

        if num_fields != (instance_length * self.size):
            # Not enough fields to construct the required number of group instances
            raise InvalidGroup(
                self.identifier.tag,
                fields,
                f"Not enough fields in {fields} to make {self.size} "
                f"instances that are each {instance_length} fields long.",
            )

        instance_length = int(instance_length)
        for idx in range(0, num_fields, instance_length):  # Loop over group instances
            self._instances.append(GroupInstance(*fields[idx : idx + instance_length]))

    def __len__(self):
        length = 1  # Count identifier field
        for instance in self._instances:
            # Count all fields in each group instance
            length += len(instance)

        return length

    def __getitem__(self, item):
        return self._instances[item]

    def __repr__(self):
        """
        :return: [(identifier tag, num instances)]:((tag_1, value_1), (tag_2, value_2)), ((tag_1, value_1), (tag_2, value_2))
        """
        group_instances_repr = ""
        for instance in self._instances:
            group_instances_repr += f"{repr(instance)}, "
        else:
            group_instances_repr = group_instances_repr[:-2]

        return f"[{repr(self.identifier)}]:{group_instances_repr}"

    def __str__(self):
        """
        :return: [identifier_tag_name:num_instances] | tag_1_name:value_1 | tag_2_name:value_2 | tag_1_name:value_1) | tag_2_name:value_2
        """
        group_instances_str = ""
        for instance in self._instances:
            group_instances_str += f"{str(instance)} | "
        else:
            group_instances_str = group_instances_str[:-3]

        return f"[{str(self.identifier)}] | {group_instances_str}"

    @property
    def instances(self):
        """
        :return: A list of GroupInstances that make up this Group.
        """
        return self._instances

    @property
    def fields(self):
        """
        :return: The Fields that are part of this group, including the Fields of any nested sub-Groups.
        """
        group_fields = []
        for instance in self._instances:
            for field in instance.fields:
                group_fields.append(field)

        return group_fields

    @property
    def raw(self):
        """
        :return: The FIX-compliant, raw binary string representation for this Group.
        """
        buf = b""
        for instance in self._instances:
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
