from unittest import mock

from wtfix.apps.admin import HeartbeatApp
from wtfix.pipeline import BasePipeline
from wtfix.protocol.common import MsgType
from wtfix.tests.conftest import mock_unfuture_result


class TestHeartbeatApp:
    def test_monitor_heartbeat_normal(self):
        """Simulate normal heartbeat rythm - message just received"""
        with mock.patch.object(
                HeartbeatApp,
                "check_server_is_responding",
                return_value=mock_unfuture_result(True),
        ) as check:
            app = HeartbeatApp(mock.MagicMock(BasePipeline))
            app._heartbeat = 0
            app.sec_since_last_receive = mock.MagicMock()
            app.sec_since_last_receive.return_value = 0

            assert app.monitor_heartbeat().result() is True
            assert check.call_count == 0

    def test_monitor_heartbeat_check_server(self):
        """Simulate receiving heartbeat from server"""
        with mock.patch.object(
            HeartbeatApp,
            "check_server_is_responding",
            return_value=mock_unfuture_result(True),
        ) as check:

            app = HeartbeatApp(mock.MagicMock(BasePipeline))
            app._heartbeat = 0
            app.update_last_receive_timestamp()

            assert app.monitor_heartbeat().result() is True
            assert check.call_count == 1

    def test_monitor_heartbeat_server_not_responding(self):
        """Simulate receiving heartbeat from server"""
        with mock.patch.object(
            HeartbeatApp,
            "check_server_is_responding",
            return_value=mock_unfuture_result(False),
        ) as check:

            app = HeartbeatApp(mock.MagicMock(BasePipeline))
            app._heartbeat = 0
            app.update_last_receive_timestamp()

            assert app.monitor_heartbeat().result() is False
            assert check.call_count == 1

    def test_server_is_responding_no_response(self):
        """Simulate no response followed by forced logout"""
        pipeline_mock = mock.MagicMock(BasePipeline)
        send_mock = pipeline_mock.send

        app = HeartbeatApp(pipeline_mock)
        app._heartbeat = 0
        app.update_last_receive_timestamp()

        assert app.check_server_is_responding().result() is False
        assert send_mock.call_count == 2

        assert send_mock.call_args_list[0][0][0].type == MsgType.TestRequest
        assert send_mock.call_args_list[1][0][0].type == MsgType.Logout

    def test_server_is_responding_response_received(self):
        """Simulate server responding on a TestRequest"""
        pipeline_mock = mock.MagicMock(BasePipeline)
        send_mock = pipeline_mock.send

        app = HeartbeatApp(pipeline_mock)
        app.is_waiting = mock.MagicMock()
        app.is_waiting.return_value = False
        app._heartbeat = 0
        app.update_last_receive_timestamp()

        assert app.check_server_is_responding().result() is True
        assert send_mock.call_count == 1

        assert send_mock.call_args_list[0][0][0].type == MsgType.TestRequest
