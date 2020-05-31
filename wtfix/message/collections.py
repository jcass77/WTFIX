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

import abc
import collections
import itertools
from typing import Union, Sequence, Generator

from wtfix.core.exceptions import TagNotFound, UnknownTag, DuplicateTags, ParsingError
from wtfix.core.utils import GroupTemplateMixin
from wtfix.message.field import Field
from wtfix.protocol.contextlib import connection


class FieldMap(collections.abc.MutableMapping, abc.ABC):
    """
    A FieldMap is a collection of a one or more Fields.

    Implementations of FieldMap should accept one or more Fields, or (tag, value) tuples, to construct the sequence,
    and then allow looking up Fields by their tag numbers:

    >>> fm = FieldDict((123, "abc"), (346, 789))
    >>> fm[123]
    Field(123, 'abc')

    How the Fields are actually stored is an implementation detail, but all FieldMaps should expose the underlying
    data store via the 'data' attribute:

    >>> fm.data
    OrderedDict([(123, Field(123, 'abc')), (346, Field(346, '789'))])

    See https://docs.python.org/3/reference/datamodel.html?highlight=__add__#emulating-container-types for a list
    of methods that should be implemented in order to emulate Python's built-in container types.
    """

    @property
    @abc.abstractmethod
    def data(self):
        """
        Provide direct access to this FieldMap's container, similar to UserDict and UserList.

        :return: The underlying container that this FieldMap's Fields are stored in.
        """

    @classmethod
    def as_sequence(
        cls, other: Union["FieldMap", Field, tuple, Sequence[Field], Sequence[tuple]]
    ) -> Union[Sequence, Generator[Field, None, None]]:
        """
        :return: wrap other in tuple to create a Sequence, if required
        """
        try:
            return other.values()
        except AttributeError:
            # Not a FieldMap
            try:
                if len(other[0]) > 0:
                    # Might be a valid sequence - use as-is.
                    return other
            except TypeError:
                # Convert to tuple
                try:
                    return (other,)
                except TypeError:
                    raise ParsingError(
                        f"Cannot process '{other}': not a valid (tag, value) pair."
                    )

    def __add__(
        self, other: Union["FieldMap", Field, tuple, Sequence[Field], Sequence[tuple]]
    ) -> "FieldMap":
        """
        Add another FieldMap to this FieldMap, or add a Field or a (tag, value) tuple or Sequences of these
        to the FieldMap.

        :param other: Another FieldMap, Field, (tag, value) tuple, or Sequence of these.
        :return: A new FieldMap, which contains the concatenation of the FieldMap with other.
        """
        return self.__class__(*itertools.chain(self.values(), self.as_sequence(other)))

    def _compare_fields(self, other_sequence):

        try:
            if not all(
                len(field) == 2 and type(field[0]) is int for field in other_sequence
            ):
                # Value being compared to must be a tuple of (tag, value) pairs.
                return False

            # Sort the sequences to be compared so that we can perform an unordered comparison
            for other_field, self_field in itertools.zip_longest(
                sorted(other_sequence), sorted(list(self.values()))
            ):
                # Compare tags and string-converted values one by one.
                if self_field.tag != other_field[0] or str(self_field.value) != str(
                    other_field[1]
                ):
                    return False

        except (TypeError, AttributeError):
            # Values cannot be compared.
            return False

        return True

    def __eq__(
        self, other: Union["FieldMap", Sequence[Field], Sequence[tuple]]
    ) -> bool:
        """
        Compare this FieldMap to other.

        Since the order in which fields appear in a FIX message is usually not significant, the field order is ignored
        when doing the comparison.

        This implementation tries various shortcuts to terminate the comparison as quickly as possible, before
        moving on to a more expensive full comparison (that requires the items being compared to be sorted first).

        :param other: Another FieldMap, sequence of Fields, or sequence of (tag, value) tuples.
        :return: True if other is equivalent to this FieldMap, False otherwise.
        """
        try:
            other_sequence = list(other.values())
        except AttributeError:
            # 'other' is not a FieldMap, continue.
            other_sequence = other

        try:
            if len(self) != len(other_sequence):
                # Can't be equal if Sequences do not have the same length.
                return False
        except TypeError:
            # Not a sequence, cannot compare
            return False

        return self._compare_fields(other_sequence)

    def __len__(self):
        """
        :return: Number of fields in this FieldMap, including all fields in repeating groups.
        """
        return len(list(self.values()))

    @abc.abstractmethod
    def __setitem__(self, tag: int, value: any):
        """
        Sets a Field in the FieldMap with the specified tag number and value.

        :param tag: The tag number to set in the FieldMap.
        :param value: The value of the Field.
        """

    @abc.abstractmethod
    def __getitem__(self, tag: int) -> Union[Field, list]:
        """
        Tries to retrieve a Field with the given tag number from this FieldMap.

        :param tag: The tag number of the Field to look up.
        :return: A Field object (or list of Field objects if more than one Field matching the tag is found).
        :raises: TagNotFound if a Field with the specified tag number could not be found.
        """

    def __setattr__(self, key, value):
        """
        Set the value of a Field in a FieldMap

        :param key: The Field's tag name
        :param value: The value to set the Field to
        """
        if key in connection.protocol.Tag.__dict__.keys():
            self[connection.protocol.Tag.__dict__[key]] = value
        else:
            super().__setattr__(key, value)

    def __delattr__(self, item):
        """
        Delete a Field from the FieldMap

        :param item: The Field's tag name
        """
        if item in connection.protocol.Tag.__dict__.keys():
            del self[connection.protocol.Tag.__dict__[item]]
        else:
            super().__delattr__(item)

    def __iter__(self):
        """
        Enable iteration over the Fields in a FieldMap
        """
        yield from self.values()

    @abc.abstractmethod
    def __delitem__(self, tag: int):
        """
        Tries to remove a Field with the given tag number from this FieldMap.

        :param tag: The tag number of the Field to remove.
        :raises: TagNotFound if a Field with the specified tag number could not be found.
        """

    def __contains__(self, tag: int):
        """
        :return: True if the FieldMap contains a Field with the given tag number, False otherwise.
        """
        for tag_ in self.keys():
            if tag_ == tag:
                return True

        return False

    def __getattr__(self, name):
        """
        Convenience method for retrieving fields using the field name (e.g. field.MsgType will try to
        retrieve tag number 35).

        :param name: The tag name.
        :return: The Field in this FieldMap with name.
        :raises UnknownTag if name is not defined in one of the available FIX specifications.
        :raises TagNotFound if the tag name is valid, but no Field for that tag exists in the FieldMap.
        """
        try:
            # First, try to get the tag number associated with 'name'.
            tag = connection.protocol.Tag.get_tag(name)
        except UnknownTag as e:
            # Not a known tag, ignore.
            raise AttributeError(
                f"{type(self).__name__} instance has no attribute '{name}'."
            ) from e

        try:
            # Then, see if a Field with that tag number is available in this FieldMap.
            return self[tag]
        except KeyError as e:
            raise TagNotFound(tag, self, f"Tag {tag} not found in {self!r}.") from e

    def count(self, tag: int) -> int:
        """
        Counts the number of times that tag occurs in this FieldMap.

        :param tag: The tag to count occurrences of.
        :return: The number of occurrences.
        """
        try:
            return collections.Counter(field.tag for field in list(self.values()))[tag]
        except KeyError:
            return 0

    def __bytes__(self) -> bytes:
        """
        :return: The FIX-compliant, raw binary sequence for this FieldMap.
        """
        buf = b""
        for field in self.values():
            buf += bytes(field)

        return buf

    def __format__(self, format_spec) -> str:
        """
        Add support for formatting FieldMaps using the custom 't' option to add tag names.

        :param format_spec: specification in Format Specification Mini-Language format.
        :return: A formatted string representation of this Field.
        """
        fields_str = ""
        for field in self.values():
            fields_str += f"{{:{format_spec}}} | ".format(field)

        else:
            fields_str = fields_str[:-3]

        return f"{fields_str}"

    def keys(self) -> Generator[int, None, None]:
        """
        Get all of the unique tags for the Fields that have been added to this FieldMap.

        Equivalent to calling keys() on a regular Python dictionary.

        :return: a generator of integers, representing the unique tag numbers.
        """
        unique_tags = set()
        for field in self.values():
            if field.tag not in unique_tags:
                unique_tags.add(field.tag)
                yield field.tag

    def values(self) -> Generator[Field, None, None]:
        """
        Get all of the Fields that have been added to this FieldMap. Group instances should be unpacked into
        their constituent Fields.

        :return: a generator of all Field values.
        """
        for field in self.data:
            try:
                for nested_field in field.values():
                    yield nested_field
            except AttributeError:
                yield field

    def get(self, tag: int, default: any = None):
        """
        Try to retrieve the given tag from the FieldMap.

        :param tag: The tag value to retrieve.
        :param default: Optional, the default value to use if the tag does not exist in this FieldMap.
        :return: The value of the tag, or the value of default if the tag is not available.
        :raises: TagNotFound if the tag does not exist in the FieldMap and no default value was provided.
        """
        try:
            return self[tag]
        except TagNotFound as e:
            if default is None:
                raise e

            return default

    @abc.abstractmethod
    def clear(self):
        """
        Clear the FieldMap of all Fields.
        """

    def __repr__(self):
        """
        :return: :return: repr(Field) separated by |
        """
        fields_repr = ""
        for field in self.values():
            fields_repr += f"{repr(field)}, "
        else:
            fields_repr = fields_repr[:-2]

        return f"{fields_repr}"

    def __str__(self):
        """
        :return: 'tag_name_1:value_1 | tag_name_2:value_2'
        """
        fields_str = ""
        for field in self.values():
            fields_str += f"({field.tag}, {str(field)}) | "
        else:
            fields_str = fields_str[:-3]

        return f"{fields_str}"


