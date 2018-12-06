import pytest

from ...message.field import Field
from ...message.message import GenericMessage
from wtfix.core.exceptions import ValidationError, TagNotFound
from ..streams import MessageParser, ParsingError


class TestMessageParser:
    def test_add_group_template_too_short(self):
        with pytest.raises(ValidationError):
            MessageParser().add_group_template(35)

    def test_remove_group_template(self):
        mp = MessageParser()
        mp.add_group_template(215, 216, 217)

        assert 215 in mp._group_templates

        mp.remove_group_template(215)
        assert 215 not in mp._group_templates

    def test_is_template_tag(self):
        mp = MessageParser()
        mp.add_group_template(215, 216, 216)

        assert mp.is_template_tag(215) is True
        assert mp.is_template_tag(216) is True

        assert mp.is_template_tag(217) is False

    def test_parse(self, sdr_message):
        m = MessageParser().parse(sdr_message.raw)
        assert m.name == "SecurityDefinitionRequest"
        assert m[8].value_ref == "FIX.4.4"

    def test_parse_raises_exception_if_no_beginstring(self):
        with pytest.raises(ParsingError):
            m = GenericMessage((35, 7), (9, "a"))
            data = m.raw.replace(b"8=" + m.begin_string, b"")
            MessageParser().parse(data)

    def test_parse_raises_exception_if_no_checksum(self):
        with pytest.raises(ParsingError):
            m = GenericMessage((35, 7), (9, "a"))
            data = m.raw
            data = data[: data.find(b"10=")]
            MessageParser().parse(data)

    def test_parse_ignores_leading_junk_pairs(self):
        m = MessageParser().parse(
            b"1=2\x013=4\x018=FIX.4.4\x019=5\x0135=0\x0110=161\x01"
        )

        with pytest.raises(TagNotFound):
            assert m[1] is None

        with pytest.raises(TagNotFound):
            assert m[3] is None

        assert m[8].value_ref == "FIX.4.4"

    def test_parse_ignores_junk_pairs(self):
        with pytest.raises(ParsingError):
            MessageParser().parse(b"1=2\x013=4\x015=6\x01")

    def test_parse_detects_duplicate_tags_without_template(self, routing_id_group):
        m = GenericMessage((35, "a"))
        m.set_group(routing_id_group)
        m += Field(1, "a")

        with pytest.raises(ParsingError):
            MessageParser().parse(m.raw)

    def test_parse_repeating_group(self, routing_id_group):
        m = GenericMessage((35, "a"))
        m.set_group(routing_id_group)
        m += Field(1, "a")

        mp = MessageParser()
        mp.add_group_template(215, 216, 217)
        m = mp.parse(m.raw)

        assert 215 in m
        assert m[1].value_ref == "a"

        group = m.get_group(215)
        assert group.size == 2

        assert len(group[0]) == 2
        assert group[0][216] == "a"
        assert group[0][217] == "b"

        assert len(group[0]) == 2
        assert group[1][216] == "c"
        assert group[1][217] == "d"

    def test_parse_nested_repeating_group(self, nested_parties_group):
        m = GenericMessage((35, "a"))
        m.set_group(nested_parties_group)
        m += Field(1, "a")

        mp = MessageParser()
        mp.add_group_template(539, 524, 525, 538)
        mp.add_group_template(804, 545, 805)

        mp.parse(m.raw)

        group = m.get_group(539)
        assert group.size == 2

        group_instance_1 = group[0]
        assert len(group_instance_1) == 8

        nested_group_1 = group_instance_1[804]
        assert len(nested_group_1) == 5

        nested_instance_1 = nested_group_1[0]
        assert len(nested_instance_1) == 2
        assert nested_instance_1[805] == "cc"

        assert m[1].value_ref == "a"
