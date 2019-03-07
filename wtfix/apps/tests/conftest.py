from unittest import mock
from unittest.mock import MagicMock

import pytest
from faker import Faker

from wtfix.apps.admin import HeartbeatApp
from wtfix.apps.parsers import RawMessageParserApp
from wtfix.apps.sessions import ClientSessionApp
from wtfix.apps.wire import EncoderApp, DecoderApp
from wtfix.conf import settings
from wtfix.message.admin import HeartbeatMessage
from wtfix.message.message import generic_message_factory
from wtfix.pipeline import BasePipeline
from wtfix.protocol.common import Tag, MsgType


@pytest.fixture
def base_pipeline():
    pipeline = MagicMock(BasePipeline)
    pipeline.settings = settings.default_session

    pipeline.apps[ClientSessionApp.name].sender = settings.default_session.SENDER
    pipeline.apps[ClientSessionApp.name].target = settings.default_session.TARGET

    return pipeline


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
    """Heartbeat app with all delays set to zero for test purposes."""

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self.sec_since_last_receive = mock.MagicMock()
        self.sec_since_last_receive.return_value = 1

    @property
    def heartbeat(self):
        return 0

    @property
    def test_request_response_delay(self):
        return 0


@pytest.fixture
def zero_heartbeat_app():
    return ZeroDelayHeartbeatTestApp(MagicMock(BasePipeline))


@pytest.fixture
def failing_server_heartbeat_app():
    """Simulates the server failing after responding to three test requests."""
    app = ZeroDelayHeartbeatTestApp(MagicMock(BasePipeline))
    num_responses = 0

    def simulate_heartbeat_response(message):
        nonlocal num_responses

        if num_responses < 3:
            app.on_heartbeat(HeartbeatMessage(message.TestReqID.as_str))
        num_responses += 1

    app.pipeline.send.side_effect = simulate_heartbeat_response

    return app


@pytest.fixture
def user_notification_message():
    faker = Faker()

    return generic_message_factory(
        (Tag.MsgType, MsgType.UserNotification),
        (Tag.MsgSeqNum, 1),
        (Tag.SenderCompID, "SENDER"),
        (Tag.SendingTime, "20181206-10:24:27.018"),
        (Tag.TargetCompID, "TARGET"),
        (Tag.NoLinesOfText, 1),
        (Tag.Text, "abc"),
        (Tag.EmailType, 0),
        (Tag.Subject, "Test message"),
        (Tag.EmailThreadID, faker.pyint()),
    )


@pytest.fixture
def messages(user_notification_message):
    faker = Faker()
    messages = []

    for idx in range(1, 6):
        next_message = generic_message_factory(
            (Tag.MsgType, MsgType.UserNotification),
            (Tag.MsgSeqNum, idx),
            (Tag.SenderCompID, "SENDER"),
            (Tag.SendingTime, "20181206-10:24:27.018"),
            (Tag.TargetCompID, "TARGET"),
            (Tag.NoLinesOfText, 1),
            (Tag.Text, "abc"),
            (Tag.EmailType, 0),
            (Tag.Subject, "Test message"),
            (Tag.EmailThreadID, faker.pyint()),
        )

        messages.append(next_message)

    return messages
