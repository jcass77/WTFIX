import copy
import uuid
from collections import OrderedDict
from datetime import datetime

import pytest

from wtfix.conf import settings
from wtfix.message.message import generic_message_factory
from wtfix.protocol.common import Tag, MsgType
from ..field import Field
from ..collections import FieldDict, Group, FieldList
from wtfix.core.exceptions import TagNotFound, DuplicateTags, ParsingError


class TestFieldMap:
    """Base class to test all implementations of 'FieldMap' interface."""

    def test_parse_fields_fields(self, fieldmap_class):
        fm = fieldmap_class(Field(1, "a"), Field(2, "b"))

        assert len(fm) == 2
        assert all([tag in fm for tag in [1, 2]])
        assert all([field in fm.values() for field in [(1, "a"), (2, "b")]])
        assert all(type(field) is Field for field in fm)

    def test_parse_fields_tuple(self, fieldmap_class):
        fm = fieldmap_class((1, "a"), (2, "b"))

        assert len(fm) == 2
        assert all([tag in fm for tag in [1, 2]])
        assert all([field in fm.values() for field in [(1, "a"), (2, "b")]])
        assert all(type(field) is Field for field in fm)

    def test_parse_fields_fields_mixed(self, fieldmap_class):
        fm = fieldmap_class(Field(1, "a"), (2, "b"))

        assert len(fm) == 2
        assert all([tag in fm for tag in [1, 2]])
        assert all([field in fm.values() for field in [(1, "a"), (2, "b")]])
        assert all(type(field) is Field for field in fm)

    def test_add_fieldmap(self, fieldmap_class, fieldmap_impl_abc_123):
        fm = fieldmap_impl_abc_123 + fieldmap_class((3, "ccc"), (4, "dddd"))

        assert len(fm) == 4
        assert all(tag in fm for tag in [3, 4])
        assert fm[3] == "ccc"
        assert fm[4] == "dddd"

    def test_add_field(self, fieldmap_impl_abc_123):
        fm = fieldmap_impl_abc_123 + Field(3, "ccc")
        assert len(fm) == 3
        assert fm[3] == "ccc"

    def test_add_sequence_of_fields(self, fieldmap_impl_abc_123):
        fm = fieldmap_impl_abc_123 + (Field(3, "ccc"), Field(4, "dddd"))
        assert len(fm) == 4
        assert fm[3] == "ccc"
        assert fm[4] == "dddd"

    def test_add_tuple(self, fieldmap_impl_abc_123):
        fm = fieldmap_impl_abc_123 + (3, "ccc")
        assert len(fm) == 3
        assert fm[3] == "ccc"

    def test_add_list_of_tuples(self, fieldmap_impl_abc_123):
        fm = fieldmap_impl_abc_123 + [(3, "ccc"), (4, "dddd")]
        assert len(fm) == 4
        assert fm[4] == "dddd"

    def test_add_not_a_sequence_raises_error(self, fieldmap_impl_abc_123):
        with pytest.raises(ParsingError):
            fieldmap_impl_abc_123 + 1

    def test_eq(self, fieldmap_class, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123 == fieldmap_class((1, "abc"), (2, 123))

    def test_eq_different_lengths_returns_false(
        self, fieldmap_class, fieldmap_impl_abc_123
    ):
        assert fieldmap_impl_abc_123 != fieldmap_class((1, "abc"))

    def test_eq_different_types_converts_to_string(
        self, fieldmap_class, fieldmap_impl_abc_123
    ):
        assert fieldmap_impl_abc_123 == fieldmap_class((1, "abc"), (2, "123"))

    def test_eq_ordering_is_not_significant(
        self, fieldmap_class, fieldmap_impl_abc_123
    ):
        assert fieldmap_impl_abc_123 == fieldmap_class((2, 123), (1, "abc"))

    def test_eq_list_of_tuples(self, fieldmap_class, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123 == [(1, "abc"), (2, 123)]

    def test_eq_list_of_fields(self, fieldmap_class, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123 == [Field(1, "abc"), Field(2, 123)]

    def test_eq_unequal_tuples_returns_false(
        self, fieldmap_class, fieldmap_impl_abc_123
    ):
        assert fieldmap_impl_abc_123 != [(1, "abc"), (2, 123, 456)]

    def test_eq_incompatible_type(self, fieldmap_class, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123 != 1

    def test_len(self, fieldmap_impl_abc_123):
        assert len(fieldmap_impl_abc_123) == 2

    def test_len_group(self, fieldmap_class, nested_parties_group):
        fm = fieldmap_class((1, "abc"), (2, 123))
        fm[nested_parties_group.tag] = nested_parties_group

        assert len(fm) == 19

    def test_setitem_by_tag_number(self, fieldmap_class):
        fm = fieldmap_class((1, "abc"), (2, 123))

        fm[3] = "c"
        assert fm[3] == "c"

    def test_setitem_by_tag_name(self, fieldmap_class):
        fm = fieldmap_class((1, "abc"), (2, 123))

        fm.MsgSeqNum = 1
        assert fm.MsgSeqNum == 1

    def test_setitem_replace_by_tag_number(self, fieldmap_class):
        fm = fieldmap_class((1, "abc"), (2, 123))
        fm[3] = "c"

        fm[2] = "aa"
        assert fm[2] == "aa"
        assert len(fm) == 3
        assert (
            list(fm.values())[1].tag == 2
        )  # Confirm position in FieldMap is maintained

    def test_setitem_replace_by_tag_name(self, fieldmap_class):
        fm = fieldmap_class((1, "a"), (Tag.MsgType, "b"))
        fm.MsgSeqNum = 1

        fm.MsgType = "aa"
        assert fm.MsgType == "aa"
        assert len(fm) == 3
        assert (
            list(fm.values())[1].tag == Tag.MsgType
        )  # Confirm position in FieldMap is maintained

    def test_setitem_group(self, fieldmap_class, routing_id_group):
        fm = fieldmap_class((1, "a"), (2, "bb"))
        fm[routing_id_group.tag] = routing_id_group

        assert fm[routing_id_group.tag] == routing_id_group
        assert all(field in fm.values() for field in routing_id_group.values())

    def test_setitem_group_instance_length_one(self, fieldmap_class):
        fm = fieldmap_class((1, "a"), (2, "bb"))

        short_group = Group(
            (Tag.NoMDEntryTypes, "1"),
            (Tag.MDEntryType, "a"),
            template=[Tag.MDEntryType],
        )
        fm[short_group.tag] = short_group

        assert fm[Tag.NoMDEntryTypes] == short_group

    def test_getitem(self, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123[1] == "abc"

    def test_getitem_unknown(self, fieldmap_impl_abc_123):
        with pytest.raises(TagNotFound):
            fieldmap_impl_abc_123[3]

    def test_getitem_wrong_tag_type_raises_exception(self, fieldmap_impl_abc_123):
        with pytest.raises(TagNotFound):
            fieldmap_impl_abc_123["3"]

    def test_getitem_group(self, fieldmap_class, routing_id_group):
        fm = fieldmap_class((1, "a"), (2, "bb"))
        fm[routing_id_group.tag] = routing_id_group

        assert isinstance(fm[routing_id_group.tag], Group)
        assert fm[routing_id_group.tag] == routing_id_group

    def test_values_nested_group(self, fieldmap_impl_abc_123, nested_parties_group):
        fieldmap_impl_abc_123[nested_parties_group.tag] = nested_parties_group
        fieldmap_impl_abc_123[3] = "c"

        assert len(fieldmap_impl_abc_123) == 20

    def test_values_and_slice(self, fieldmap_class, nested_parties_group):
        fm = fieldmap_class((1, "abc"), (2, 123))
        fm[nested_parties_group.tag] = nested_parties_group
        fm = fieldmap_class(*list(fm.values())[:2])

        assert fm == [(1, "abc"), (2, 123)]

    def test_get_group_not_found(self, fieldmap_impl_abc_123):
        with pytest.raises(TagNotFound):
            fieldmap_impl_abc_123[215]

    def test_get_nested_group(self, fieldmap_class, nested_parties_group):
        fm = fieldmap_class((1, "a"), (2, "bb"))
        fm[nested_parties_group.tag] = nested_parties_group

        g = fm[nested_parties_group.tag]  # Get group from FieldMap
        assert g == nested_parties_group

        ng = g[0][804]  # Get nested group from first instance in parent group

        # Ensure we have the correct group with the right (tag, value) pairs.
        assert len(ng[0]) == 2
        assert ng[0][545] == "c"
        assert ng[0][805] == "cc"

    def test_setattr(self, fieldmap_class):
        fm = fieldmap_class()
        fm.MsgType = MsgType.Logon

        assert fm.MsgType == MsgType.Logon

    def test_delattr(self, fieldmap_class):
        fm = fieldmap_class()
        fm.MsgType = MsgType.Logon

        assert list(fm.values()) == [(Tag.MsgType, MsgType.Logon)]

        del fm.MsgType
        assert len(list(fm.values())) == 0

    def test_iter(self, fieldmap_impl_abc_123):
        fields = [field for field in fieldmap_impl_abc_123]
        assert fields == [(1, "abc"), (2, 123)]

        values = [str(field) for field in fieldmap_impl_abc_123]
        assert values == ["abc", "123"]

        tags = [field.tag for field in fieldmap_impl_abc_123]
        assert tags == [1, 2]

    def test_iter_nested_groups(self, fieldmap_impl_abc_123, nested_parties_group):
        fieldmap_impl_abc_123[nested_parties_group.tag] = nested_parties_group
        fieldmap_impl_abc_123[3] = "c"

        fields = [field for field in fieldmap_impl_abc_123]
        assert fields == [
            (1, "abc"),
            (2, 123),
            (539, 2),
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
            (3, "c"),
        ]

    def test_delitem(self, fieldmap_impl_abc_123):
        assert len(fieldmap_impl_abc_123) == 2

        del fieldmap_impl_abc_123[1]
        assert len(fieldmap_impl_abc_123) == 1
        assert 2 in fieldmap_impl_abc_123

    def test_delitem_unknown(self, fieldmap_impl_abc_123):
        with pytest.raises(TagNotFound):
            del fieldmap_impl_abc_123[3]

    def test_delitem_wrong_tag_type_raises_exception(self, fieldmap_impl_abc_123):
        with pytest.raises(TagNotFound):
            del fieldmap_impl_abc_123["3"]

    def test_contains(self, fieldmap_impl_abc_123):
        assert 1 in fieldmap_impl_abc_123
        assert "1" not in fieldmap_impl_abc_123
        assert 3 not in fieldmap_impl_abc_123

    def test_contains_group(self, fieldmap_class, routing_id_group):
        fm = fieldmap_class((1, "a"), (2, "bb"))
        fm[routing_id_group.tag] = routing_id_group

        group_tags = {field.tag for field in routing_id_group.values()}
        assert all(tag in fm for tag in group_tags)

    def test_getattr(self, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123.Account == "abc"

    def test_getattr_unknown(self, fieldmap_class):
        with pytest.raises(AttributeError):
            fm = fieldmap_class((1, "a"))
            fm.TEST_TAG

    def test_getattr_not_found(self, fieldmap_class):
        with pytest.raises(TagNotFound):
            fm = fieldmap_class((2, "a"))
            fm.Account

    def test_getattr_group_tag(self, fieldmap_class, routing_id_group):
        fm = fieldmap_class((1, "a"), (2, "bb"))
        fm[routing_id_group.tag] = routing_id_group

        assert fm.NoRoutingIDs[0].RoutingType == (216, "a")

    def test_clear(self, fieldmap_impl_abc_123):
        assert len(fieldmap_impl_abc_123) == 2

        fieldmap_impl_abc_123.clear()
        assert len(fieldmap_impl_abc_123) == 0

    def test_count(self, fieldmap_impl_abc_123):
        assert fieldmap_impl_abc_123.count(1) == 1

    def test_count_group_fields(self, fieldmap_class, nested_parties_group):
        fm = fieldmap_class((1, "a"), (2, "bb"))
        fm[nested_parties_group.tag] = nested_parties_group

        assert fm.count(804) == 2
        assert fm.count(524) == 2
        assert fm.count(545) == 4

    def test_bytes(self, fieldmap_impl_abc_123):
        assert (
            bytes(fieldmap_impl_abc_123)
            == b"1=abc" + settings.SOH + b"2=123" + settings.SOH
        )

    def test_keys(self, fieldmap_impl_abc_123, nested_parties_group):
        fieldmap_impl_abc_123[nested_parties_group.tag] = nested_parties_group
        assert all(
            tag in fieldmap_impl_abc_123.keys()
            for tag in [1, 2, 539, 524, 525, 538, 804, 545, 805]
        )

    def test_values(self, fieldmap_impl_abc_123):
        assert all(
            value in fieldmap_impl_abc_123.values() for value in [(1, "abc"), (2, 123)]
        )

    def test_get(self, fieldmap_class):
        fm = fieldmap_class((1, "abc"))
        assert fm.get(1) == "abc"

    def test_get_falls_back_to_default(self, fieldmap_class):
        fm = fieldmap_class()
        assert fm.get(1, default="abc") == "abc"

    def test_get_not_found_and_no_default_provided_raises_exception(
        self, fieldmap_class
    ):
        with pytest.raises(TagNotFound):
            fm = fieldmap_class()
            fm.get(1)

    def test_pop(self, fieldmap_class):
        fm = fieldmap_class((1, "abc"), (2, 123), (3, "def"))
        fm.pop(2)

        assert list(fm.values()) == [(1, "abc"), (3, "def")]

    def test_copy(self, fieldmap_impl_abc_123):
        test = copy.copy(fieldmap_impl_abc_123)
        assert id(test) != id(fieldmap_impl_abc_123)
        assert test == fieldmap_impl_abc_123


class TestFieldList:
    def test_data_getter(self):
        fm = FieldList((1, "abc"), (2, 123))
        assert isinstance(fm.data, list)

    def test_setitem_duplicate_raises_exception(self, nested_parties_group):
        with pytest.raises(DuplicateTags):
            fm = FieldList(nested_parties_group)
            fm[524] = "abc"

    def test_getitem_duplicate_raises_exception(self, nested_parties_group):
        fm = FieldList((1, "abc"), (2, "def"), (2, 123), (3, "ghi"))
        assert fm[2] == [(2, "def"), (2, 123)]

    def test_pop_duplicate(self):
        with pytest.raises(DuplicateTags):
            fm = FieldList((1, "abc"), (2, 123), (1, "def"))
            fm.pop(1)

            assert list(fm.values()) == [(2, 123)]

    def test_delattr_duplicate_raises_exception(self, nested_parties_group):
        with pytest.raises(DuplicateTags):
            fm = FieldList(*nested_parties_group.values())
            del fm.NestedPartyID

    def test_delitem_duplicate_raises_exception(self, nested_parties_group):
        with pytest.raises(DuplicateTags):
            fm = FieldList(*nested_parties_group.values())
            del fm[Tag.NestedPartyID]

    def test_repr_list_output(self):
        fm = FieldList()
        assert repr(fm) == "FieldList()"

        fm = FieldList((1, "a"), (2, "bb"))
        assert repr(fm) == "FieldList(Field(1, 'a'), Field(2, 'bb'))"

    def test_format_list_pretty_print_tags(self):
        fm = FieldList((34, "a"), (35, "bb"), (1, "ccc"))
        assert f"{fm:t}" == "[MsgSeqNum (34): a | MsgType (35): bb | Account (1): ccc]"

    def test_format_list_pretty_print_tags_multiple_options(self):
        fm = FieldList((34, 123))
        assert f"{fm:t0.2f}" == "[MsgSeqNum (34): 123.00]"

    def test_repr_list_eval(self):
        fm = FieldList()
        assert eval(repr(fm)) == fm

        fm = FieldList((1, "a"), (2, "bb"))
        assert eval(repr(fm)) == fm

    def test_str_list(self):
        fm = FieldList()
        assert str(fm) == "[]"

        fm = FieldList((34, "a"), (35, "bb"), (1, "ccc"))
        assert str(fm) == "[(34, a) | (35, bb) | (1, ccc)]"


class TestFieldDict:
    def test_parse_fields_duplicate_tags_raises_exception(self):
        with pytest.raises(DuplicateTags):
            FieldDict((1, "a"), (1, "b"))

    def test_parse_repeating_group(self, routing_id_group):
        fm = FieldDict(
            (35, "a"),
            (1, "b"),
            (2, "c"),
            *routing_id_group.values(),
            (3, "e"),
            group_templates={Tag.NoRoutingIDs: {"*": [Tag.RoutingType, Tag.RoutingID]}},
        )

        assert Tag.NoRoutingIDs in fm
        assert fm[1] == "b"

        group = fm[Tag.NoRoutingIDs]
        assert group.size == 2

        assert len(group[0]) == 2
        assert group[0][Tag.RoutingType] == "a"
        assert group[0][Tag.RoutingID] == "b"

        assert len(group[1]) == 2
        assert group[1].RoutingType == "c"
        assert group[1].RoutingID == "d"

        assert fm[3] == "e"

    def test_parse_incomplete_repeating_group(self):
        fm = FieldDict(
            (35, "a"),
            (1, "b"),
            (2, "c"),
            (Tag.NoRoutingIDs, 2),
            (Tag.RoutingType, "a"),
            # (217, "b"),  <-- Simulated one instance not containing all template fields
            (Tag.RoutingType, "c"),
            (Tag.RoutingID, "d"),
            (3, "e"),
            group_templates={Tag.NoRoutingIDs: {"*": [Tag.RoutingType, Tag.RoutingID]}},
        )
        assert 215 in fm
        assert fm[1] == "b"

        group = fm[215]
        assert group.size == 2

        assert len(group[0]) == 1
        assert group[0][216] == "a"

        assert len(group[1]) == 2
        assert group[1][216] == "c"
        assert group[1][217] == "d"

        assert fm[3] == "e"

    def test_parse_repeating_group_wrong_order(self):
        fm = FieldDict(
            (35, "a"),
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
            group_templates={3: {"*": [4, 5, 6]}},
        )

        assert 3 in fm
        assert fm[1] == "a"

        group = fm[3]
        assert group.size == 2

        assert len(group[0]) == 3
        assert group[0][4] == "b"
        assert group[0][5] == "a"
        assert group[0][6] == "x"

        assert len(group[1]) == 3
        assert group[1][4] == "c"
        assert group[1][5] == "d"
        assert group[1][6] == "y"

        assert fm[7] == "e"

    def test_parse_repeating_group_duplicate_tags(self):
        with pytest.raises(ParsingError):
            fm = FieldDict(
                (35, "a"),
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
                group_templates={3: {"*": [4, 5, 6]}},
            )

            assert 3 in fm
            assert fm[1] == "a"

            group = fm[3]
            assert group.size == 2

            assert len(group[0]) == 3
            assert group[0][4] == "b"
            assert group[0][5] == "a"
            assert group[0][6] == "x"

            assert len(group[1]) == 3
            assert group[1][4] == "c"
            assert group[1][5] == "d"
            assert group[1][6] == "y"

            assert fm[7] == "e"

    def test_parse_nested_repeating_group(self, nested_parties_group):
        fm = FieldDict(
            (35, "a"),
            (1, "a"),
            (2, "b"),
            *nested_parties_group.values(),
            (3, "c"),
            group_templates={539: {"*": [524, 525, 538, 804]}, 804: {"*": [545, 805]}},
        )

        group = fm[539]
        assert group.size == 2

        group_instance_1 = group[0]
        assert len(group_instance_1) == 8

        nested_group_1 = group_instance_1[804]
        assert nested_group_1.size == 2
        assert len(nested_group_1) == 5

        nested_instance_1 = nested_group_1[0]
        assert len(nested_instance_1) == 2
        assert nested_instance_1[805] == "cc"

        assert fm[1] == "a"

    def test_data_getter(self):
        fm = FieldDict((1, "abc"), (2, 123))
        assert isinstance(fm.data, OrderedDict)

    def test_repr_dict_output(self):
        fm = FieldDict()
        assert repr(fm) == "FieldDict()"

        fm = FieldDict((1, "a"), (2, "bb"))
        assert repr(fm) == "FieldDict(Field(1, 'a'), Field(2, 'bb'))"

    def test_format_dict_pretty_print_tags(self):
        fm = FieldDict((34, "a"), (35, "bb"), (1, "ccc"))
        assert f"{fm:t}" == "{MsgSeqNum (34): a | MsgType (35): bb | Account (1): ccc}"

    def test_format_dict_pretty_print_tags_multiple_options(self):
        fm = FieldDict((34, 123))
        assert f"{fm:t0.2f}" == "{MsgSeqNum (34): 123.00}"

    def test_repr_dict_eval(self):
        fm = FieldDict()
        assert eval(repr(fm)) == fm

        fm = FieldDict((1, "a"), (2, "bb"))
        assert eval(repr(fm)) == fm

    def test_str_dict(self):
        fm = FieldDict()
        assert str(fm) == "{}"

        fm = FieldDict((34, "a"), (35, "bb"), (1, "ccc"))
        assert str(fm) == "{(34, a) | (35, bb) | (1, ccc)}"

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

        mdr_message[Tag.NoRelatedSym] = Group(
            (Tag.NoRelatedSym, 1),
            (Tag.SecurityID, "test123"),
            template=[Tag.SecurityID],
        )

        mdr_message[Tag.NoMDEntryTypes] = Group(
            (Tag.NoMDEntryTypes, 1), (Tag.MDEntryType, "h"), template=[Tag.MDEntryType]
        )

        mdr_message[9956] = 1
        mdr_message[9957] = 3
        mdr_message[9958] = int(datetime.utcnow().timestamp())
        mdr_message[9959] = int(datetime.utcnow().timestamp())
        mdr_message[9960] = 1

        assert len(mdr_message) == 13
        assert len(list(mdr_message.values())) == 13

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

    def test_parse_fields_template_violation_raises_exception(self):
        with pytest.raises(ParsingError):
            Group(
                (Tag.NoMDEntryTypes, 3),
                (Tag.MDEntryType, "a"),
                (Tag.MDEntryPx, "abc"),
                (Tag.MDEntryType, "b"),
                (Tag.MDEntryPx, "abc"),
                (999, "c"),  # <-- Invalid tag
                (Tag.MDEntryPx, "abc"),
                template=[Tag.MDEntryType, Tag.MDEntryPx],
            )

    def test_parse_fields_wrong_size_raises_exception(self):
        with pytest.raises(ParsingError):
            Group(
                (Tag.NoMDEntryTypes, 3),  # <-- Only two instances provided
                (Tag.MDEntryType, "a"),
                (Tag.MDEntryPx, "abc"),
                (Tag.MDEntryType, "b"),
                (Tag.MDEntryPx, "abc"),
                template=[Tag.MDEntryType, Tag.MDEntryPx],
            )

    def test_defaults_to_using_templates_configured_in_settings_if_safe(self):
        g = Group((Tag.NoRoutingIDs, 1), (Tag.RoutingID, "a"), (Tag.RoutingType, "b"))

        assert g[0].RoutingID == "a"

    def test_raises_exception_if_no_group_template_available(self):
        with pytest.raises(ParsingError):
            Group((1_234_567_890, 0))

    def test_invalid_group(self):
        with pytest.raises(ParsingError):
            Group((Tag.NoRoutingIDs, "2"), (Tag.RoutingID, "b"), (Tag.RoutingType, "c"))

    def test_empty_group(self):
        g = Group((Tag.NoMDEntries, 0), template=[Tag.MDEntryType])

        assert g.size == 0
        assert len(g) == 1  # Should consist only of the identifier field.
        assert len(g.instances) == 0

    def test_poorly_formed_arguments_raises_exception(self):
        with pytest.raises(ParsingError):
            Group((1, "1"), *(2, "a"), template=[2])

    def test_data_getter(self, routing_id_group):
        assert isinstance(routing_id_group.data, list)

    def test_add_group(self, routing_id_group):
        other = Group(
            (Tag.NoRoutingIDs, 2),
            (Tag.RoutingType, "e"),
            (Tag.RoutingID, "f"),
            (Tag.RoutingType, "g"),
            (Tag.RoutingID, "h"),
            template=[Tag.RoutingType, Tag.RoutingID],
        )

        g = routing_id_group + other
        assert g.size == 4
        assert (
            repr(g)
            == "Group(Field(215, '4'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'), Field(216, 'e'), Field(217, 'f'), Field(216, 'g'), Field(217, 'h'))"  # noqa
        )

    def test_add_fieldmap(self, fieldmap_class, routing_id_group):
        other = fieldmap_class((Tag.RoutingType, "e"), (Tag.RoutingID, "f"))

        g = routing_id_group + other
        assert (
            repr(g)
            == "Group(Field(215, '3'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'), Field(216, 'e'), Field(217, 'f'))"  # noqa
        )

    def test_add_field(self, routing_id_group):
        fm = routing_id_group + Field(216, "z")
        assert (
            repr(fm)
            == "Group(Field(215, '3'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'), Field(216, 'z'))"  # noqa
        )

    def test_add_sequence_of_fields(self, routing_id_group):
        other = (Field(Tag.RoutingType, "e"), Field(Tag.RoutingID, "f"))

        g = routing_id_group + other
        assert (
            repr(g)
            == "Group(Field(215, '3'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'), Field(216, 'e'), Field(217, 'f'))"  # noqa
        )

    def test_add_tuple(self, routing_id_group):
        fm = routing_id_group + (216, "z")
        assert (
            repr(fm)
            == "Group(Field(215, '3'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'), Field(216, 'z'))"  # noqa
        )

    def test_add_sequence_of_tuples(self, routing_id_group):
        other = ((Tag.RoutingType, "e"), (Tag.RoutingID, "f"))

        g = routing_id_group + other
        assert (
            repr(g)
            == "Group(Field(215, '3'), Field(216, 'a'), Field(217, 'b'), Field(216, 'c'), Field(217, 'd'), Field(216, 'e'), Field(217, 'f'))"  # noqa
        )

    def test_add_not_compatible_with_template_raises_exception(self, routing_id_group):
        with pytest.raises(ParsingError):
            routing_id_group + ((123_456_789, "def"),)

    def test_eq_group(self, routing_id_group):
        assert routing_id_group == Group(
            Field(215, 2),
            Field(216, "a"),
            Field(217, "b"),
            Field(216, "c"),
            Field(217, "d"),
        )

    def test_eq_fieldmap(self, fieldmap_class):
        group = Group(
            (
                Tag.NoRoutingIDs,
                1,
            ),  # Can only contain one instance to be comparable to FieldDict
            (Tag.RoutingType, "a"),
            (Tag.RoutingID, "b"),
            template=[Tag.RoutingType, Tag.RoutingID],
        )

        assert group == fieldmap_class((215, 1), (216, "a"), (217, "b"))

    def test_eq_sequence_of_fields(self, routing_id_group):
        assert routing_id_group == (
            Field(215, 2),
            Field(216, "a"),
            Field(217, "b"),
            Field(216, "c"),
            Field(217, "d"),
        )

    def test_eq_sequence_of_tuples(self, routing_id_group):
        assert routing_id_group == (
            (215, "2"),
            (216, "a"),
            (217, "b"),
            (216, "c"),
            (217, "d"),
        )

    def test_eq_different_identifiers_returns_false(self, routing_id_group):
        assert routing_id_group != Group(
            Field(999, "2"),
            Field(216, "a"),
            Field(217, "b"),
            Field(216, "c"),
            Field(217, "d"),
            template=[216, 217],
        )

    def test_len(self, routing_id_group, nested_parties_group):
        assert len(routing_id_group) == 5
        assert len(nested_parties_group) == 17
        assert len(nested_parties_group[0]) == 8
        assert len(nested_parties_group[0][804]) == 5
        assert len(nested_parties_group[0][804][0]) == 2

    def test_len_nested_group(self, nested_parties_group):
        assert len(nested_parties_group) == 17

    def test_setitem_fieldmap(self, fieldmap_class, routing_id_group):
        routing_id_group[1] = fieldmap_class(
            (Tag.RoutingType, "c"), (Tag.RoutingID, "d")
        )

        assert routing_id_group.size == 2
        assert routing_id_group[1] == [(Tag.RoutingType, "c"), (Tag.RoutingID, "d")]

    def test_setitem_sequence_of_fields(self, routing_id_group):
        routing_id_group[1] = (Field(Tag.RoutingType, "c"), Field(Tag.RoutingID, "d"))

        assert routing_id_group.size == 2
        assert routing_id_group[1] == [(Tag.RoutingType, "c"), (Tag.RoutingID, "d")]

    def test_setitem_sequence_of_tuples(self, routing_id_group):
        routing_id_group[1] = [(Tag.RoutingType, "c"), (Tag.RoutingID, "d")]

        assert routing_id_group.size == 2
        assert routing_id_group[1] == [(Tag.RoutingType, "c"), (Tag.RoutingID, "d")]

    def test_setitem_partial_instance(self, routing_id_group):
        routing_id_group[1] = [(Tag.RoutingType, "d")]

        assert routing_id_group.size == 2
        assert routing_id_group[1] == [(Tag.RoutingType, "d")]

    def test_setitem_index_out_of_range_raises_exception(self, routing_id_group):
        with pytest.raises(IndexError):
            routing_id_group[2] = [(Tag.RoutingType, "c"), (Tag.RoutingID, "d")]

    def test_setitem_not_compatible_with_template_raises_exception(
        self, routing_id_group
    ):
        with pytest.raises(ParsingError):
            routing_id_group[1] = [(123_456_789, "c")]

    def test_get_item(self, routing_id_group):
        assert routing_id_group[0] == routing_id_group.instances[0]

    def test_get_item_index_out_of_range_raises_exception(self, routing_id_group):
        with pytest.raises(IndexError):
            routing_id_group[len(routing_id_group) + 1]

    def test_values(self, routing_id_group):
        fields = list(routing_id_group.values())
        assert len(fields) == 5
        assert fields == [
            (Tag.NoRoutingIDs, "2"),
            (Tag.RoutingType, "a"),
            (Tag.RoutingID, "b"),
            (Tag.RoutingType, "c"),
            (Tag.RoutingID, "d"),
        ]

    def test_values_nested(self, nested_parties_group):
        fields = list(nested_parties_group.values())
        assert len(fields) == 17
        assert fields == [
            (539, 2),
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
        assert eval(repr(routing_id_group)) == routing_id_group

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

        assert nested_parties_group.instances[0][804].instances[0] == [
            (545, "c"),
            (805, "cc"),
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

        assert nested_parties_group.instances[1][804].instances[1] == [
            (545, "f"),
            (805, "ff"),
        ]

    def test_del_item(self, routing_id_group):
        assert routing_id_group.size == 2

        del routing_id_group[0]
        assert routing_id_group.size == 1

    def test_clear(self):
        g = Group((Tag.NoRoutingIDs, 1), (Tag.RoutingID, "a"), (Tag.RoutingType, "b"))

        assert len(g) == 3

        g.clear()
        assert list(g.values()) == [(215, 0)]
        assert g.size == 0
        assert g.value == 0

    def test_tag_getter(self, routing_id_group):
        assert routing_id_group.tag == 215

    def test_value_getter(self, routing_id_group):
        assert routing_id_group.value == "2"

    def test_size_getter(self, routing_id_group, nested_parties_group):
        assert routing_id_group.size == 2
        assert nested_parties_group.size == 2
        assert nested_parties_group[0][804].size == 2  # Get sub group by tag notation
        assert (
            nested_parties_group.instances[1][804].size == 2
        )  # Get sub group using explicit call

    def test_bytes(self, routing_id_group):
        assert (
            bytes(routing_id_group) == b"215=2\x01216=a\x01217=b\x01216=c\x01217=d\x01"
        )
