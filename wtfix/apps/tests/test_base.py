import asyncio
from unittest import mock
from collections import Counter

import pytest
from unsync import unsync

from wtfix.apps.base import BaseApp
from wtfix.core.exceptions import ValidationError, MessageProcessingError
from wtfix.pipeline import BasePipeline

from wtfix.message.message import generic_message_factory
from wtfix.apps.base import on
from wtfix.apps.base import MessageTypeHandlerApp


class TestBaseApp:
    class MockApp(MessageTypeHandlerApp):
        name = "mock_app"

    def test_raises_exception_on_init_if_app_name_not_defined(self):
        with pytest.raises(ValidationError):
            BaseApp(mock.MagicMock(BasePipeline))

    def test_str(self):

        app = self.MockApp("mock_app")
        app.name = "mock_app"

        assert str(app) == "mock_app"


class MockApp(MessageTypeHandlerApp):
    name = "mock_app"

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)

        self.counter = Counter()

    @unsync
    @on("a")
    async def on_a(self, message):
        self.counter["a"] += 1

        return message

    @unsync
    @on("z")
    async def on_z(self, message):
        pass

    @unsync
    async def on_unhandled(self, message):

        self.counter["unhandled"] += 1

        return message


class TestMessageTypeHandlerApp:
    @pytest.mark.asyncio
    async def test_on_receive_handler(self, unsync_event_loop):

        app = MockApp("mock_app")

        await app.on_receive(generic_message_factory((35, "a")))
        await app.on_receive(generic_message_factory((35, "b")))

        await asyncio.sleep(
            0.1
        )  # Nothing to await. Sleep to give processes time to complete.

        assert app.counter["a"] == 1
        assert app.counter["b"] == 0
        assert app.counter["unhandled"] == 1

    @pytest.mark.asyncio
    async def test_on_receive_handler_raises_exception_if_message_not_returned(
        self, unsync_event_loop
    ):
        with pytest.raises(MessageProcessingError):
            app = MockApp("mock_app")
            await app.on_receive(generic_message_factory((35, "z")))

            await asyncio.sleep(0.1)
