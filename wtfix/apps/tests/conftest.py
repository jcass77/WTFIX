from unittest.mock import MagicMock

import pytest

from wtfix.apps.wire import EncoderApp, DecoderApp
from wtfix.pipeline import BasePipeline


@pytest.fixture(scope="session")
def encoder_app():
    return EncoderApp(MagicMock(BasePipeline))


@pytest.fixture
def decoder_app():
    return DecoderApp(MagicMock(BasePipeline))
