import pytest

from ..field import Field
from ..message import GenericMessage
from wtfix.core.exceptions import ValidationError
from ...protocol.common import MsgType, Tag


class TestGenericMessage:
    def test_add_returns_message_instance(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        m += Field(3, "ccc")

        assert isinstance(m, GenericMessage)

    def test_type_getter(self, sdr_message):
        assert sdr_message.type == MsgType.SecurityDefinitionRequest

    def test_type_getter_none(self):
        assert GenericMessage().type is None

    def test_type_getter_unknown(self):
        assert GenericMessage((Tag.MsgType, "abc123")).type == "abc123"

    def test_name_getter(self, sdr_message):
        assert sdr_message.name == "SecurityDefinitionRequest"

    def test_name_getter_no_type(self):
        assert GenericMessage().name == "Unknown"

    def test_name_getter_unknown_type(self):
        assert GenericMessage((Tag.MsgType, "abc123")).name == "Unknown"

    def test_seq_num(self, sdr_message):
        assert sdr_message.seq_num == 1

    def test_sender_id_getter(self, sdr_message):
        assert sdr_message.sender_id == "SENDER"

    def test_sender_id_getter_default(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        assert m.sender_id == "SENDER_ENV_VAR"

    def test_target_id_getter(self, sdr_message):
        assert sdr_message.target_id == "TARGET"

    def test_target_id_getter_default(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        assert m.target_id == "TARGET_ENV_VAR"

    def test_validate(self, sdr_message):
        sdr_message.validate()

    def test_validate_no_msgtype_raises_exception(self, sdr_message):
        with pytest.raises(ValidationError):
            m = GenericMessage((1, "a"), (2, "bb"))
            m.validate()

    def test_clear(self, sdr_message):
        sdr_message.clear()
        assert len(sdr_message) == 0
