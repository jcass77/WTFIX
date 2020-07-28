from unittest import mock

import pytest
from faker import Faker

from wtfix.apps.admin import HeartbeatApp
from wtfix.apps.parsers import RawMessageParserApp
from wtfix.apps.wire import EncoderApp, DecoderApp
from wtfix.conf import settings
from wtfix.message.admin import HeartbeatMessage
from wtfix.message.message import generic_message_factory
from wtfix.protocol.contextlib import connection


@pytest.fixture
def encoder_app(base_pipeline):
    return EncoderApp(base_pipeline)


@pytest.fixture
def decoder_app(base_pipeline):
    return DecoderApp(base_pipeline)


@pytest.fixture
def raw_msg_parser_app(base_pipeline):
    return RawMessageParserApp(base_pipeline)


class ZeroDelayHeartbeatTestApp(HeartbeatApp):
    """Heartbeat app with all delays set low for faster tests."""

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self.seconds_to_next_check = mock.MagicMock()
        self.seconds_to_next_check.return_value = 0

    @property
    def heartbeat_interval(self):
        return 0.1

    @property
    def test_request_response_delay(self):
        return 0.1


@pytest.fixture
def zero_heartbeat_app(base_pipeline):
    return ZeroDelayHeartbeatTestApp(base_pipeline)


@pytest.fixture
def failing_server_heartbeat_app(base_pipeline):
    """Simulates the server failing after responding to three test requests."""
    app = ZeroDelayHeartbeatTestApp(base_pipeline)
    num_responses = 0

    async def simulate_heartbeat_response(message):
        nonlocal num_responses

        if num_responses < 3:
            await app.on_heartbeat(HeartbeatMessage(str(message.TestReqID)))
        num_responses += 1

    app.pipeline.send.side_effect = simulate_heartbeat_response

    return app


@pytest.fixture
def user_notification_message():
    faker = Faker()

    return generic_message_factory(
        (connection.protocol.Tag.MsgType, connection.protocol.MsgType.UserNotification),
        (connection.protocol.Tag.MsgSeqNum, 1),
        (
            connection.protocol.Tag.SenderCompID,
            settings.CONNECTIONS[connection.name]["SENDER"],
        ),
        (connection.protocol.Tag.SendingTime, "20181206-10:24:27.018"),
        (
            connection.protocol.Tag.TargetCompID,
            settings.CONNECTIONS[connection.name]["TARGET"],
        ),
        (connection.protocol.Tag.NoLinesOfText, 1),
        (connection.protocol.Tag.Text, "abc"),
        (connection.protocol.Tag.EmailType, 0),
        (connection.protocol.Tag.Subject, "Test message"),
        (connection.protocol.Tag.EmailThreadID, faker.pyint()),
    )


@pytest.fixture
def messages(user_notification_message):
    messages = []

    for idx in range(1, 6):
        next_message = user_notification_message.copy()
        next_message.seq_num = idx
        messages.append(next_message)

    return messages
