import pytest

from ...protocol import base
from ..field import Field
from ..fieldset import (
    DuplicateTags,
    FieldSet,
    GroupInstance,
    TagNotFound,
    UnknownTag,
    InvalidGroup,
)


class TestFieldSet:
    def test_add(self, fieldset_a_b):
        fs1 = FieldSet((3, b"ccc"), (4, b"dddd"))

        fs2 = fieldset_a_b + fs1
        assert len(fs2) == 4
        assert list(fs2) == [(1, b"a"), (2, b"bb"), (3, b"ccc"), (4, b"dddd")]

    def test_add_field(self, fieldset_a_b):
        f = Field((3, b"ccc"))

        fs = fieldset_a_b + f
        assert len(fs) == 3
        assert list(fs) == [(1, b"a"), (2, b"bb"), (3, b"ccc")]

    def test_add_tuple(self, fieldset_a_b):
        fs = fieldset_a_b + (3, b"ccc")
        assert len(fs) == 3
        assert list(fs) == [(1, b"a"), (2, b"bb"), (3, b"ccc")]

    def test_is_eq(self, fieldset_a_b):
        fs1 = fs2 = fieldset_a_b

        assert fs1 == fs2

    def test_is_eq_list_of_tuples(self, fieldset_a_b):
        assert fieldset_a_b == [(1, b"a"), (2, b"bb")]

    def test_is_eq_list_of_fields(self, fieldset_a_b):
        assert fieldset_a_b == [Field(1, b"a"), Field(2, b"bb")]

    def test_is_not_eq(self, fieldset_a_b):
        fs = FieldSet((3, b"ccc"), (4, b"dddd"))

        assert fieldset_a_b != fs

    def test_is_not_eq_list_of_tuples(self, fieldset_a_b):
        assert fieldset_a_b != [(1, b"a"), (2, b"a")]

    def test_is_not_eq_list_of_fields(self, fieldset_a_b):
        assert fieldset_a_b != [Field(1, b"a"), Field(2, b"a")]

    def test_iter(self, fieldset_a_b):

        fields = []
        for field in iter(fieldset_a_b):
            fields.append(field)

        assert fields == [(1, b"a"), (2, b"bb")]
        assert type(fields[0] is Field)

    def test_get_item(self):
        fs = FieldSet((1, b"a"), (2, b"bb"), (3, b"ccc"))

        assert type(fs[1]) is Field
        assert fs[1] == (2, b"bb")
        assert fs[1:] == FieldSet((2, b"bb"), (3, b"ccc"))

    def test_len(self):
        fs = FieldSet((1, b"a"), (2, b"bb"), (3, b"ccc"))

        assert len(fs) == 3

    def test_getattr(self, fieldset_a_b):
        assert fieldset_a_b.Account == b"a"

    def test_getattr_unknown(self):
        with pytest.raises(UnknownTag):
            fs = FieldSet((1, b"a"))
            fs.TEST_TAG

    def test_getattr_not_found(self):
        with pytest.raises(TagNotFound):
            fs = FieldSet((2, b"a"))
            fs.Account

    def test_repr(self, fieldset_a_b):
        fs = FieldSet()
        assert repr(fs) == "()"

        assert repr(fieldset_a_b) == "((1, b'a'), (2, b'bb'))"

    def test_str(self):
        fs = FieldSet()
        assert str(fs) == "()"

        fs = FieldSet((34, b"a"), (35, b"bb"), (1, b"ccc"))
        assert str(fs) == "((MsgSeqNum, b'a'), (MsgType, b'bb'), (Account, b'ccc'))"

    def test_fields_getter(self, fieldset_a_b):
        assert list(fieldset_a_b.fields) == [(1, b"a"), (2, b"bb")]

    def test_raw(self, fieldset_a_b):
        assert fieldset_a_b.raw == b"1=a" + base.SOH + b"2=bb" + base.SOH

    def test_parse_fields_tuple(self):
        fs = FieldSet((1, b"a"), (2, b"b"))

        assert len(fs) == 2
        assert all([key in fs._fields for key in [1, 2]])
        assert all([value in fs._fields.values() for value in [(1, b"a"), (2, b"b")]])
        assert type(fs._fields[1] is Field)

    def test_parse_fields_fields(self):
        fs = FieldSet(Field(1, b"a"), Field(2, b"b"))

        assert len(fs) == 2
        assert all([key in fs._fields for key in [1, 2]])
        assert all([value in fs._fields.values() for value in [(1, b"a"), (2, b"b")]])
        assert type(fs._fields[1] is Field)

    def test_parse_fields_fields_mixed(self):
        fs = FieldSet(Field(1, b"a"), (2, b"b"))

        assert len(fs) == 2
        assert all([key in fs._fields for key in [1, 2]])
        assert all([value in fs._fields.values() for value in [(1, b"a"), (2, b"b")]])
        assert type(fs._fields[1] is Field)

    def test_parse_fields_duplicate_tags_raises_exception(self):
        with pytest.raises(DuplicateTags):
            FieldSet((1, b"a"), (1, b"b"))

    def test_get(self, fieldset_a_b):
        assert fieldset_a_b.get(1) == b"a"
        assert fieldset_a_b.get(1, b"default") == b"a"

    def test_get_default(self, fieldset_a_b):
        assert fieldset_a_b.get(3, b"default") == b"default"

    def test_get_not_found(self, fieldset_a_b):
        with pytest.raises(TagNotFound):
            fieldset_a_b.get(3)

    def test_set_group(self, routing_id_group):
        fs = FieldSet((1, b"a"), (2, b"bb"))
        fs.set_group(routing_id_group)

        assert fs.get(routing_id_group.tag)

    def test_get_group(self, fieldset_a_b, routing_id_group):
        fs = FieldSet((1, b"a"), (2, b"bb"))
        fs.set_group(routing_id_group)

        assert fs.get_group(215) == routing_id_group

    def test_get_group_not_found(self, fieldset_a_b):
        with pytest.raises(TagNotFound):
            fieldset_a_b.get_group(215)

    def test_get_group_invalid(self, fieldset_a_b):
        with pytest.raises(InvalidGroup):
            fieldset_a_b.get_group(1)

    def test_get_nested_group(self, nested_parties_group):
        fs = FieldSet((1, b"a"), (2, b"bb"))
        fs.set_group(nested_parties_group)

        g = fs.get_group(539)  # Get group from FieldSet
        assert g == nested_parties_group

        ng = g[0].get_group(804)  # Get nested group from first instance in parent group

        # Ensure we have the correct group with the right (tag, value) pairs.
        assert len(ng[0]) == 2
        assert ng[0].get(545) == b"d"
        assert ng[0].get(805) == b"e"


class TestGroupInstance:
    def test_init(self):
        gi = GroupInstance((1, b"a"), (2, b"bb"))
        assert len(gi) == 2


class TestGroup:
    def test_repr(self, routing_id_group):
        assert (
            repr(routing_id_group)
            == "(215, b'2'):((216, b'a'), (217, b'b')), ((216, b'a'), (217, b'b'))"
        )

    def test_str(self, routing_id_group):
        assert (
            str(routing_id_group)
            == "(NoRoutingIDs, b'2'):((RoutingType, b'a'), (RoutingID, b'b')), ((RoutingType, b'a'), (RoutingID, b'b'))"
        )

    def test_raw(self, routing_id_group):
        assert routing_id_group.raw == b"215=2\x01216=a\x01217=b\x01216=a\x01217=b\x01"

    def test_tag_getter(self, routing_id_group):
        assert routing_id_group.tag == 215

    def test_value_getter(self, routing_id_group):
        assert routing_id_group.value == b"2"

    def test_size_getter(self, routing_id_group):
        assert routing_id_group.size == 2
        assert len(routing_id_group) == routing_id_group.size
