from unittest import mock
from collections import Counter

import pytest

from wtfix.apps.base import BaseApp
from wtfix.core.exceptions import ValidationError
from wtfix.pipeline import BasePipeline

from wtfix.message.message import GenericMessage
from wtfix.apps.base import on
from wtfix.apps.base import MessageTypeHandlerApp


class TestBaseApp:
    def test_check_name(self):
        with pytest.raises(ValidationError):
            BaseApp(mock.MagicMock(BasePipeline))


class MockApp(MessageTypeHandlerApp):
    name = "mock_app"

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)

        self.counter = Counter()

    @on("a")
    def on_a(self, _message):
        self.counter["a"] += 1

    def on_unhandled(self, _message):
        self.counter["unhandled"] += 1


class TestMessageTypeHandlerApp:
    def test_on_receive_handler(self):

        app = MockApp("mock_app")

        app.on_receive(GenericMessage((35, "a")))
        app.on_receive(GenericMessage((35, "b")))

        assert app.counter["a"] == 1
        assert app.counter["b"] == 0
        assert app.counter["unhandled"] == 1
