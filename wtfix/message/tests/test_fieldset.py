import pytest

from wtfix.conf import settings
from wtfix.protocol.common import Tag
from ..field import Field
from ..fieldset import OrderedDictFieldSet, Group, ListFieldSet
from wtfix.core.exceptions import (
    TagNotFound,
    DuplicateTags,
    InvalidGroup,
)


class TestFieldSet:
    """Base class to test all implementations of 'FieldSet' interface."""

    def test_add(self, fieldset_class, fieldset_impl_ab):
        fs = fieldset_impl_ab + fieldset_class((3, "ccc"), (4, "dddd"))

        assert len(fs) == 4
        assert all(tag in fs for tag in [3, 4])
        assert fs[3] == "ccc"
        assert fs[4] == "dddd"

    def test_add_field(self, fieldset_impl_ab):
        fs = fieldset_impl_ab + Field(3, "ccc")
        assert len(fs) == 3
        assert fs[3] == "ccc"

    def test_add_list_of_fields(self, fieldset_impl_ab):
        fs = fieldset_impl_ab + [Field(3, "ccc"), Field(4, "dddd")]
        assert len(fs) == 4
        assert fs[3] == "ccc"
        assert fs[4] == "dddd"

    def test_add_tuple(self, fieldset_impl_ab):
        fs = fieldset_impl_ab + (3, "ccc")
        assert len(fs) == 3
        assert fs[3] == "ccc"

    def test_add_list_of_tuples(self, fieldset_impl_ab):
        fs = fieldset_impl_ab + [(3, "ccc"), (4, "dddd")]
        assert len(fs) == 4
        assert fs[4] == "dddd"

    def test_add_not_a_tuple_raises_error(self, fieldset_impl_ab):
        with pytest.raises(TypeError):
            fieldset_impl_ab + 1

    def test_eq(self, fieldset_class, fieldset_impl_ab):
        assert fieldset_impl_ab == fieldset_class((1, "a"), (2, "bb"))

    def test_eq_list_of_tuples(self, fieldset_class, fieldset_impl_ab):
        assert fieldset_impl_ab == [(1, "a"), (2, "bb")]

    def test_len(self, fieldset_impl_ab):
        assert len(fieldset_impl_ab) == 2

    def test_len_group(self, fieldset_class, nested_parties_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(nested_parties_group)

        assert len(fs) == 19

    def test_setitem(self, fieldset_class):
        fs = fieldset_class((1, "a"), (2, "b"))

        fs[3] = "c"
        assert fs[3] == "c"

    def test_setitem_replace(self, fieldset_class):
        fs = fieldset_class((1, "a"), (2, "b"))
        fs[3] = "c"

        fs[2] = "aa"
        assert fs[2] == "aa"
        assert len(fs) == 3
        assert fs.fields[1].tag == 2  # Confirm position in FieldSet is maintained

    def test_getitem(self, fieldset_impl_ab):
        assert fieldset_impl_ab[1] == "a"

    def test_getitem_unknown(self, fieldset_impl_ab):
        with pytest.raises(TagNotFound):
            fieldset_impl_ab[3]

    def test_delitem(self, fieldset_impl_ab):
        assert len(fieldset_impl_ab) == 2

        del fieldset_impl_ab[1]
        assert len(fieldset_impl_ab) == 1
        assert 2 in fieldset_impl_ab

    def test_delitem_unknown(self, fieldset_impl_ab):
        with pytest.raises(TagNotFound):
            del fieldset_impl_ab[3]

    def test_contains(self, fieldset_impl_ab):
        assert 1 in fieldset_impl_ab
        assert 3 not in fieldset_impl_ab
        assert "4" not in fieldset_impl_ab

    def test_contains_group(self, fieldset_class, routing_id_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert 215 in fs
        assert 216 in fs
        assert 217 in fs

    def test_getattr(self, fieldset_impl_ab):
        assert fieldset_impl_ab.Account == "a"

    def test_getattr_unknown(self, fieldset_class):
        with pytest.raises(AttributeError):
            fs = fieldset_class((1, "a"))
            fs.TEST_TAG

    def test_getattr_not_found(self, fieldset_class):
        with pytest.raises(TagNotFound):
            fs = fieldset_class((2, "a"))
            fs.Account

    def test_fields_getter(self, fieldset_impl_ab):
        assert fieldset_impl_ab.fields == [(1, "a"), (2, "bb")]

    def test_raw_getter(self, fieldset_impl_ab):
        assert fieldset_impl_ab.raw == b"1=a" + settings.SOH + b"2=bb" + settings.SOH

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

    def test_set_group(self, fieldset_class, routing_id_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert fs[routing_id_group.tag] == routing_id_group
        assert all(field in fs.fields for field in routing_id_group.fields)

    def test_set_group_instance_length_one(self, fieldset_class):
        fs = fieldset_class((1, "a"), (2, "bb"))

        short_group = Group((Tag.NoMDEntryTypes, "1"), (Tag.MDEntryType, "a"))
        fs.set_group(short_group)

        assert fs.get_group(Tag.NoMDEntryTypes) == short_group

    def test_get_group(self, fieldset_class, routing_id_group):
        fs = fieldset_class((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert fs.get_group(routing_id_group.tag) == routing_id_group

    def test_get_group_not_found(self, fieldset_impl_ab):
        with pytest.raises(TagNotFound):
            fieldset_impl_ab.get_group(215)

    def test_get_group_invalid(self, fieldset_impl_ab):
        with pytest.raises(InvalidGroup):
            fieldset_impl_ab.get_group(1)

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


class TesListFieldSet:
    def test_repr_list(self):
        fs = ListFieldSet()
        assert repr(fs) == "[]"

        fs = ListFieldSet((1, "a"), (2, "bb"))
        assert repr(fs) == "[(1, a), (2, bb)]"

    def test_str_list(self):
        fs = ListFieldSet()
        assert str(fs) == "[]"

        fs = ListFieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert str(fs) == "[MsgSeqNum (34):a | MsgType (35):bb | Account (1):ccc]"


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
            (3, "c"),
            group_templates={215: [216, 217]}
        )

        assert 215 in fs
        assert fs[1] == "a"

        group = fs.get_group(215)
        assert group.size == 2

        assert len(group[0]) == 2
        assert group[0][216] == "a"
        assert group[0][217] == "b"

        assert len(group[0]) == 2
        assert group[1][216] == "c"
        assert group[1][217] == "d"

        assert fs[3] == "c"

    def test_parse_nested_repeating_group(self, nested_parties_group):
        fs = OrderedDictFieldSet(
            (1, "a"),
            (2, "b"),
            nested_parties_group.identifier,
            *nested_parties_group.fields,
            (3, "c"),
            group_templates={539: [524, 525, 538], 804: [545, 805]}
        )
        # fs = OrderedDictFieldSet((1, 'a'), (2, 'b'), (539, 2), (524, "a"), (525, "aa"), (538, "aaa"), (804, 2), (545, "c"), (805, "cc"), (545, "d"), (805, "dd"), (524, "b"), (525, "bb"), (538, "bbb"), (804, 2), (545, "e"), (805, "ee"), (545, "f"), (805, "ff"), (3, "c"), group_templates={539: [524, 525, 538], 804: [545, 805]})

        group = fs.get_group(539)
        assert group.size == 2

        group_instance_1 = group[0]
        assert len(group_instance_1) == 8

        nested_group_1 = group_instance_1[804]
        assert len(nested_group_1) == 5

        nested_instance_1 = nested_group_1[0]
        assert len(nested_instance_1) == 2
        assert nested_instance_1[805] == "cc"

        assert fs[1].value_ref == "a"

    def test_repr_dict(self):
        fs = OrderedDictFieldSet()
        assert repr(fs) == "{}"

        fs = OrderedDictFieldSet((1, "a"), (2, "bb"))
        assert repr(fs) == "{(1, a), (2, bb)}"

    def test_str_dict(self):
        fs = OrderedDictFieldSet()
        assert str(fs) == "{}"

        fs = OrderedDictFieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert str(fs) == "{MsgSeqNum (34):a | MsgType (35):bb | Account (1):ccc}"


class TestGroup:
    def test_group(self):
        entry_types = [5, "B"]
        instances = []
        for et in entry_types:
            instances.append((Tag.MDEntryType, et))

        g = Group(
            (Tag.NoMDEntryTypes, 2), *((Tag.MDEntryType, et) for et in entry_types)
        )

        assert repr(g) == "[(267, 2)]:[(269, 5)], [(269, B)]"

    def test_invalid_group(self):
        with pytest.raises(InvalidGroup):
            Group((215, "2"), (216, "a"), (217, "b"), (216, "c"))

    def test_len(self, routing_id_group):
        assert len(routing_id_group) == 5

    def test_len_nested_group(self, nested_parties_group):
        assert len(nested_parties_group) == 17

    def test_repr(self, routing_id_group):
        assert (
            repr(routing_id_group)
            == "[(215, 2)]:[(216, a), (217, b)], [(216, c), (217, d)]"
        )

    def test_str(self, routing_id_group):
        assert (
            str(routing_id_group)
            == "[NoRoutingIDs (215):2] | [RoutingType (216):a | RoutingID (217):b] | "
            "[RoutingType (216):c | RoutingID (217):d]"
        )

    def test_raw_getter(self, routing_id_group):
        assert routing_id_group.raw == b"215=2\x01216=a\x01217=b\x01216=c\x01217=d\x01"

    def test_tag_getter(self, routing_id_group):
        assert routing_id_group.tag == 215

    def test_value_getter(self, routing_id_group):
        assert routing_id_group.value == "2"

    def test_size_getter(self, routing_id_group):
        assert routing_id_group.size == 2
