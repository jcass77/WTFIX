import uuid
from datetime import datetime

import pytest

from wtfix.conf import settings
from wtfix.message.message import generic_message_factory
from wtfix.protocol.common import Tag, MsgType
from ..field import Field
from ..fieldset import OrderedDictFieldSet, Group, ListFieldSet
from wtfix.core.exceptions import (
    TagNotFound,
    DuplicateTags,
    InvalidGroup,
    ImproperlyConfigured,
)


class TestFieldSet:
    """Base class to test all implementations of 'FieldSet' interface."""

    def test_add(self, fieldset_class, fieldset_impl_abc_123):
        fs = fieldset_impl_abc_123 + fieldset_class((3, "ccc"), (4, "dddd"))

        assert len(fs) == 4
        assert all(tag in fs for tag in [3, 4])
        assert fs[3] == "ccc"
        assert fs[4] == "dddd"

    def test_add_field(self, fieldset_impl_abc_123):
        fs = fieldset_impl_abc_123 + Field(3, "ccc")
        assert len(fs) == 3
        assert fs[3] == "ccc"

    def test_add_list_of_fields(self, fieldset_impl_abc_123):
        fs = fieldset_impl_abc_123 + [Field(3, "ccc"), Field(4, "dddd")]
        assert len(fs) == 4
        assert fs[3] == "ccc"
        assert fs[4] == "dddd"

    def test_add_tuple(self, fieldset_impl_abc_123):
        fs = fieldset_impl_abc_123 + (3, "ccc")
        assert len(fs) == 3
        assert fs[3] == "ccc"

    def test_add_list_of_tuples(self, fieldset_impl_abc_123):
        fs = fieldset_impl_abc_123 + [(3, "ccc"), (4, "dddd")]
        assert len(fs) == 4
        assert fs[4] == "dddd"

    def test_add_not_a_tuple_raises_error(self, fieldset_impl_abc_123):
        with pytest.raises(Exception):
            fieldset_impl_abc_123 + 1

    def test_eq(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 == fieldset_class((1, "abc"), (2, 123))

    def test_eq_different_lengths_returns_false(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 != fieldset_class((1, "abc"))

    def test_eq_different_types_converts_to_string(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 == fieldset_class((1, "abc"), (2, "123"))

    def test_eq_ordering_is_not_significant(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 == fieldset_class((2, 123), (1, "abc"))

    def test_eq_list_of_tuples(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 == [(1, "abc"), (2, 123)]

    def test_eq_unequal_tuples_returns_false(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 != [(1, "abc"), (2, 123, 456)]

    def test_eq_incompatible_type(self, fieldset_class, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123 != 1

    def test_len(self, fieldset_impl_abc_123):
        assert len(fieldset_impl_abc_123) == 2

    def test_len_group(self, fieldset_class, nested_parties_group):
        fs = fieldset_class((1, "abc"), (2, 123))
        fs.set_group(nested_parties_group)

        assert len(fs) == 19

    def test_setitem_by_tag_number(self, fieldset_class):
        fs = fieldset_class((1, "abc"), (2, 123))

        fs[3] = "c"
        assert fs[3] == "c"

    def test_setitem_by_tag_name(self, fieldset_class):
        fs = fieldset_class((1, "abc"), (2, 123))

        fs.MsgSeqNum = 1
        assert fs.MsgSeqNum == 1

    def test_setitem_replace_by_tag_number(self, fieldset_class):
        fs = fieldset_class((1, "abc"), (2, 123))
        fs[3] = "c"

        fs[2] = "aa"
        assert fs[2] == "aa"
        assert len(fs) == 3
        assert fs.fields[1].tag == 2  # Confirm position in FieldSet is maintained

    def test_setitem_replace_by_tag_name(self, fieldset_class):
        fs = fieldset_class((1, "a"), (Tag.MsgType, "b"))
        fs.MsgSeqNum = 1

        fs.MsgType = "aa"
        assert fs.MsgType == "aa"
        assert len(fs) == 3
        assert (
            fs.fields[1].tag == Tag.MsgType
        )  # Confirm position in FieldSet is maintained

    def test_getitem(self, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123[1] == "abc"

    def test_getitem_unknown(self, fieldset_impl_abc_123):
        with pytest.raises(TagNotFound):
            fieldset_impl_abc_123[3]

    def test_iter(self, fieldset_impl_abc_123):
        fields = [field for field in fieldset_impl_abc_123]
        assert fields == [(1, "abc"), (2, 123)]

        values = [str(field) for field in fieldset_impl_abc_123]
        assert values == ["abc", "123"]

        tags = [field.tag for field in fieldset_impl_abc_123]
        assert tags == [1, 2]

    def test_iter_nested_groups(self, fieldset_impl_abc_123, nested_parties_group):
        fieldset_impl_abc_123.set_group(nested_parties_group)
        fieldset_impl_abc_123[3] = "c"

        fields = [field for field in fieldset_impl_abc_123]
        assert fields == fieldset_impl_abc_123.fields

    def test_delitem(self, fieldset_impl_abc_123):
        assert len(fieldset_impl_abc_123) == 2

        del fieldset_impl_abc_123[1]
        assert len(fieldset_impl_abc_123) == 1
        assert 2 in fieldset_impl_abc_123

    def test_delitem_unknown(self, fieldset_impl_abc_123):
        with pytest.raises(TagNotFound):
            del fieldset_impl_abc_123[3]

    def test_contains(self, fieldset_impl_abc_123):
        assert 1 in fieldset_impl_abc_123
        assert 3 not in fieldset_impl_abc_123
        assert "4" not in fieldset_impl_abc_123

    def test_contains_group(self, fieldset_class, routing_id_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert 215 in fs
        assert 216 in fs
        assert 217 in fs

    def test_getattr(self, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123.Account == "abc"

    def test_getattr_unknown(self, fieldset_class):
        with pytest.raises(AttributeError):
            fs = fieldset_class((1, "a"))
            fs.TEST_TAG

    def test_getattr_not_found(self, fieldset_class):
        with pytest.raises(TagNotFound):
            fs = fieldset_class((2, "a"))
            fs.Account

    def test_fields_getter(self, fieldset_impl_abc_123):
        assert fieldset_impl_abc_123.fields == [(1, "abc"), (2, 123)]

    def test_bytes(self, fieldset_impl_abc_123):
        assert bytes(fieldset_impl_abc_123) == b"1=abc" + settings.SOH + b"2=123" + settings.SOH

    def test_nested_fields_getter(self, fieldset_impl_abc_123, nested_parties_group):
        fieldset_impl_abc_123.set_group(nested_parties_group)
        fieldset_impl_abc_123[3] = "c"

        assert len(fieldset_impl_abc_123.fields) == 20

    def test_parse_fields_tuple(self, fieldset_class):
        fs = fieldset_class((1, "a"), (2, "b"))

        assert len(fs) == 2
        assert all([tag in fs for tag in [1, 2]])
        assert all([field in fs.fields for field in [(1, "a"), (2, "b")]])
        assert type(fs[1] is Field)

    def test_parse_fields_fields(self, fieldset_class):
        fs = fieldset_class(Field(1, "a"), Field(2, "b"))

        assert len(fs) == 2
        assert all([tag in fs for tag in [1, 2]])
        assert all([field in fs.fields for field in [(1, "a"), (2, "b")]])
        assert type(fs[1] is Field)

    def test_parse_fields_fields_mixed(self, fieldset_class):
        fs = fieldset_class(Field(1, "a"), (2, "b"))

        assert len(fs) == 2
        assert all([tag in fs for tag in [1, 2]])
        assert all([field in fs.fields for field in [(1, "a"), (2, "b")]])
        assert type(fs[1] is Field)

    def test_get(self, fieldset_class):
        fs = fieldset_class((1, "abc"))
        assert fs.get(1) == "abc"

    def test_get_falls_back_to_default(self, fieldset_class):
        fs = fieldset_class()
        assert fs.get(1, default="abc") == "abc"

    def test_get_not_found_and_no_default_provided_raises_exception(
        self, fieldset_class
    ):
        with pytest.raises(TagNotFound):
            fs = fieldset_class()
            fs.get(1)

    def test_set_group(self, fieldset_class, routing_id_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert fs[routing_id_group.tag] == routing_id_group
        assert all(field in fs.fields for field in routing_id_group.fields)

    def test_set_group_instance_length_one(self, fieldset_class):
        fs = fieldset_class((1, "a"), (2, "bb"))

        short_group = Group(
            (Tag.NoMDEntryTypes, "1"),
            (Tag.MDEntryType, "a"),
            template=[Tag.MDEntryType],
        )
        fs.set_group(short_group)

        assert fs.get_group(Tag.NoMDEntryTypes) == short_group

    def test_get_group(self, fieldset_class, routing_id_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert fs.get_group(routing_id_group.tag) == routing_id_group

    def test_get_group_not_found(self, fieldset_impl_abc_123):
        with pytest.raises(TagNotFound):
            fieldset_impl_abc_123.get_group(215)

    def test_get_group_invalid(self, fieldset_impl_abc_123):
        with pytest.raises(InvalidGroup):
            fieldset_impl_abc_123.get_group(1)

    def test_get_nested_group(self, fieldset_class, nested_parties_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(nested_parties_group)

        g = fs.get_group(nested_parties_group.tag)  # Get group from FieldSet
        assert g == nested_parties_group

        ng = g[0].get_group(804)  # Get nested group from first instance in parent group

        # Ensure we have the correct group with the right (tag, value) pairs.
        assert len(ng[0]) == 2
        assert ng[0][545] == "c"
        assert ng[0][805] == "cc"


class TestListFieldSet:
    def test_repr_list_output(self):
        fs = ListFieldSet()
        assert repr(fs) == "ListFieldSet()"

        fs = ListFieldSet((1, "a"), (2, "bb"))
        assert repr(fs) == "ListFieldSet(Field(1, 'a'), Field(2, 'bb'))"

    def test_format_list_pretty_print_tags(self):
        fs = ListFieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert f"{fs:t}" == "[MsgSeqNum (34): a | MsgType (35): bb | Account (1): ccc]"

    def test_format_list_pretty_print_tags_multiple_options(self):
        fs = ListFieldSet((34, 123))
        assert f"{fs:t0.2f}" == "[MsgSeqNum (34): 123.00]"

    def test_repr_list_eval(self):
        fs = ListFieldSet()
        assert eval(repr(fs)) == fs

        fs = ListFieldSet((1, "a"), (2, "bb"))
        assert eval(repr(fs)) == fs

    def test_str_list(self):
        fs = ListFieldSet()
        assert str(fs) == "[]"

        fs = ListFieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert str(fs) == "[(34, a) | (35, bb) | (1, ccc)]"


class TestOrderedDictFieldSet:
    def test_parse_fields_duplicate_tags_raises_exception(self):
        with pytest.raises(DuplicateTags):
            OrderedDictFieldSet((1, "a"), (1, "b"))

    def test_parse_repeating_group(self, routing_id_group):
        fs = OrderedDictFieldSet(
            (1, "a"),
            (2, "b"),
            routing_id_group.identifier,
            *routing_id_group.fields,
            (3, "e"),
        )

        assert Tag.NoRoutingIDs in fs
        assert fs[1] == "a"

        group = fs.get_group(Tag.NoRoutingIDs)
        assert group.size == 2

        assert len(group[0]) == 2
        assert group[0][Tag.RoutingType] == "a"
        assert group[0][Tag.RoutingID] == "b"

        assert len(group[1]) == 2
        assert group[1].RoutingType == "c"
        assert group[1].RoutingID == "d"

        assert fs[3] == "e"

    def test_parse_incomplete_repeating_group(self):
        fs = OrderedDictFieldSet(
            (1, "a"),
            (2, "b"),
            (Tag.NoRoutingIDs, 2),
            (Tag.RoutingType, "a"),
            # (217, "b"),  <-- Simulated one instance not containing all template fields
            (Tag.RoutingType, "c"),
            (Tag.RoutingID, "d"),
            (3, "e"),
        )
        assert 215 in fs
        assert fs[1] == "a"

        group = fs.get_group(215)
        assert group.size == 2

        assert len(group[0]) == 1
        assert group[0][216] == "a"

        assert len(group[1]) == 2
        assert group[1][216] == "c"
        assert group[1][217] == "d"

        assert fs[3] == "e"

    def test_parse_repeating_group_wrong_order(self):
        fs = OrderedDictFieldSet(
            (1, "a"),
            (2, "b"),
            (3, 2),
            (6, "x"),  # <-- Switch tag order
            (4, "b"),
            (5, "a"),
            (4, "c"),
            (6, "y"),  # <-- Switch tag order
            (5, "d"),
            (7, "e"),
            group_templates={3: [4, 5, 6]},
        )

        assert 3 in fs
        assert fs[1] == "a"

        group = fs.get_group(3)
        assert group.size == 2

        assert len(group[0]) == 3
        assert group[0][4] == "b"
        assert group[0][5] == "a"
        assert group[0][6] == "x"

        assert len(group[1]) == 3
        assert group[1][4] == "c"
        assert group[1][5] == "d"
        assert group[1][6] == "y"

        assert fs[7] == "e"

    def test_parse_repeating_group_duplicate_tags(self):
        with pytest.raises(InvalidGroup):
            fs = OrderedDictFieldSet(
                (1, "a"),
                (2, "b"),
                (3, 2),
                (4, "b"),
                (5, "a"),
                (5, "a"),  # <-- Duplicate
                (6, "x"),
                (4, "c"),
                (5, "d"),
                (6, "y"),
                (7, "e"),
                group_templates={3: [4, 5, 6]},
            )

            assert 3 in fs
            assert fs[1] == "a"

            group = fs.get_group(3)
            assert group.size == 2

            assert len(group[0]) == 3
            assert group[0][4] == "b"
            assert group[0][5] == "a"
            assert group[0][6] == "x"

            assert len(group[1]) == 3
            assert group[1][4] == "c"
            assert group[1][5] == "d"
            assert group[1][6] == "y"

            assert fs[7] == "e"

    def test_parse_nested_repeating_group(self, nested_parties_group):
        fs = OrderedDictFieldSet(
            (1, "a"),
            (2, "b"),
            nested_parties_group.identifier,
            *nested_parties_group.fields,
            (3, "c"),
            group_templates={539: [524, 525, 538, 804], 804: [545, 805]},
        )

        group = fs.get_group(539)
        assert group.size == 2

        group_instance_1 = group[0]
        assert len(group_instance_1) == 8

        nested_group_1 = group_instance_1[804]
        assert len(nested_group_1) == 5

        nested_instance_1 = nested_group_1[0]
        assert len(nested_instance_1) == 2
        assert nested_instance_1[805] == "cc"

        assert fs[1] == "a"

    def test_repr_dict_output(self):
        fs = OrderedDictFieldSet()
        assert repr(fs) == "OrderedDictFieldSet()"

        fs = OrderedDictFieldSet((1, "a"), (2, "bb"))
        assert repr(fs) == "OrderedDictFieldSet(Field(1, 'a'), Field(2, 'bb'))"

    def test_format_dict_pretty_print_tags(self):
        fs = OrderedDictFieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert f"{fs:t}" == "{MsgSeqNum (34): a | MsgType (35): bb | Account (1): ccc}"

    def test_format_dict_pretty_print_tags_multiple_options(self):
        fs = OrderedDictFieldSet((34, 123))
        assert f"{fs:t0.2f}" == "{MsgSeqNum (34): 123.00}"

    def test_repr_dict_eval(self):
        fs = OrderedDictFieldSet()
        assert eval(repr(fs)) == fs

        fs = OrderedDictFieldSet((1, "a"), (2, "bb"))
        assert eval(repr(fs)) == fs

    def test_str_dict(self):
        fs = OrderedDictFieldSet()
        assert str(fs) == "{}"

        fs = OrderedDictFieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert str(fs) == "{(34, a) | (35, bb) | (1, ccc)}"

    def test_regression_for_getting_fields_for_message_with_repeating_groups(self):
        """
        Regression where repeating group fields for market data request messages (type V) were not extracted correctly
        """
        mdr_message = generic_message_factory(
            (Tag.MsgType, MsgType.MarketDataRequest),
            (Tag.MDReqID, uuid.uuid4().hex),
            (Tag.SubscriptionRequestType, "h"),  # Historical request
            (Tag.MarketDepth, 0),
        )

        mdr_message.set_group(
            Group(
                (Tag.NoRelatedSym, 1),
                (Tag.SecurityID, "test123"),
                template=[Tag.SecurityID],
            )
        )

        mdr_message.set_group(
            Group(
                (Tag.NoMDEntryTypes, 1),
                (Tag.MDEntryType, "h"),
                template=[Tag.MDEntryType],
            )
        )

        mdr_message[9956] = 1
        mdr_message[9957] = 3
        mdr_message[9958] = int(datetime.utcnow().timestamp())
        mdr_message[9959] = int(datetime.utcnow().timestamp())
        mdr_message[9960] = 1

        assert len(mdr_message) == 13
        assert len(mdr_message.fields) == 13

        assert all(
            field in mdr_message
            for field in [
                35,
                262,
                263,
                264,
                146,
                48,
                267,
                269,
                9956,
                9957,
                9958,
                9959,
                9960,
            ]
        )


class TestGroup:
    def test_defaults_to_using_templates_configured_in_settings_if_safe(self):
        g = Group((Tag.NoRoutingIDs, 1), (Tag.RoutingID, "a"), (Tag.RoutingType, "b"))

        assert g[0].RoutingID == "a"

    def test_raises_exception_if_no_group_template_available(self):
        with pytest.raises(ImproperlyConfigured):
            Group((1_234_567_890, 0))

    def test_parse_fields(self):
        g = Group(
            (Tag.NoMDEntryTypes, 3),
            (Tag.MDEntryType, "a"),
            (Tag.MDEntryPx, "abc"),
            (Tag.MDEntryType, "b"),
            (Tag.MDEntryPx, "abc"),
            (Tag.MDEntryType, "c"),
            (Tag.MDEntryPx, "abc"),
            template=[Tag.MDEntryType, Tag.MDEntryPx],
        )

        assert g[0] == [(269, "a"), (270, "abc")]
        assert g[1] == [(269, "b"), (270, "abc")]
        assert g[2] == [(269, "c"), (270, "abc")]

    def test_invalid_group(self):
        with pytest.raises(InvalidGroup):
            Group(
                (Tag.NoRoutingIDs, "2"),
                (Tag.RoutingID, "b"),
                (Tag.RoutingType, "c"),
            )

    def test_empty_group(self):
        g = Group((Tag.NoMDEntries, 0), template=[Tag.MDEntryType])

        assert g.size == 0
        assert len(g) == 1  # Should consist only of the identifier field.
        assert len(g.instances) == 0

    def test_poorly_formed_arguments_raises_exception(self):
        with pytest.raises(AttributeError):
            Group((1, "1"), *(2, "a"), template=[2])

    def test_eq(self, routing_id_group):
        assert routing_id_group == Group(
            Field(215, "2"),
            Field(216, "a"),
            Field(217, "b"),
            Field(216, "c"),
            Field(217, "d")
        )

    def test_eq_tuple(self, routing_id_group):
        assert routing_id_group == (
            (215, "2"),
            (216, "a"),
            (217, "b"),
            (216, "c"),
            (217, "d")
        )

    def test_eq_different_identifiers_returns_false(self, routing_id_group):
        assert routing_id_group != Group(
            Field(999, "2"),
            Field(216, "a"),
            Field(217, "b"),
            Field(216, "c"),
            Field(217, "d"),
            template=[216, 217]
        )

    def test_len(self, routing_id_group, nested_parties_group):
        assert len(routing_id_group) == 5
        assert len(nested_parties_group) == 17
        assert len(nested_parties_group[0]) == 8
        assert len(nested_parties_group[0][804]) == 5
        assert len(nested_parties_group[0][804][0]) == 2

    def test_len_nested_group(self, nested_parties_group):
        assert len(nested_parties_group) == 17

    def test_format_pretty_print_tags(self, routing_id_group):
        assert (
            f"{routing_id_group:t}"
            == "[NoRoutingIDs (215): 2] | [RoutingType (216): a | RoutingID (217): b] | "
            "[RoutingType (216): c | RoutingID (217): d]"
        )

    def test_repr_output(self, routing_id_group):
        assert (
            repr(routing_id_group)
            == "Group(Field(215, '2'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'))"
        )

    def test_repr_eval(self, routing_id_group):
        assert (
            eval(repr(routing_id_group)) == routing_id_group
        )

    def test_str(self, routing_id_group):
        assert (
            str(routing_id_group)
            == "[(215, 2)] | [(216, a) | (217, b)] | [(216, c) | (217, d)]"
        )

    def test_instances_getter(self, nested_parties_group):
        assert len(nested_parties_group.instances) == 2
        assert nested_parties_group.instances[0] == [
            (524, "a"),
            (525, "aa"),
            (538, "aaa"),
            (804, 2),
            (545, "c"),
            (805, "cc"),
            (545, "d"),
            (805, "dd"),
        ]

        assert nested_parties_group.instances[0].get_group(804).fields == [
            (545, "c"),
            (805, "cc"),
            (545, "d"),
            (805, "dd"),
        ]

        assert nested_parties_group.instances[1] == [
            (524, "b"),
            (525, "bb"),
            (538, "bbb"),
            (804, 2),
            (545, "e"),
            (805, "ee"),
            (545, "f"),
            (805, "ff"),
        ]

        assert nested_parties_group.instances[1].get_group(804).fields == [
            (545, "e"),
            (805, "ee"),
            (545, "f"),
            (805, "ff"),
        ]

    def test_fields_getter(self, nested_parties_group):
        assert len(nested_parties_group.fields) == 16
        assert nested_parties_group.fields == [
            (524, "a"),
            (525, "aa"),
            (538, "aaa"),
            (804, 2),
            (545, "c"),
            (805, "cc"),
            (545, "d"),
            (805, "dd"),
            (524, "b"),
            (525, "bb"),
            (538, "bbb"),
            (804, 2),
            (545, "e"),
            (805, "ee"),
            (545, "f"),
            (805, "ff"),
        ]

    def test_tag_getter(self, routing_id_group):
        assert routing_id_group.tag == 215

    def test_value_getter(self, routing_id_group):
        assert routing_id_group.value == "2"

    def test_size_getter(self, routing_id_group, nested_parties_group):
        assert routing_id_group.size == 2
        assert nested_parties_group.size == 2
        assert nested_parties_group[0][804].size == 2  # Get sub group by tag notation
        assert (
            nested_parties_group.instances[1].get_group(804).size == 2
        )  # Get sub group using explicit call

    def test_bytes(self, routing_id_group):
        assert bytes(routing_id_group) == b"215=2\x01216=a\x01217=b\x01216=c\x01217=d\x01"
