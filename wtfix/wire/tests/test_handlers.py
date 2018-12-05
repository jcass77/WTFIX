from ..handlers import BaseHandler


class TestBaseHandler:
    def test_load_middleware(self, three_level_middleware):
        handler = BaseHandler()
        handler.load_middleware(three_level_middleware)

        assert len(handler._middleware) == 3

    def test_receive(self, three_level_middleware):
        handler = BaseHandler()
        handler.load_middleware(three_level_middleware)

        assert handler.receive("Test") == "Test r1 r2 r3"

    def test_receive_stop(self, three_level_stop_middleware):
        handler = BaseHandler()
        handler.load_middleware(three_level_stop_middleware)

        # TODO: count calls to 'on_receive'
        assert handler.receive("Test") is None

    def test_send(self, three_level_middleware):
        handler = BaseHandler()
        handler.load_middleware(three_level_middleware)

        assert handler.send("Test") == "Test s3 s2 s1"

    def test_send_stop(self, three_level_stop_middleware):
        handler = BaseHandler()
        handler.load_middleware(three_level_stop_middleware)

        # TODO: count calls to 'on_send'
        assert handler.send("Test") is None
