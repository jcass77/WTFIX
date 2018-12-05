from ..app import BaseApp, stack


def test_stack():
    class Below(BaseApp):
        pass

    class Middle(BaseApp):
        pass

    class Above(BaseApp):
        pass

    app_stack = stack((Below, {}), (Middle, {}), (Above, {}))

    assert isinstance(app_stack, Below)
    assert app_stack.lower_app is None

    middle = app_stack.upper_app
    assert isinstance(middle, Middle)

    top = middle.upper_app
    assert isinstance(top, Above)
    assert top.upper_app is None


class TestBaseApp:
    def test_on_receive(self):
        EXPECTED_IN = "IN MESSAGE"

        class Below(BaseApp):
            pass

        class Middle(BaseApp):
            pass

        class Above(BaseApp):
            def on_receive(self, message):
                assert message == EXPECTED_IN
                return message

        app_stack = stack((Below, {}), (Middle, {}), (Above, {}))

        assert app_stack._on_receive(EXPECTED_IN) == EXPECTED_IN

    def test_on_receive_stop(self):
        EXPECTED_IN = "IN MESSAGE"

        class Below(BaseApp):
            pass

        class Middle(BaseApp):
            def on_receive(self, message):
                pass

        class Above(BaseApp):
            def on_receive(self, message):
                assert False  # Message should not bubble up to this layer.

        app_stack = stack((Below, {}), (Middle, {}), (Above, {}))

        assert app_stack._on_receive(EXPECTED_IN) is None

    def test_on_send(self):
        class Below(BaseApp):
            def _on_send(self, message):
                return f"{message} 3"

        class Middle(BaseApp):
            def _on_send(self, message):
                return f"{message} 2"

        class Above(BaseApp):
            def _on_send(self, message):
                assert message == "Test"
                return f"{message} 1"

        app_stack = stack((Below, {}), (Middle, {}), (Above, {}))

        assert app_stack.upper_app.send("Test") == "Test 1 2 3"

    # def test_on_receive_stop(self):
    #     EXPECTED_IN = "IN MESSAGE"
    #
    #     class Below(BaseApp):
    #         pass
    #
    #     class Middle(BaseApp):
    #         def on_receive(self, message):
    #             pass
    #
    #     class Above(BaseApp):
    #         def on_receive(self, message):
    #             assert False  # Message should not bubble up to this layer.
    #
    #     app_stack = stack((Below, {}), (Middle, {}), (Above, {}))
    #
    #     assert app_stack._on_receive(EXPECTED_IN) is None
