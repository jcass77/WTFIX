from unittest import mock
from unittest.mock import MagicMock

import pytest

from wtfix.apps.admin import HeartbeatApp
from wtfix.apps.parsers import RawMessageParserApp
from wtfix.apps.wire import EncoderApp, DecoderApp
from wtfix.pipeline import BasePipeline
from wtfix.protocol.common import Tag


@pytest.fixture(scope="session")
def encoder_app():
    return EncoderApp(MagicMock(BasePipeline))


@pytest.fixture
def decoder_app():
    return DecoderApp(MagicMock(BasePipeline))


@pytest.fixture
def raw_msg_parser_app():
    return RawMessageParserApp(MagicMock(BasePipeline))


class HeartbeatTestApp(HeartbeatApp):
    """Heartbeat app with all delays set to zero for test purposes."""

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self._heartbeat = 0
        self._test_request_response_delay = 0

        self.sec_since_last_receive = mock.MagicMock()
        self.sec_since_last_receive.return_value = 1


@pytest.fixture
def heartbeat_app():
    return HeartbeatTestApp(MagicMock(BasePipeline))


@pytest.fixture
def failing_server_heartbeat_app():
    """Simulates the server failing after responding to three test requests."""
    app = HeartbeatTestApp(MagicMock(BasePipeline))
    num_responses = 0

    def simulate_heartbeat_response(message):
        nonlocal num_responses

        if num_responses < 3:
            app.on_heartbeat({Tag.TestReqID: message[Tag.TestReqID].as_str})
        num_responses += 1

    app.pipeline.send.side_effect = simulate_heartbeat_response

    return app
