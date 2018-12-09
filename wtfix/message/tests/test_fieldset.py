import pytest

from wtfix.conf import settings
from ..field import Field
from ..fieldset import FieldSet, Group
from wtfix.core.exceptions import TagNotFound, DuplicateTags, InvalidGroup


class TestFieldSet:
    def test_add(self, fieldset_a_b):
        fs = fieldset_a_b + FieldSet((3, "ccc"), (4, "dddd"))

        assert len(fs) == 4
        assert all(tag in fs for tag in [3, 4])
        assert fs[3] == "ccc"
        assert fs[4] == "dddd"

    def test_add_field(self, fieldset_a_b):
        fs = fieldset_a_b + Field(3, "ccc")
        assert len(fs) == 3
        assert fs[3] == "ccc"

    def test_add_list_of_fields(self, fieldset_a_b):
        fs = fieldset_a_b + [Field(3, "ccc"), Field(4, "dddd")]
        assert len(fs) == 4
        assert fs[3] == "ccc"
        assert fs[4] == "dddd"

    def test_add_tuple(self, fieldset_a_b):
        fs = fieldset_a_b + (3, "ccc")
        assert len(fs) == 3
        assert fs[3] == "ccc"

    def test_add_list_of_tuples(self, fieldset_a_b):
        fs = fieldset_a_b + [(3, "ccc"), (4, "dddd")]
        assert len(fs) == 4
        assert fs[4] == "dddd"

    def test_len(self, fieldset_a_b):
        assert len(fieldset_a_b) == 2

    def test_len_group(self, nested_parties_group):
        fs = FieldSet((1, "a"), (2, "bb"))
        fs.set_group(nested_parties_group)

        assert len(fs) == 19

    def test_setitem(self, fieldset_a_b):
        fs = FieldSet((1, "a"), (2, "b"))

        fs[3] = "c"
        assert fs[3] == "c"

    def test_getitem(self, fieldset_a_b):
        assert fieldset_a_b[1] == "a"

    def test_getitem_unknown(self, fieldset_a_b):
        with pytest.raises(TagNotFound):
            fieldset_a_b[3]

    def test_getattr(self, fieldset_a_b):
        assert fieldset_a_b.Account == "a"

    def test_getattr_unknown(self):
        with pytest.raises(AttributeError):
            fs = FieldSet((1, "a"))
            fs.TEST_TAG

    def test_getattr_not_found(self):
        with pytest.raises(TagNotFound):
            fs = FieldSet((2, "a"))
            fs.Account

    def test_repr(self, fieldset_a_b):
        fs = FieldSet()
        assert repr(fs) == ""

        assert repr(fieldset_a_b) == "(1, a), (2, bb)"

    def test_str(self):
        fs = FieldSet()
        assert str(fs) == ""

        fs = FieldSet((34, "a"), (35, "bb"), (1, "ccc"))
        assert (
            str(fs) == "(MsgSeqNum (34), a), (MsgType (35), bb), (Account (1), ccc)"
        )

    def test_raw(self, fieldset_a_b):
        assert fieldset_a_b.raw == b"1=a" + settings.SOH + b"2=bb" + settings.SOH

    def test_parse_fields_tuple(self):
        fs = FieldSet((1, "a"), (2, "b"))

        assert len(fs) == 2
        assert all([tag in fs for tag in [1, 2]])
        assert all([value in fs.items() for value in [(1, "a"), (2, "b")]])
        assert type(fs[1] is Field)

    def test_parse_fields_fields(self):
        fs = FieldSet(Field(1, "a"), Field(2, "b"))

        assert len(fs) == 2
        assert all([tag in fs for tag in [1, 2]])
        assert all([value in fs.items() for value in [(1, "a"), (2, "b")]])
        assert type(fs[1] is Field)

    def test_parse_fields_fields_mixed(self):
        fs = FieldSet(Field(1, "a"), (2, "b"))

        assert len(fs) == 2
        assert all([tag in fs for tag in [1, 2]])
        assert all([value in fs.items() for value in [(1, "a"), (2, "b")]])
        assert type(fs[1] is Field)

    def test_parse_fields_duplicate_tags_raises_exception(self):
        with pytest.raises(DuplicateTags):
            FieldSet((1, "a"), (1, "b"))

    def test_set_group(self, routing_id_group):
        fs = FieldSet((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert fs[routing_id_group.tag] == routing_id_group

    def test_get_group(self, fieldset_a_b, routing_id_group):
        fs = FieldSet((1, "a"), (2, "bb"))
        fs.set_group(routing_id_group)

        assert fs.get_group(routing_id_group.tag) == routing_id_group

    def test_get_group_not_found(self, fieldset_a_b):
        with pytest.raises(TagNotFound):
            fieldset_a_b.get_group(215)

    def test_get_group_invalid(self, fieldset_a_b):
        with pytest.raises(InvalidGroup):
            fieldset_a_b.get_group(1)

    def test_get_nested_group(self, nested_parties_group):
        fs = FieldSet((1, "a"), (2, "bb"))
        fs.set_group(nested_parties_group)

        g = fs.get_group(nested_parties_group.tag)  # Get group from FieldSet
        assert g == nested_parties_group

        ng = g[0].get_group(804)  # Get nested group from first instance in parent group

        # Ensure we have the correct group with the right (tag, value) pairs.
        assert len(ng[0]) == 2
        assert ng[0][545] == "c"
        assert ng[0][805] == "cc"


class TestGroupInstance:
    # Currently identical to FieldSet
    pass


class TestGroup:
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
            == "(215, 2):(216, a), (217, b), (216, c), (217, d)"
        )

    def test_str(self, routing_id_group):
        assert (
            str(routing_id_group)
            == "(NoRoutingIDs (215), 2):(RoutingType (216), a), (RoutingID (217), b), "
            "(RoutingType (216), c), (RoutingID (217), d)"
        )

    def test_raw(self, routing_id_group):
        assert routing_id_group.raw == b"215=2\x01216=a\x01217=b\x01216=c\x01217=d\x01"

    def test_tag_getter(self, routing_id_group):
        assert routing_id_group.tag == 215

    def test_value_getter(self, routing_id_group):
        assert routing_id_group.value == "2"

    def test_size_getter(self, routing_id_group):
        assert routing_id_group.size == 2
