import asyncio
from unittest.mock import Mock

import pytest
from unsync import unsync

from wtfix.apps.base import BaseApp
from wtfix.core.exceptions import StopMessageProcessing
from wtfix.core import utils
from wtfix.message.message import FIXMessage


@pytest.fixture(scope="session")
def routing_id_group_pairs(routing_id_group):
    """Returns a list of (tag, value) tuples for the repeating group"""
    group = routing_id_group
    pairs = [(utils.encode(routing_id_group.tag), routing_id_group.size)]
    for instance in group:
        pairs += [(utils.encode(tag), value) for tag, value in instance.values()]

    return pairs


def get_mock_async(return_value=None):
    """
    Create a Mock-able async class member
    """

    @unsync
    async def mock_async(*args, **kwargs):
        return return_value

    return Mock(wraps=mock_async)


def get_slow_mock_async(sleep_time):
    """
    Simulate an async method that is slow to respond - useful for testing timeouts.
    """

    @unsync
    async def mock_async(*args, **kwargs):
        await asyncio.sleep(sleep_time)

    return Mock(wraps=mock_async)


class Below(BaseApp):
    name = "below"

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} r1"

        return await super().on_receive(message)

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} s1"

        return await super().on_send(message)


class Middle(BaseApp):
    name = "middle"

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} r2"

        return await super().on_receive(message)

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} s2"

        return await super().on_send(message)


class MiddleStop(BaseApp):
    name = "middle_stop"

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        raise StopMessageProcessing()

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        raise StopMessageProcessing()


class Top(BaseApp):
    name = "top"

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} r3"

        return await super().on_receive(message)

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} s3"

        return await super().on_send(message)


@pytest.fixture(scope="session")
def three_level_app_chain():
    return [
        "wtfix.tests.conftest.Top",
        "wtfix.tests.conftest.Middle",
        "wtfix.tests.conftest.Below",
    ]


@pytest.fixture(scope="session")
def three_level_stop_app_chain():
    return [
        "wtfix.tests.conftest.Top",
        "wtfix.tests.conftest.MiddleStop",
        "wtfix.tests.conftest.Below",
    ]
