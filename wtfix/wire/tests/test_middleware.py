from collections import Counter

from ...message.message import GenericMessage
from ..middleware import ByMessageTypeMiddleware, on


class MockMiddleware(ByMessageTypeMiddleware):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)

        self.counter = Counter()

    @on("a")
    def on_a(self, _message):
        self.counter["a"] += 1

    def on_unhandled(self, _message):
        self.counter["unhandled"] += 1


class TestByMessageTypeMiddleware:
    def test_on_receive_handler(self):

        mw = MockMiddleware("mock_middleware")

        mw.on_receive(GenericMessage((35, "a")))
        mw.on_receive(GenericMessage((35, "b")))

        assert mw.counter["a"] == 1
        assert mw.counter["b"] == 0
        assert mw.counter["unhandled"] == 1
