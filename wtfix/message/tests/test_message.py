import pytest

from ..message import GenericMessage, ValidationError
from ...protocol.base import MsgType


class TestGenericMessage:
    def test_type_getter(self, sdr_message):
        assert sdr_message.type == MsgType.SecurityDefinitionRequest

    def test_name_getter(self, sdr_message):
        assert sdr_message.name == "SecurityDefinitionRequest"

    def test_seq_num(self, sdr_message):
        assert sdr_message.seq_num == 1

    def test_sender_id(self, sdr_message):
        assert sdr_message.sender_id == "SENDER"

    def test_target_id(self, sdr_message):
        assert sdr_message.target_id == "TARGET"

    def test_raw(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        assert m.raw == b"8=FIX.4.4\x019=5\x0135=a\x012=bb\x0110=8\x01"

    def test_raw_invalid(self):
        with pytest.raises(ValidationError):
            GenericMessage((1, "a"), (2, "b")).raw

    def test_raw_nested_group(self, nested_parties_group):
        m = GenericMessage((35, "a"), (2, "bb"))
        m.set_group(nested_parties_group)

        assert (
            m.raw
            == b"8=FIX.4.4\x019=117\x0135=a\x012=bb\x01" +  # Header
               b"539=2\x01" +  # Group identifier
               b"524=a\x01525=aa\x01538=aaa\x01" +  # First group
               b"804=2\x01545=c\x01805=cc\x01545=d\x01805=dd\x01" +  # First nested group
               b"524=b\x01525=bb\x01538=bbb\x01" +  # Second group
               b"804=2\x01545=e\x01805=ee\x01545=f\x01805=ff\x01" +  # Second nested group
               b"10=219\x01"
        )

    def test_validate(self, sdr_message):
        sdr_message.validate()

    def test_validate_no_msgtype_raises_exception(self, sdr_message):
        with pytest.raises(ValidationError):
            m = GenericMessage((1, "a"), (2, "bb"))
            m.validate()

    def test_checksum(self):
        # Test with real message sent by ROFEX demo
        assert (
            GenericMessage._checksum(
                b"8=FIXT.1.1\x01",
                b"9=75\x01",
                b"35=A\x01",
                b"34=1\x01",
                b"49=ROFX\x01",
                b"52=20170417-18:29:09.599\x01",
                b"56=eco\x0198=0\x01",
                b"108=20\x01",
                b"141=Y\x01",
                b"1137=9\x01",
            )
            == 79
        )

    def test_clear(self, sdr_message):
        sdr_message.clear()
        assert len(sdr_message) == 0