class FieldList(FieldMap):
    """
    A simple FieldMap that stores all of its Fields in a list.

    This type of FieldMap is easy to instantiate as it does not require any knowledge of the intended
    message structure. The downside is that the internal list structure is not very efficient when it comes
    to performing Field lookups.
    """

    def __init__(self, *fields: Union[Field, tuple], **kwargs):
        """
        Initialize the FieldMap from the fields provided, storing the parsed Fields internally in a list.

        :param fields: List of Field or (tag, value) tuples.
        :param kwargs: Unused.
        """
        self._data = self._parse_fields(fields)

    @property
    def data(self):
        return self._data

    @classmethod
    def _parse_fields(cls, fields, **kwargs):
        """
        Creates a list of Fields from the provided (tag, value) pairs.

        :param fields: Any combination of (tag, value) pairs or other Field objects.
        :return: An list of Fields.
        """
        parsed_fields = []

        for field in fields:
            # For each field in the FieldMap
            if isinstance(field, Field) or isinstance(field, Group):
                # Add field as-is
                parsed_fields.append(field)
                continue

            try:
                # Add new field
                parsed_fields.append(
                    Field(
                        *field
                    )  # Make sure that this is an actual, well-formed Field.
                )
            except TypeError:
                raise ParsingError(
                    f"Invalid Field: '{field}' mut be a (tag, value) tuple."
                )

        return parsed_fields

    def __setitem__(self, tag: int, value: any):
        count = self.count(tag)
        if count > 1:
            raise DuplicateTags(
                tag,
                self.values(),
                message=f"Cannot set value: FieldMap contains {count} occurrence(s) of '{tag}'.",
            )

        if not (isinstance(value, Field) or isinstance(value, Group)):
            # Create a new Field if value is not a Field or Group already.
            value = Field(tag, value)

        if tag in self:
            # Update value, retaining the Field's position in the list
            self._data = [value if field.tag == tag else field for field in self.data]
        else:
            # Add a new Field
            self.data.append(value)

    def __getitem__(self, tag: int) -> Union[Field, list]:
        items = [field for field in self.data if field.tag == tag]

        if len(items) == 0:
            raise TagNotFound(tag, self)

        if len(items) == 1:
            return items[0]  # Return Field instead of a list of one.

        return items

    def __delitem__(self, tag: int):
        count = self.count(tag)
        if count > 1:
            raise DuplicateTags(
                tag,
                self.values(),
                message=f"Cannot delete Field by tag reference: "
                f"FieldMap contains {count} occurrences of '{tag}'. "
                f"Delete the Field(s) manually from 'data' instead.",
            )

        idx = 0
        for field in self._data:
            if field.tag == tag:
                del self._data[idx]

                return
            idx += 1

        raise TagNotFound(tag, self)

    def clear(self):
        self._data.clear()

    def __format__(self, format_spec):
        return f"[{super().__format__(format_spec)}]"

    def __repr__(self):
        """
        :return: [(tag_1, value_1), (tag_2, value_2)]
        """
        return f"{type(self).__name__}({super().__repr__()})"

    def __str__(self):
        """
        :return: '[tag_name_1:value_1 | tag_name_2:value_2]'
        """
        return f"[{super().__str__()}]"


