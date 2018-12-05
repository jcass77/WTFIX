import pytest

from ..middleware import BaseMiddleware
from ...protocol import utils


@pytest.fixture(scope="session")
def routing_id_group_pairs(routing_id_group):
    """Returns a list of (tag, value) tuples for the repeating group"""
    group = routing_id_group
    pairs = [(utils.encode(routing_id_group.tag), routing_id_group.size)]
    for instance in group:
        pairs += [(utils.encode(tag), value) for tag, value in instance.values()]

    return pairs


@pytest.fixture(scope="session")
def three_level_middleware():
    class Below(BaseMiddleware):
        def on_receive(self, message):
            return f"{message} r1"

        def on_send(self, message):
            return f"{message} s1"

    class Middle(BaseMiddleware):
        def on_receive(self, message):
            return f"{message} r2"

        def on_send(self, message):
            return f"{message} s2"

    class Top(BaseMiddleware):
        def on_receive(self, message):
            return f"{message} r3"

        def on_send(self, message):
            return f"{message} s3"

    return [Below("below"), Middle("middle"), Top("top")]


@pytest.fixture(scope="session")
def three_level_stop_middleware():
    class Below(BaseMiddleware):
        def on_receive(self, message):
            return f"{message} r1"

        def on_send(self, message):
            return f"{message} s1"

    class Middle(BaseMiddleware):
        def on_receive(self, message):
            return None

        def on_send(self, message):
            return None

    class Top(BaseMiddleware):
        def on_receive(self, message):
            return f"{message} r3"

        def on_send(self, message):
            return f"{message} s3"

    return [Below("below"), Middle("middle"), Top("top")]
