from unittest import mock

import pytest
from unsync import Unfuture

from wtfix.apps.admin import HeartbeatApp
from wtfix.core.exceptions import MessageProcessingError
from wtfix.message import admin
from wtfix.message.admin import TestRequest, Heartbeat
from wtfix.protocol.common import Tag


class TestHeartbeatApp:
    @pytest.mark.asyncio
    async def test_server_stops_responding_after_three_test_requests(
        self, unsync_event_loop, failing_server_heartbeat_app
    ):
        await failing_server_heartbeat_app.start(heartbeat=0, response_delay=0)

        assert failing_server_heartbeat_app.pipeline.send.call_count == 4
        assert failing_server_heartbeat_app.pipeline.stop.called

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_test_request_not_necessary(
        self, unsync_event_loop, heartbeat_app
    ):
        """Simulate normal heartbeat rythm - message just received"""
        with mock.patch.object(
            HeartbeatApp, "send_test_request", return_value=Unfuture.from_value(None)
        ) as check:
            heartbeat_app.sec_since_last_receive.return_value = 0
            await heartbeat_app.monitor_heartbeat()
            assert check.call_count == 0

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_heartbeat_exceeded(
        self, unsync_event_loop, heartbeat_app
    ):
        """Simulate normal heartbeat rythm - heartbeat exceeded since last message was received"""
        with mock.patch.object(
            HeartbeatApp, "send_test_request", return_value=Unfuture.from_value(None)
        ) as check:
            await heartbeat_app.monitor_heartbeat()
            assert check.call_count == 1

    @pytest.mark.asyncio
    async def test_send_test_request(self, unsync_event_loop, heartbeat_app):
        def simulate_heartbeat_response(message):
            heartbeat_app.on_heartbeat({Tag.TestReqID: message[Tag.TestReqID].as_str})

        heartbeat_app.pipeline.send.side_effect = simulate_heartbeat_response

        await heartbeat_app.send_test_request()
        assert not heartbeat_app._server_not_responding.is_set()

    @pytest.mark.asyncio
    async def test_send_test_request_no_response(
        self, unsync_event_loop, heartbeat_app
    ):
        await heartbeat_app.send_test_request()
        assert heartbeat_app._server_not_responding.is_set()

    def test_logon_sets_heartbeat_increment(self, heartbeat_app, logon_message):
        assert heartbeat_app._heartbeat == 0

        heartbeat_app.on_logon(logon_message)
        assert heartbeat_app._heartbeat == 30

    def test_sends_heartbeat_on_test_request(self, heartbeat_app):
        request_message = TestRequest("test123")
        heartbeat_app.on_test_request(request_message)

        heartbeat_app.pipeline.send.assert_called_with(admin.Heartbeat("test123"))

    def test_resets_request_id_when_heartbeat_received(self, heartbeat_app):
        heartbeat_message = Heartbeat("test123")
        heartbeat_app._test_request_id = "test123"

        heartbeat_app.on_heartbeat(heartbeat_message)

        assert heartbeat_app._test_request_id is None

    def test_raises_exception_on_unexpected_heartbeat(self, heartbeat_app):
        with pytest.raises(MessageProcessingError):
            heartbeat_message = Heartbeat("123test")
            heartbeat_app._test_request_id = "test123"

            heartbeat_app.on_heartbeat(heartbeat_message)

    def test_on_receive_updated_timestamp(self, heartbeat_app):
        prev_timestamp = heartbeat_app._last_receive

        heartbeat_app.on_receive(TestRequest("test123"))
        assert heartbeat_app._last_receive != prev_timestamp
