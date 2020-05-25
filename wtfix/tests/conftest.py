import pytest

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


class Below(BaseApp):
    name = "below"

    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} r1"

        return await super().on_receive(message)

    async def on_send(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} s1"

        return await super().on_send(message)


class Middle(BaseApp):
    name = "middle"

    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} r2"

        return await super().on_receive(message)

    async def on_send(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} s2"

        return await super().on_send(message)


class MiddleStop(BaseApp):
    name = "middle_stop"

    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        raise StopMessageProcessing()

    async def on_send(self, message: FIXMessage) -> FIXMessage:
        raise StopMessageProcessing()


class Top(BaseApp):
    name = "top"

    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        message.TestReqID = f"{message.TestReqID} r3"

        return await super().on_receive(message)

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
