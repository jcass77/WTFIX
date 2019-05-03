import os
from asyncio import Future
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
    """
    Basic mock pipeline that can be used to instantiate new apps in tests.

    :return: A pipeline mock with a client session initialized.
    """
    pipeline = MagicMock(BasePipeline)
    pipeline.settings = settings.default_connection

    client_session = ClientSessionApp(pipeline, new_session=True)
    client_session.sender = settings.default_connection.SENDER
    client_session.target = settings.default_connection.TARGET

    pipeline.apps = {ClientSessionApp.name: client_session}

    # Mock a future message that will allow us to await pipeline.send and pipeline.receive.
    # Only useful in situations where we are not interested in the actual message result :(
    mock_future_message = MagicMock(return_value=Future())
    mock_future_message.return_value.set_result({})

    pipeline.send = mock_future_message
    pipeline.receive = mock_future_message

    yield pipeline

    try:
        os.remove(client_session._sid_path)
    except FileNotFoundError:
        # File does not exist - skip deletion
        pass


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
def failing_server_heartbeat_app():
    """Simulates the server failing after responding to three test requests."""
    app = ZeroDelayHeartbeatTestApp(MagicMock(BasePipeline))
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
        (Tag.MsgType, MsgType.UserNotification),
        (Tag.MsgSeqNum, 1),
        (Tag.SenderCompID, settings.default_connection.SENDER),
        (Tag.SendingTime, "20181206-10:24:27.018"),
        (Tag.TargetCompID, settings.default_connection.TARGET),
        (Tag.NoLinesOfText, 1),
        (Tag.Text, "abc"),
        (Tag.EmailType, 0),
        (Tag.Subject, "Test message"),
        (Tag.EmailThreadID, faker.pyint()),
    )


@pytest.fixture
def messages(user_notification_message):
    messages = []

    for idx in range(1, 6):
        next_message = user_notification_message.copy()
        next_message.seq_num = idx
        messages.append(next_message)

    return messages
