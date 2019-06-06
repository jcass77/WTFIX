import pytest

from wtfix.conf import settings
from ..field import Field
from ..message import (
    GenericMessage,
    RawMessage,
    generic_message_factory,
    OptimizedGenericMessage,
)
from wtfix.core.exceptions import ValidationError
from ...protocol.common import MsgType, Tag


class TestFixMessageMixin:
    def test_type_getter(self, generic_message_class, sdr_message_fields):
        m = generic_message_class(*sdr_message_fields)
        assert m.type == MsgType.SecurityDefinitionRequest

    def test_type_getter_none(self, generic_message_class):
        assert generic_message_class().type is None

    def test_type_getter_unknown(self, generic_message_class):
        assert generic_message_class((Tag.MsgType, "abc123")).type == "abc123"

    def test_name_getter(self, generic_message_class, sdr_message_fields):
        m = generic_message_class(*sdr_message_fields)
        assert m.name == "SecurityDefinitionRequest"

    def test_name_getter_no_type(self, generic_message_class):
        assert generic_message_class().name == "Unknown"

    def test_name_getter_unknown_type(self, generic_message_class):
        assert generic_message_class((Tag.MsgType, "abc123")).name == "Unknown"

    def test_seq_num(self, generic_message_class, sdr_message_fields):
        m = generic_message_class(*sdr_message_fields)
        assert m.seq_num == 1

    def test_seq_num_getter_defaults_to_none(self, generic_message_class):
        m = generic_message_class((35, "a"), (2, "bb"))
        assert m.seq_num is None

    def test_sender_id_getter(self, generic_message_class, sdr_message_fields):
        m = generic_message_class(*sdr_message_fields)
        assert m.sender_id == "SENDER"

    def test_sender_id_getter_defaults_to_none(self, generic_message_class):
        m = generic_message_class((35, "a"), (2, "bb"))
        assert m.sender_id is None

    def test_target_id_getter(self, generic_message_class, sdr_message_fields):
        m = generic_message_class(*sdr_message_fields)
        assert m.target_id == "TARGET"

    def test_target_id_getter_defaults_to_none(self, generic_message_class):
        m = generic_message_class((35, "a"), (2, "bb"))
        assert m.target_id is None

    def test_validate(self, generic_message_class, sdr_message_fields):
        m = generic_message_class(*sdr_message_fields)
        m.validate()

    def test_validate_no_msgtype_raises_exception(self, generic_message_class):
        with pytest.raises(ValidationError):
            m = generic_message_class((1, "a"), (2, "bb"))
            m.validate()

    def test_sorting(self):
        m1 = generic_message_factory((Tag.MsgSeqNum, 1))
        m2 = generic_message_factory((Tag.MsgSeqNum, 2))
        m3 = generic_message_factory((Tag.MsgSeqNum, 3))

        list_ = [m2, m3, m1]
        assert sorted(list_) == [m1, m2, m3]

    def test_sorting_not_implemented(self):
        with pytest.raises(TypeError):
            m1 = generic_message_factory((Tag.MsgSeqNum, 1))
            m2 = 2

            list_ = [m2, m1]
            sorted(list_)


class TestRawMessage:
    def test_copy(self):
        rm = RawMessage(
            message_type=MsgType.QuoteStatusRequest,
            message_seq_num=1,
            encoded_body=b"12345" + settings.SOH + b"67890" + settings.SOH,
        )

        new_rm = rm.copy()
        assert new_rm == rm

    def test_format_pretty_print_tags(self):
        rm = RawMessage(
            message_type=MsgType.QuoteStatusRequest,
            message_seq_num=1,
            encoded_body=b"12345" + settings.SOH + b"67890" + settings.SOH,
        )

        assert (
            f"{rm:t}"
            == "QuoteStatusRequest (a): {BeginString (8): FIX.4.4 | BodyLength (9): 12 | MsgType (35): a | "
            "MsgSeqNum (34): 1 | CheckSum (10): 15}, with byte-encoded content: b'12345\\x0167890\\x01'"
        )

    def test_str(self):
        rm = RawMessage(
            message_type=MsgType.QuoteStatusRequest,
            message_seq_num=1,
            encoded_body=b"12345" + settings.SOH + b"67890" + settings.SOH,
        )

        assert (
            str(rm) == "a: {(8, FIX.4.4) | (9, 12) | (35, a) | "
            "(34, 1) | (10, 15)}, with byte-encoded content: b'12345\\x0167890\\x01'"
        )


class TestGenericMessage:
    def test_copy(self):
        m = GenericMessage((35, "a"), (2, "bb"))

        new_m = m.copy()
        assert new_m == m

    def test_add_returns_message_instance(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        m += Field(3, "ccc")

        assert isinstance(m, GenericMessage)

    def test_format_pretty_print_tags(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        m += Field(3, "ccc")

        assert (
            f"{m:t}"
            == "QuoteStatusRequest (a): [MsgType (35): a | AdvId (2): bb | AdvRefID (3): ccc]"
        )

    def test_str(self):
        m = GenericMessage((35, "a"), (2, "bb"))
        m += Field(3, "ccc")

        assert str(m) == "a: [(35, a) | (2, bb) | (3, ccc)]"


class TestOptimizedGenericMessage:
    def test_copy(self):
        m = OptimizedGenericMessage(
            (35, "a"), (2, 2), (3, "b"), (3, "c"), group_templates={2: {"*": [3]}}
        )

        new_m = m.copy()
        assert new_m == m


def test_message_factory_returns_optimized_message_by_default():
    m = generic_message_factory((1, "a"), (2, "b"))
    assert isinstance(m, OptimizedGenericMessage)


def test_message_factory_falls_back_to_generic_if_no_group_template_is_defined():
    m = generic_message_factory((1, "a"), (1, "b"))
    assert isinstance(m, GenericMessage)


def test_message_factory_uses_group_template_to_create_optimized_messages():
    m = generic_message_factory(
        (35, "a"), (2, 2), (3, "b"), (3, "c"), group_templates={2: {"a": [3]}}
    )
    assert isinstance(m, OptimizedGenericMessage)
