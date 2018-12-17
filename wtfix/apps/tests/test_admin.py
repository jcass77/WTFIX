from unittest import mock

import pytest
from unsync import Unfuture

from wtfix.apps.admin import HeartbeatApp
from wtfix.protocol.common import MsgType


class TestHeartbeatApp:
    def test_monitor_heartbeat_normal(self, heartbeat_app):
        """Simulate normal heartbeat rythm - message just received"""
        with mock.patch.object(
                HeartbeatApp,
                "send_test_request",
                return_value=Unfuture.from_value(True),
        ) as check:
            heartbeat_app.sec_since_last_receive = mock.MagicMock()
            heartbeat_app.sec_since_last_receive.return_value = 0

            assert heartbeat_app.monitor_heartbeat().result() is True
            assert check.call_count == 0

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_check_server(self, unsync_event_loop, heartbeat_app):
        """Simulate receiving heartbeat from server"""
        with mock.patch.object(
            HeartbeatApp,
            "send_test_request",
            return_value=Unfuture.from_value(True),
        ) as check:
            heartbeat_app.update_last_receive_timestamp()

            assert heartbeat_app.monitor_heartbeat().result() is True
            assert check.call_count == 1

    def test_monitor_heartbeat_server_not_responding(self, heartbeat_app):
        """Simulate receiving heartbeat from server"""
        with mock.patch.object(
            HeartbeatApp,
            "send_test_request",
            return_value=Unfuture.from_value(False),
        ) as check:
            heartbeat_app.update_last_receive_timestamp()

            assert heartbeat_app.monitor_heartbeat().result() is False
            assert check.call_count == 1

    @pytest.mark.asyncio
    async def test_server_is_responding_no_response(self, unsync_event_loop, heartbeat_app):
        """Simulate no response followed by forced logout"""
        heartbeat_app.update_last_receive_timestamp()

        assert heartbeat_app.send_test_request().result() is False
        assert heartbeat_app.pipeline.send.call_count == 1
        assert heartbeat_app.pipeline.send.call_args_list[0][0][0].type == MsgType.TestRequest

        assert heartbeat_app.pipeline.stop.call_count == 1

    def test_server_is_responding_response_received(self, heartbeat_app):
        """Simulate server responding on a TestRequest"""

        heartbeat_app.is_waiting = mock.MagicMock()
        heartbeat_app.is_waiting.return_value = False
        heartbeat_app.update_last_receive_timestamp()

        assert heartbeat_app.send_test_request().result() is True
        assert heartbeat_app.pipeline.send.call_count == 1

        assert heartbeat_app.pipeline.send.call_args_list[0][0][0].type == MsgType.TestRequest
