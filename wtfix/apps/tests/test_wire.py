from datetime import datetime

import pytest

from wtfix.apps.wire import DecoderApp
from wtfix.conf import settings
from wtfix.core.exceptions import ValidationError, ParsingError
from wtfix.message.message import generic_message_factory
from wtfix.core import utils
from wtfix.protocol.contextlib import connection


class TestEncoderApp:
    def test_encode_message(self, logon_message, encoder_app):
        # Skip timestamp, which will always change.
        assert encoder_app.encode_message(logon_message).startswith(
            b"8=FIX.4.4\x019=99\x0135=A\x0134=1\x0149=SENDER\x01"
        )

        # Compare remainder, skipping checksum which will change based on timestamp
        assert encoder_app.encode_message(logon_message)[:-7].endswith(
            b"56=TARGET\x0198=0\x01108=30\x01553=USERNAME\x01554=PASSWORD\x01141=Y\x01"
        )

    def test_encode_message_invalid(self, encoder_app):
        with pytest.raises(ValidationError):
            encoder_app.encode_message(generic_message_factory((1, "a"), (2, "b")))

    def test_encode_message_nested_group(self, encoder_app, nested_parties_group):
        m = generic_message_factory((35, "a"), (34, 1), (2, "bb"))
        m[nested_parties_group.tag] = nested_parties_group
        m.SendingTime = datetime.utcnow().strftime(settings.DATETIME_FORMAT)[:-3]

        # Compare just the group-related bytes.
        assert encoder_app.encode_message(m)[82:-7] == (
            b"539=2\x01"  # Header
            + b"524=a\x01525=aa\x01538=aaa\x01"  # Group identifier
            + b"804=2\x01545=c\x01805=cc\x01545=d\x01805=dd\x01"  # First group
            + b"524=b\x01525=bb\x01538=bbb\x01"  # First nested group
            + b"804=2\x01545=e\x01805=ee\x01545=f\x01805=ff\x01"  # Second group
        )  # Second nested group


class TestDecoderApp:
    def test_check_begin_string(self, simple_encoded_msg):
        assert DecoderApp.check_begin_string(simple_encoded_msg) == (b"FIX.4.4", 9)

    def test_check_begin_string_not_found_raises_exception(self, simple_encoded_msg):
        with pytest.raises(ParsingError):
            DecoderApp.check_begin_string(simple_encoded_msg[10:])

    def test_check_begin_string_not_at_start_raises_exception(self, simple_encoded_msg):
        with pytest.raises(ParsingError):
            DecoderApp.check_begin_string(b"34=0" + settings.SOH + simple_encoded_msg)

    def test_check_body_length(self, simple_encoded_msg):
        assert DecoderApp.check_body_length(
            simple_encoded_msg, start=0, body_end=19
        ) == (5, 13)

    def test_check_body_length_body_end_not_provided(self, simple_encoded_msg):
        assert DecoderApp.check_body_length(simple_encoded_msg) == (5, 13)

    def test_body_length_not_found_raises_exception(self, simple_encoded_msg):
        with pytest.raises(ParsingError):
            encoded_msg = simple_encoded_msg[:9] + simple_encoded_msg[13:]
            DecoderApp.check_body_length(encoded_msg)

    def test_check_body_length_wrong_length_raises_exception(self, simple_encoded_msg):
        with pytest.raises(ParsingError):
            encoded_msg = b"8=FIX.4.4\x019=1\x0135=0\x0110=161\x01"
            assert DecoderApp.check_body_length(encoded_msg) == (b"5", 9, 13)

    def test_check_checksum(self, simple_encoded_msg):
        checksum, _ = DecoderApp.check_checksum(simple_encoded_msg)
        assert checksum == 163

    def test_check_checksum_not_found_raises_exception(self, simple_encoded_msg):
        with pytest.raises(ParsingError):
            encoded_msg = simple_encoded_msg[:-7]
            DecoderApp.check_checksum(encoded_msg)

    def test_check_checksum_trailing_bytes_raises_exception(self, simple_encoded_msg):
        with pytest.raises(ParsingError):
            message = simple_encoded_msg + b"34=1" + settings.SOH
            DecoderApp.check_checksum(message)

    def test_check_checksum_raises_exception_if_checksum_invalid(
        self, simple_encoded_msg
    ):
        with pytest.raises(ParsingError):
            encoded_msg = simple_encoded_msg[:-4] + b"123" + settings.SOH
            DecoderApp.check_checksum(encoded_msg, 0, 19)

    def test_decode_message(
        self, encoder_app, decoder_app, generic_message_class, sdr_message_fields
    ):
        m = generic_message_class(*sdr_message_fields)
        m = decoder_app.decode_message(encoder_app.encode_message(m))
        assert m.BeginString == "FIX.4.4"
        assert int(m.BodyLength) == 113
        assert m.MsgType == "c"
        assert int(m.MsgSeqNum) == 1
        # Compare body, skipping timestamp and checksum
        assert m.encoded_body[:13] == b"49=SENDER\x0152="
        assert (
            m.encoded_body[35:]
            == b"56=TARGET\x0155=^.*$\x01167=CS\x01320=37a0b5c8afb543ec8f29eca2a44be2ec\x01321=3\x01"
        )

    def test_decode_message_raises_exception_if_no_beginstring(
        self, encoder_app, decoder_app
    ):
        with pytest.raises(ParsingError):
            m = generic_message_factory(
                (
                    connection.protocol.Tag.MsgType,
                    connection.protocol.MsgType.TestRequest,
                ),
                (connection.protocol.Tag.MsgSeqNum, 1),
                (connection.protocol.Tag.TestReqID, "a"),
                (
                    connection.protocol.Tag.SendingTime,
                    datetime.utcnow().strftime(settings.DATETIME_FORMAT)[:-3],
                ),
            )
            data = encoder_app.encode_message(m).replace(
                b"8=" + utils.encode(settings.BEGIN_STRING), b""
            )
            decoder_app.decode_message(data)

    def test_decode_message_raises_exception_on_leading_junk(self, decoder_app):
        with pytest.raises(ParsingError):
            decoder_app.decode_message(
                b"1=2\x013=4\x018=FIX.4.4\x019=5\x0135=0\x0110=161\x01"
            )
