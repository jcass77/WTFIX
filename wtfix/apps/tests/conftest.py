from unittest import mock
from unittest.mock import MagicMock

import pytest

from wtfix.apps.admin import HeartbeatApp
from wtfix.apps.parsers import BasicMessageParserApp
from wtfix.apps.wire import EncoderApp, DecoderApp
from wtfix.pipeline import BasePipeline


@pytest.fixture(scope="session")
def encoder_app():
    return EncoderApp(MagicMock(BasePipeline))


@pytest.fixture
def decoder_app():
    return DecoderApp(MagicMock(BasePipeline))


@pytest.fixture
def basic_parser_app():
    return BasicMessageParserApp(MagicMock(BasePipeline))


@pytest.fixture
def heartbeat_app():
    app = HeartbeatApp(mock.MagicMock(BasePipeline))
    app._heartbeat = 0
    app._test_request_response_delay = 0

    return app
