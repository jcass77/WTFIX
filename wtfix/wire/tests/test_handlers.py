from ..handlers import BaseHandler


class TestBaseHandler:
    def test_load_apps(self, three_level_app_chain):
        handler = BaseHandler()
        handler.load_apps(three_level_app_chain)

        assert len(handler._installed_apps) == 3

    def test_receive(self, three_level_app_chain):
        handler = BaseHandler()
        handler.load_apps(three_level_app_chain)

        assert handler.receive("Test") == "Test r1 r2 r3"

    # def test_receive_stop(self, three_level_stop_app_chain):
    #     handler = BaseHandler()
    #     handler.load_apps(three_level_stop_app_chain)
    #
    #     # TODO: count calls to 'on_receive'
    #     assert handler.receive("Test") is None

    def test_send(self, three_level_app_chain):
        handler = BaseHandler()
        handler.load_apps(three_level_app_chain)

        assert handler.send("Test") == "Test s3 s2 s1"

    # def test_send_stop(self, three_level_stop_app_chain):
    #     handler = BaseHandler()
    #     handler.load_apps(three_level_stop_app_chain)
    #
    #     # TODO: count calls to 'on_send'
    #     assert handler.send("Test") is None
