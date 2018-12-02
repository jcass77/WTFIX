import pytest

from ...message.field import Field
from ...message.fieldset import TagNotFound, InvalidGroup
from ...message.message import GenericMessage
from ..streams import MessageParser


class TestMessageParser:
    def test_handle_duplicates(self, routing_id_group, routing_id_group_pairs):
        g = MessageParser._handle_duplicates(b"216", routing_id_group_pairs, 3)
        assert g == routing_id_group

    def test_handle_duplicates_invalid(self, routing_id_group, routing_id_group_pairs):
        with pytest.raises(InvalidGroup):
            del routing_id_group_pairs[1]
            g = MessageParser._handle_duplicates(216, routing_id_group_pairs, 3)

    def test_parse(self, sdr_message):
        m = MessageParser.parse(sdr_message.raw)
        assert m.name == "SecurityDefinitionRequest"
        assert m.get(8) == "FIX.4.4"

    def test_parse_incomplete_fix_message(self):
        data = b"8=FIX.4.4\x019="
        m = MessageParser.parse(data)
        assert m is None

        data += b"5\x0135=0\x0110=161\x01"
        m = MessageParser.parse(data)

        assert m is not None
        assert m.get(8) == "FIX.4.4"
        assert m.get(9) == "5"
        assert m.get(35) == "0"
        assert m.get(10) == "161"

    def test_parse_ignores_leading_junk_pairs(self):
        m = MessageParser.parse(b"1=2\x013=4\x018=FIX.4.4\x019=5\x0135=0\x0110=161\x01")
        assert m is not None

        with pytest.raises(TagNotFound):
            assert m.get(1) is None

        with pytest.raises(TagNotFound):
            assert m.get(3) is None

        assert m.get(8) == "FIX.4.4"

    def test_parse_ignores_junk_pairs(self):
        m = MessageParser.parse(b"1=2\x013=4\x015=6\x01")
        assert m is None

    def test_parse_repeating_group(self, routing_id_group):
        m = GenericMessage((35, "a"))
        m.set_group(routing_id_group)
        m += Field(1, "a")

        m = MessageParser.parse(m.raw)

        assert m is not None
        assert m.get_group(215) is not None
        assert m.get(1) == "a"

    @pytest.mark.skip("Nested repeating groups are not currently supported :(")
    def test_parse_nested_repeating_group(self, nested_parties_group):
        m = GenericMessage((35, "a"))
        m.set_group(nested_parties_group)
        m += Field(1, "a")

        m = MessageParser.parse(m.raw)

        assert m is not None
        assert m.get_group(539) is not None
        assert m.get(1) == "a"
