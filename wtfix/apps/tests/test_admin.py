import asyncio
from unittest import mock
from unittest.mock import MagicMock

import pytest
from unsync import Unfuture

from wtfix.apps.admin import HeartbeatApp
from wtfix.core.exceptions import MessageProcessingError
from wtfix.message import admin
from wtfix.message.admin import TestRequest, Heartbeat
from wtfix.pipeline import BasePipeline
from wtfix.protocol.common import Tag


class TestHeartbeatApp:
    def test_heartbeat_getter_defaults_to_30(self):
        heartbeat_app = HeartbeatApp(MagicMock(BasePipeline))
        assert heartbeat_app.heartbeat == 30

    @pytest.mark.asyncio
    async def test_server_stops_responding_after_three_test_requests(
        self, unsync_event_loop, failing_server_heartbeat_app
    ):
        await failing_server_heartbeat_app.monitor_heartbeat()

        assert failing_server_heartbeat_app.pipeline.send.call_count == 4
        assert failing_server_heartbeat_app.pipeline.stop.called

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_test_request_not_necessary(
        self, unsync_event_loop, zero_heartbeat_app
    ):
        """Simulate normal heartbeat rhythm - message just received"""
        with mock.patch.object(
            HeartbeatApp, "send_test_request", return_value=Unfuture.from_value(None)
        ) as check:

            zero_heartbeat_app.sec_since_last_receive.return_value = 0
            try:
                await asyncio.wait_for(zero_heartbeat_app.monitor_heartbeat(), 0.1)
            except asyncio.futures.TimeoutError:
                pass

            assert check.call_count == 0

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_heartbeat_exceeded(
        self, unsync_event_loop, zero_heartbeat_app
    ):
        """Simulate normal heartbeat rhythm - heartbeat exceeded since last message was received"""
        with mock.patch.object(
            HeartbeatApp, "send_test_request", return_value=Unfuture.from_value(None)
        ) as check:

            try:
                await asyncio.wait_for(zero_heartbeat_app.monitor_heartbeat(), 0.1)
            except asyncio.futures.TimeoutError:
                pass

            assert check.call_count > 1

    @pytest.mark.asyncio
    async def test_send_test_request(self, unsync_event_loop, zero_heartbeat_app):
        def simulate_heartbeat_response(message):
            zero_heartbeat_app.on_heartbeat({Tag.TestReqID: message[Tag.TestReqID].as_str})

        zero_heartbeat_app.pipeline.send.side_effect = simulate_heartbeat_response

        try:
            await asyncio.wait_for(zero_heartbeat_app.monitor_heartbeat(), 0.1)
        except asyncio.futures.TimeoutError:
            pass

        assert not zero_heartbeat_app._server_not_responding.is_set()

    @pytest.mark.asyncio
    async def test_send_test_request_no_response(
        self, unsync_event_loop, zero_heartbeat_app
    ):
        await zero_heartbeat_app.send_test_request()
        assert zero_heartbeat_app._server_not_responding.is_set()

    def test_logon_sets_heartbeat_increment(self, logon_message):
        heartbeat_app = HeartbeatApp(MagicMock(BasePipeline))

        logon_message[Tag.HeartBtInt] = 45
        heartbeat_app.on_logon(logon_message)

        assert heartbeat_app.heartbeat == 45

    def test_sends_heartbeat_on_test_request(self, zero_heartbeat_app):
        request_message = TestRequest("test123")
        zero_heartbeat_app.on_test_request(request_message)

        zero_heartbeat_app.pipeline.send.assert_called_with(admin.Heartbeat("test123"))

    def test_resets_request_id_when_heartbeat_received(self, zero_heartbeat_app):
        heartbeat_message = Heartbeat("test123")
        zero_heartbeat_app._test_request_id = "test123"

        zero_heartbeat_app.on_heartbeat(heartbeat_message)

        assert zero_heartbeat_app._test_request_id is None

    def test_raises_exception_on_unexpected_heartbeat(self, zero_heartbeat_app):
        with pytest.raises(MessageProcessingError):
            heartbeat_message = Heartbeat("123test")
            zero_heartbeat_app._test_request_id = "test123"

            zero_heartbeat_app.on_heartbeat(heartbeat_message)

    def test_on_receive_updated_timestamp(self, zero_heartbeat_app):
        prev_timestamp = zero_heartbeat_app._last_receive

        zero_heartbeat_app.on_receive(TestRequest("test123"))
        assert zero_heartbeat_app._last_receive != prev_timestamp