class FieldDict(FieldMap, GroupTemplateMixin):
    """
    A FieldMap that stores all of its Fields in an OrderedDict.

    This type of FieldMap should be faster at doing Field lookups and manipulating the FieldMap in general.
    """

    def __init__(self, *fields, **kwargs):
        """
        If 'fields' contain one or more repeating groups then you *have* to provide the corresponding repeating group
        template(s) in order for the FieldMap to know how to parse and store those groups.

        :param fields: List of Field or (tag, value) tuples.
        :param kwargs: Can optionally contain a 'group_templates' keyword argument in the format:

            group_templates={identifier_tag: [instance_tag_1,..instance_tag_n]}

        that defines the additional templates that can be used to parse repeating groups. Group templates are
        automatically initialized from the GROUP_TEMPLATES setting.
        :raises: DuplicateTags if 'fields' contain repeating Fields for which no group_template has been provided.
        """
        self.group_templates = kwargs.get("group_templates", {})
        self._data = self._parse_fields(fields)

    @property
    def data(self):
        return self._data

    def _parse_fields(self, fields, **kwargs):
        """
        Parses the list of field tuples recursively into Field instances.

        :param fields: A list of (tag, value) tuples
        :return: A list of parsed Field and repeating Group objects.
        :raises: DuplicateTags if 'fields' contain repeating Fields for which no group_template has been provided.
        """
        parsed_fields = collections.OrderedDict()

        idx = 0
        tags_seen = set()

        while idx < len(fields):
            field = fields[idx]

            if not isinstance(fields[idx], Field):
                try:
                    field = Field(*fields[idx])
                except TypeError:
                    raise ParsingError(
                        f"Invalid Field: '{field}' mut be a (tag, value) tuple."
                    )

            if field.tag in tags_seen:
                raise DuplicateTags(
                    field.tag,
                    fields[idx],
                    f"No repeating group template defined for duplicate tag {field.tag} in {fields}.",
                )

            else:
                # Busy parsing a non-group tag.
                tags_seen.add(field.tag)

            if field.tag in self.group_templates:
                # Tag denotes the start of a new repeating group.
                try:
                    message_type = str(parsed_fields[connection.protocol.Tag.MsgType])
                except KeyError:
                    # Message type not yet determined!
                    raise ParsingError(
                        f"Cannot parse repeating group as MsgType tag ({connection.protocol.Tag.MsgType}) has not "
                        "been seen yet!"
                    )

                group = self._parse_group_fields(fields, idx, message_type)
                parsed_fields[group.tag] = group

                # Skip over all of the fields that were processed as part of the group.
                idx += len(group)
                continue

            parsed_fields[field.tag] = field
            idx += 1

        return parsed_fields

    def _parse_group_fields(self, fields, group_index, message_type):
        parsed_fields = []

        # Retrieve the template for this repeating group
        group_identifier = Field(fields[group_index][0], fields[group_index][1])
        templates = self.get_group_templates(
            group_identifier.tag, message_type=message_type
        )
        if len(templates) != 1:
            # Cannot have more than one template defined for a group_identifier / message_type pair
            raise ParsingError(
                f"Could not determine template for tag {group_identifier.tag}."
            )

        instance_template = templates[0]
        idx = group_index + 1

        while idx < len(fields):
            field = fields[idx]

            if not isinstance(fields[idx], Field):
                try:
                    field = Field(*fields[idx])
                except TypeError:
                    raise ParsingError(
                        f"Invalid Field: '{field}' mut be a (tag, value) tuple."
                    )

            if field.tag not in instance_template:
                # No more group fields to process - done.
                break

            if field.tag in self.group_templates:
                # Tag denotes the start of a new repeating group.
                group = self._parse_group_fields(fields, idx, message_type)

                parsed_fields.append(group)
                # Skip over all of the fields that were processed as part of the group.
                idx += len(group)
                continue

            parsed_fields.append(field)
            idx += 1

        return Group(group_identifier, *parsed_fields, template=instance_template)

    def __setitem__(self, tag: int, value: any):
        if isinstance(value, Group):
            # Also add group templates when a new group is set.
            self.add_group_templates({tag: {"*": value.template}})

        elif not (isinstance(value, Field)):
            # Create a new Field if value is not a Field or Group already.
            value = Field(tag, value)

        self._data[tag] = value

    def __getitem__(self, tag: int):
        try:
            return self._data[tag]  # Shortcut: lookup Field by tag
        except KeyError:
            raise TagNotFound(tag, self)

    def __delitem__(self, tag: int):
        try:
            del self._data[tag]
        except KeyError:
            raise TagNotFound(tag, self)

    def __contains__(self, tag: int):
        # Optimization, look for tag in dictionary first
        if tag in self._data:
            return True

        # Fallback, might be a group tag - search full field list
        return super().__contains__(tag)

    def values(self) -> Generator[Field, None, None]:
        for field in self.data.values():
            try:
                for nested_field in field.values():
                    yield nested_field
            except AttributeError:
                yield field

    def clear(self):
        self._data.clear()

    def __format__(self, format_spec):
        return f"{{{super().__format__(format_spec)}}}"

    def __repr__(self):
        """
        :return: {(tag_1, value_1), (tag_2, value_2)}
        """
        return f"{type(self).__name__}({super().__repr__()})"

    def __str__(self):
        """
        :return: '{tag_name_1:value_1 | tag_name_2:value_2}'
        """
        return f"{{{super().__str__()}}}"


