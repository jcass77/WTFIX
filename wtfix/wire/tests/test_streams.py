import pytest

from ...message.field import Field
from ...message.fieldset import TagNotFound
from ...message.message import GenericMessage
from ..streams import MessageParser, ParsingError


class TestMessageParser:
    def test_parse(self, sdr_message):
        m = MessageParser().parse(sdr_message.raw)
        assert m.name == "SecurityDefinitionRequest"
        assert m[8].value == "FIX.4.4"

    def test_parse_raises_exception_if_no_beginstring(self):
        with pytest.raises(ParsingError):
            m = GenericMessage((35, 7), (9, "a"))
            data = m.raw.replace(b"8=" + m.begin_string, b"")
            MessageParser().parse(data)

    def test_parse_raises_exception_if_no_checksum(self):
        with pytest.raises(ParsingError):
            m = GenericMessage((35, 7), (9, "a"))
            data = m.raw
            data = data[:data.find(b"10=")]
            MessageParser().parse(data)

    def test_parse_ignores_leading_junk_pairs(self):
        m = MessageParser().parse(b"1=2\x013=4\x018=FIX.4.4\x019=5\x0135=0\x0110=161\x01")

        with pytest.raises(TagNotFound):
            assert m[1] is None

        with pytest.raises(TagNotFound):
            assert m[3] is None

        assert m[8].value == "FIX.4.4"

    def test_parse_ignores_junk_pairs(self):
        with pytest.raises(ParsingError):
            MessageParser().parse(b"1=2\x013=4\x015=6\x01")

    @pytest.mark.skip("Repeating groups are not currently supported :(")
    def test_parse_repeating_group(self, routing_id_group):
        m = GenericMessage((35, "a"))
        m.set_group(routing_id_group)
        m += Field(1, "a")

        m = MessageParser().parse(m.raw)

        assert m is not None
        assert m.get_group(215) is not None
        assert m[1].value == "a"

    @pytest.mark.skip("Nested repeating groups are not currently supported :(")
    def test_parse_nested_repeating_group(self, nested_parties_group):
        m = GenericMessage((35, "a"))
        m.set_group(nested_parties_group)
        m += Field(1, "a")

        m = MessageParser().parse(m.raw)

        assert m is not None
        assert m.get_group(539) is not None
        assert m[1].value == "a"