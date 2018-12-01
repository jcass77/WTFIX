import pytest

from wtfix.message.fieldset import FieldSet
from ..message import BaseMessage, ValidationError
from ...protocol.base import MsgType


class TestBaseMessage:
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
        m = BaseMessage((35, b"a"), (2, b"bb"))
        assert m.raw == b"8=FIX.4.4\x019=5\x0135=a\x012=bb\x0110=8\x01"

    def test_raw_invalid(self):
        with pytest.raises(ValidationError):
            BaseMessage((1, b"a"), (2, b"b")).raw

    # def test_to_raw_nested_group(self, nested_parties_group):
    #     m = BaseMessage((35, b"a"), (2, b"bb"))
    #     m.set_group(nested_parties_group)
    #
    #     assert m.to_raw() == ""

    def test_validate(self, sdr_message):
        sdr_message.validate()

    def test_validate_no_msgtype_raises_exception(self, sdr_message):
        with pytest.raises(ValidationError):
            m = BaseMessage((1, b"a"), (2, b"bb"))
            m.validate()

    def test_checksum(self):
        # Test with real message sent by ROFEX demo
        assert (
                BaseMessage._checksum(
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
