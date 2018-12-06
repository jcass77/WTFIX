import pytest

from wtfix.app.base import BaseApp
from ...protocol import utils


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

    def on_receive(self, message):
        return f"{message} r1"

    def on_send(self, message):
        return f"{message} s1"


class Middle(BaseApp):
    name = "middle"

    def on_receive(self, message):
        return f"{message} r2"

    def on_send(self, message):
        return f"{message} s2"


class MiddleStop(BaseApp):
    name = "middle_stop"

    def on_receive(self, message):
        return None

    def on_send(self, message):
        return None


class Top(BaseApp):
    name = "top"

    def on_receive(self, message):
        return f"{message} r3"

    def on_send(self, message):
        return f"{message} s3"


@pytest.fixture(scope="session")
def three_level_app_chain():
    return [
        "wtfix.wire.tests.conftest.Below",
        "wtfix.wire.tests.conftest.Middle",
        "wtfix.wire.tests.conftest.Top",
    ]


@pytest.fixture(scope="session")
def three_level_stop_app_chain():
    return [
        "wtfix.wire.tests.conftest.Below",
        "wtfix.wire.tests.conftest.MiddleStop",
        "wtfix.wire.tests.conftest.Top",
    ]
