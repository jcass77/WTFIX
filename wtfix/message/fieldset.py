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

import abc
import collections
import itertools
import numbers

from wtfix.conf import settings
from wtfix.core.exceptions import (
    TagNotFound,
    InvalidGroup,
    UnknownTag,
    DuplicateTags,
    ParsingError,
    ImproperlyConfigured,
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
        Sets a Field in the FieldSet with the specified tag number and value.

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

    def __setattr__(self, key, value):
        """
        Set the value of a Field in a Fieldset

        :param key: The Field's tag name
        :param value: The value to set the Field to
        """
        try:
            tag_num = common.Tag.get_tag(key)
            self[tag_num].value_ref.value = value
        except UnknownTag:
            # Not a known tag number, fall back to default Python implementation
            return super().__setattr__(key, value)
        except TagNotFound:
            # Valid tag, but it has not been added to FieldSet yet - do so now
            self[tag_num] = value

    def __iter__(self):
        """
        Enable iteration over the Fields in a FieldSet
        """
        yield from self.fields

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
            return self[tag]
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

    def get(self, tag, default=None):
        """
        Try to retrieve the given tag from the FieldSet.

        :param tag: The tag value to retrieve.
        :param default: Optional, the default value to use if the tag does not exist in this FieldSet.
        :return: The value of the tag, or the value of default if the tag is not available.
        :raises: TagNotFound if the tag does not exist in the FieldSet and no default value was provided.
        """
        try:
            return self[tag]
        except TagNotFound as e:
            if default is None:
                raise e

            return default

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
        :param kwargs: Can optionally contain a 'group_templates' keyword argument in the format:

            group_templates={identifier_tag: [instance_tag_1,..instance_tag_n]}

        that defines the additional templates that can be used to parse repeating groups. Group templates are
        automatically initialized from the GROUP_TEMPLATES setting.
        :raises: DuplicateTags if 'fields' contain repeating Fields for which no group_template has been provided.
        """
        group_templates = kwargs.get("group_templates", {})
        if len(group_templates) > 0:
            self.group_templates = group_templates

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

    def set_group(self, group):
        # Also add group templates when a new group is set.
        self.add_group_templates({group.identifier.tag: group.template})

        super().set_group(group)

    def _parse_fields(self, fields, **kwargs):
        """
        Parses the list of field tuples recursively into Field instances.

        :param fields: A list of (tag, value) tuples
        :return: A list of parsed Field and repeating Group objects.
        :raises: DuplicateTags if 'fields' contain repeating Fields for which no group_template has been provided.
        """
        parsed_fields = []

        idx = 0
        instance_template = []
        group_index = kwargs.get("group_index", None)
        busy_parsing_group = group_index is not None

        if busy_parsing_group:
            # Retrieve the template for this repeating group
            instance_template = self.group_templates[fields[group_index][0]]
            idx = group_index + 1

        tags_seen = set()

        while idx < len(fields):
            field = fields[idx]

            if type(fields[idx]) is tuple:
                field = Field(*fields[idx])

            if field.tag in tags_seen:
                raise DuplicateTags(
                    field.tag,
                    fields[idx],
                    f"No repeating group template defined for duplicate tag {field.tag} in {fields}.",
                )

            if busy_parsing_group and field.tag not in instance_template:
                # No more group fields to process - done.
                break

            if field.tag in self.group_templates:
                # Tag denotes the start of a new repeating group.
                group_fields = self._parse_fields(fields, group_index=idx)
                group = Group(
                    field, *group_fields, template=self.group_templates[field.tag]
                )

                parsed_fields.append(group)
                # Skip over all of the fields that were processed as part of the group.
                idx += len(group)
                continue

            parsed_fields.append(field)

            if not busy_parsing_group:
                # Busy parsing a non-group tag.
                tags_seen.add(field.tag)

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

    def __init__(self, identifier, *fields, template=None):
        """
        :param identifier: A Field that identifies the repeating Group. The value of the 'identifier' Field
        indicates the number of times that GroupInstance repeats in this Group.
        :param fields: A GroupInstance or list of (tag, value) tuples.
        :param template: Optional. The list of tags that this repeating group consists of. If no template is
        provided then tries to find a template corresponding to identifier.tag in the default GROUP_TEMPLATES setting.
        :raises: ImproperlyConfigured if no template is specified and no template could be found in settings.
        """
        self.identifier = Field(*identifier)
        if template is None:
            try:
                template = settings.default_session.GROUP_TEMPLATES[self.identifier.tag]
            except KeyError:
                raise (
                    ImproperlyConfigured(
                        f"No template available for repeating group identifier {self.identifier}."
                    )
                )

        self._instance_template = template

        self._instances = self._parse_fields(fields)

    def _parse_fields(self, fields, **kwargs):

        parsed_fields = []
        num_fields = len(fields)

        if num_fields == 0 and self.size == 0:
            # Empty group
            return parsed_fields

        instance_tags = set(self._instance_template)
        instance_start = 0
        instance_end = 0

        for field in fields:  # Loop over group instances
            if type(field) is tuple:
                field = Field(*field)

            if field.tag not in instance_tags:
                if field.tag in self._instance_template:
                    # Tag belongs to the next instance. Append the current instance to this group.
                    parsed_fields.append(
                        GroupInstance(*fields[instance_start:instance_end])
                    )

                    instance_start = instance_end
                    instance_tags = set(self._instance_template)

                else:
                    raise ParsingError(
                        f"Unknown tag {field.tag} found while parsing group fields {self._instance_template}."
                    )

            instance_tags.remove(field.tag)
            instance_end += 1

        else:
            # Add last instance
            parsed_fields.append(GroupInstance(*fields[instance_start:instance_end]))

        if len(parsed_fields) != self.size:
            raise InvalidGroup(
                self.identifier.tag,
                fields,
                f"Cannot make {self.size} instances of {self._instance_template} with {fields}.",
            )

        return parsed_fields

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
    def template(self):
        return self._instance_template

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