class Group(FieldMap, GroupTemplateMixin):
    """
    A repeating group of FieldList 'instances' that form the Group.
    """

    def __init__(self, identifier, *fields, template=None, message_type="*"):
        """
        :param identifier: A Field that identifies the repeating Group. The value of the 'identifier' Field
        indicates the number of times that GroupInstance repeats in this Group.
        :param fields: A FieldMap or list of (tag, value) tuples.
        :param template: Optional. The list of tags that this repeating group consists of. If no template is
        provided then tries to find a template corresponding to identifier.tag in the default GROUP_TEMPLATES setting.
        :param message_type: Optional. The message type that this repeating group is for (used to retrieve the correct
        default template).
        :raises: ParsingError if no template is specified and no template could be found in settings.
        """
        group_identifier = Field(
            *identifier
        )  # First, make sure the group identifier is a valid Field.

        if template is None:
            templates = self.get_group_templates(
                group_identifier.tag, message_type=message_type
            )
            if len(templates) != 1:
                # FieldDicts are not message-type aware, so can only handle a single template per identifier tag
                raise ParsingError(
                    f"Could not determine template for tag {group_identifier.tag}."
                )

            template = templates[0]

        self.identifier = group_identifier
        self._instance_template = template
        self._instances = self._parse_fields(
            group_identifier, fields, template=template
        )

        if len(self._instances) != self.size:
            raise ParsingError(
                self.tag,
                fields,
                f"Cannot make {self.size} instances of {template} with {fields}.",
            )

    @property
    def data(self):
        return self._instances

    def _parse_fields(self, identifier, fields, template=None):
        if not fields and int(identifier) == 0:
            # Empty group
            return []

        if template is None:
            template = self._get_template(identifier)

        return self._parse_instance_fields(identifier.tag, fields, template)

    def _parse_instance_fields(self, identifier_tag, fields, template):

        instances = []
        parsed_fields = []
        instance_tags_remaining = set(template)

        for field in fields:  # Loop over group instances
            if not isinstance(field, Field) and not isinstance(field, Group):
                try:
                    field = Field(*field)
                except TypeError:
                    raise ParsingError(
                        f"Invalid Field: '{field}' mut be a (tag, value) tuple."
                    )

            if field.tag == identifier_tag:
                continue  # Skip over identifier tags

            if field.tag not in instance_tags_remaining:
                if field.tag in template:
                    # Tag belongs to the next instance. Append the current instance to this group.
                    instances.append(FieldList(*parsed_fields))

                    instance_tags_remaining = set(template)  # Reset group filter
                    parsed_fields.clear()  # Start parsing the next instance

                else:
                    raise ParsingError(
                        f"Unknown tag {field.tag} found while parsing group fields {template}."
                    )

            instance_tags_remaining.remove(field.tag)
            parsed_fields.append(field)

        if parsed_fields:
            # Append final instance that was parsed
            instances.append(FieldList(*parsed_fields))

        return instances

    def __add__(
        self, other: Union["Group", FieldMap, Sequence[Field], Sequence[tuple]]
    ) -> "Group":
        """
        Add group instance(s) to this group.

        The instance(s) to add can be contained in another Group, FieldMap, sequence of Fields, or a sequence of
        (tag, value) tuples.

        The instance fields to add will be validated against this group's template and a ParsingError raise for
        any template violations that occur.

        :param other: Another Group, FieldMap, sequence of Fields, or sequence of (tag, value) tuples.
        :return: A new Group, which includes the newly added instance fields.
        :return: A new Group, which includes the newly added instance fields.
        """
        instances = self._parse_fields(
            self.identifier, self.as_sequence(other), template=self.template
        )

        return self.__class__(
            (self.tag, self.size + len(instances)),
            *itertools.chain(self.values(), itertools.chain.from_iterable(instances)),
        )

    def __eq__(self, other: Union["Group", FieldMap, Sequence[Field], Sequence[tuple]]):
        """
        Compare this Group to other.

        The only difference between this implementation and that of FieldMap is that we also need to compare the
        'identifier' tag.

        :param other: Another Group, FieldMap, sequence of Fields, or sequence of (tag, value) tuples.
        :return: True if other is equivalent to this Group, False otherwise.
        """
        try:
            if self.identifier.tag != other.identifier.tag or str(
                self.identifier.value
            ) != str(other.identifier.value):
                return False
        except AttributeError:
            # Not a Group, try FieldMap
            try:
                other_sequence = list(other.values())
            except AttributeError:
                # Not a FieldMap, use sequence as-is
                other_sequence = other

            try:
                if self.identifier.tag != other_sequence[0][0] or str(
                    self.identifier.value
                ) != str(other_sequence[0][1]):
                    return False

            except KeyError:
                # Not a tuple, cannot compare
                return False
        else:
            other_sequence = list(other.values())

        try:
            if len(self) != len(other_sequence):
                # Can't be equal if Sequences do not have the same length.
                return False
        except TypeError:
            # Not a sequence, cannot compare
            return False

        return self._compare_fields(other_sequence)

    def __len__(self):
        length = 1  # Count identifier field
        for instance in self.instances:
            # Count all fields in each group instance
            length += len(instance)

        return length

    def __setitem__(
        self, index: int, value: Union[FieldMap, Sequence[Field], Sequence[tuple]]
    ):
        try:
            value_sequence = list(value.values())
        except AttributeError:
            # Not a FieldMap, use as-is
            value_sequence = value

        instance = self._parse_instance_fields(self.tag, value_sequence, self.template)
        if len(instance) != 1:
            raise ParsingError(
                f"{value} does not adhere to Group template '{self.template}'."
            )

        self._instances[index] = instance[0]

    def __getitem__(self, index):
        return self.instances[index]

    def values(self) -> Generator[Field, None, None]:
        yield self.identifier  # Produce this group's identifier first

        for field in self.data:
            try:
                for nested_field in field.values():
                    yield nested_field
            except AttributeError:
                yield field

    def __format__(self, format_spec):
        # Allows groups to be rendered as part of FieldMaps.
        if "t" in format_spec:
            group_instances_str = ""

            for instance in self.instances:
                group_instances_str += f"{{:{format_spec}}} | ".format(instance)
            else:
                group_instances_str = group_instances_str[:-3]
            return f"[{{:{format_spec}}}] | {group_instances_str}".format(
                self.identifier
            )

        else:
            raise ValueError(
                f"Unknown format code '{format_spec}' for object of type 'Group'."
            )

    def __repr__(self):
        """
        :return: Group(identifier tag, num instances), (tag_1, value_1), (tag_2, value_2),
                (tag_1, value_1), (tag_2, value_2))
        """
        group_instances_repr = ""
        for instance in self.instances:
            group_instances_repr += f"{repr(instance)}, "
        else:
            group_instances_repr = group_instances_repr[:-2]

        group_instances_repr = group_instances_repr.replace("FieldList(", "").replace(
            "))", ")"
        )

        return f"{self.__class__.__name__}({repr(self.identifier)}, {group_instances_repr})"

    def __str__(self):
        """
        :return: [identifier_tag_name:num_instances] | tag_1_name:value_1 | tag_2_name:value_2 |
                 tag_1_name:value_1) | tag_2_name:value_2
        """
        group_instances_str = ""
        for instance in self.instances:
            group_instances_str += f"{str(instance)} | "
        else:
            group_instances_str = group_instances_str[:-3]

        return f"[({self.tag}, {self.size})] | {group_instances_str}"

    @property
    def instances(self):
        """
        :return: A list of FieldLists that make up this Group.
        """
        return self._instances

    @property
    def template(self):
        return self._instance_template

    def __delitem__(self, index: int):
        del self._instances[index]
        self.identifier = Field(self.tag, int(self.value) - 1)

    def clear(self):
        for instance in self.instances:
            instance.clear()

        self.identifier = Field(self.identifier.tag, 0)

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
        return self.identifier.value

    @property
    def size(self):
        """
        :return: The number of GroupInstances in this group.
        """
        return int(self.identifier)

    def __bytes__(self):
        """
        :return: The FIX-compliant, raw binary string representation for this Group.
        """
        buf = b""
        for instance in self.instances:
            buf += bytes(instance)

        return bytes(self.identifier) + buf
