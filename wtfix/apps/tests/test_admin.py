import asyncio
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import MagicMock

import pytest

from wtfix.apps.admin import (
    HeartbeatApp,
    SeqNumManagerApp,
    AuthenticationApp,
    HeartbeatTimers,
)
from wtfix.apps.sessions import ClientSessionApp
from wtfix.apps.store import MessageStoreApp, MemoryStore
from wtfix.conf import settings
from wtfix.core.exceptions import StopMessageProcessing, SessionError
from wtfix.message import admin
from wtfix.message.admin import TestRequestMessage, HeartbeatMessage
from wtfix.message.message import OptimizedGenericMessage
from wtfix.pipeline import BasePipeline
from wtfix.protocol.contextlib import connection


class TestAuthenticationApp:
    @pytest.mark.asyncio
    async def test_on_logon_raises_exception_on_wrong_heartbeat_response(
        self, base_pipeline
    ):
        with pytest.raises(SessionError):
            logon_msg = admin.LogonMessage("", "", heartbeat_int=60)
            logon_msg.ResetSeqNumFlag = True

            auth_app = AuthenticationApp(base_pipeline)
            await auth_app.on_logon(logon_msg)

    @pytest.mark.asyncio
    async def test_on_logon_sets_default_test_message_indicator_to_false(
        self, base_pipeline
    ):
        logon_msg = admin.LogonMessage("", "")
        logon_msg.ResetSeqNumFlag = True

        auth_app = AuthenticationApp(base_pipeline)
        await auth_app.on_logon(logon_msg)

        assert auth_app.test_mode is False

    @pytest.mark.asyncio
    async def test_on_logon_raises_exception_on_wrong_test_indicator_response(
        self, base_pipeline
    ):
        with pytest.raises(SessionError):
            logon_msg = admin.LogonMessage("", "")
            logon_msg.ResetSeqNumFlag = True
            logon_msg.TestMessageIndicator = True

            auth_app = AuthenticationApp(base_pipeline)
            await auth_app.on_logon(logon_msg)

    @pytest.mark.asyncio
    async def test_on_logon_raises_exception_on_wrong_reset_sequence_number_response(
        self, base_pipeline
    ):
        with pytest.raises(SessionError):
            logon_msg = admin.LogonMessage("", "")
            logon_msg.ResetSeqNumFlag = False

            auth_app = AuthenticationApp(base_pipeline)
            await auth_app.on_logon(logon_msg)


class TestHeartbeatApp:
    def test_heartbeat_getter_defaults_to_global_settings(self, base_pipeline):
        heartbeat_app = HeartbeatApp(base_pipeline)
        assert (
            heartbeat_app.heartbeat_interval
            == settings.CONNECTIONS[connection.name]["HEARTBEAT_INT"]
        )

    @pytest.mark.asyncio
    async def test_server_stops_responding_after_three_test_requests(
        self, failing_server_heartbeat_app
    ):
        await failing_server_heartbeat_app.heartbeat_monitor(
            HeartbeatTimers.RECEIVE, failing_server_heartbeat_app.send_test_request
        )

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert failing_server_heartbeat_app.pipeline.send.call_count == 4
        assert failing_server_heartbeat_app.pipeline.stop.called

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_test_request_not_necessary(
        self, zero_heartbeat_app
    ):
        """Simulate normal heartbeat_interval rhythm - message just received"""
        future_mock = asyncio.Future()
        future_mock.set_result(None)
        with mock.patch.object(
            HeartbeatApp, "send_test_request", return_value=future_mock
        ) as check:

            zero_heartbeat_app.seconds_to_next_check.return_value = 1
            try:
                await asyncio.wait_for(
                    zero_heartbeat_app.heartbeat_monitor(
                        HeartbeatTimers.RECEIVE, zero_heartbeat_app.send_test_request
                    ),
                    0.1,
                )
            except asyncio.exceptions.TimeoutError:
                pass

            assert check.call_count == 0

    @pytest.mark.asyncio
    async def test_monitor_heartbeat_heartbeat_exceeded(self, zero_heartbeat_app):
        """Simulate normal heartbeat_interval rhythm - heartbeat_interval exceeded since last message was received"""
        future_mock = asyncio.Future()
        future_mock.set_result(None)
        with mock.patch.object(
            HeartbeatApp, "send_test_request", return_value=future_mock
        ) as check:

            try:
                await asyncio.wait_for(
                    zero_heartbeat_app.heartbeat_monitor(
                        HeartbeatTimers.RECEIVE, zero_heartbeat_app.send_test_request
                    ),
                    0.1,
                )
            except asyncio.exceptions.TimeoutError:
                pass

            assert check.call_count > 1

    @pytest.mark.asyncio
    async def test_send_test_request(self, zero_heartbeat_app):
        async def simulate_heartbeat_response(message):
            await zero_heartbeat_app.on_heartbeat(
                HeartbeatMessage(str(message.TestReqID))
            )

        zero_heartbeat_app.pipeline.send.side_effect = simulate_heartbeat_response

        try:
            await asyncio.wait_for(
                zero_heartbeat_app.heartbeat_monitor(
                    HeartbeatTimers.RECEIVE, zero_heartbeat_app.send_test_request
                ),
                0.1,
            )
        except asyncio.exceptions.TimeoutError:
            pass

        assert not zero_heartbeat_app._server_not_responding.is_set()

    @pytest.mark.asyncio
    async def test_send_test_request_no_response(self, zero_heartbeat_app):
        await zero_heartbeat_app.send_test_request()
        assert zero_heartbeat_app._server_not_responding.is_set()

    @pytest.mark.asyncio
    async def test_logon_sets_heartbeat_increment(self, logon_message, base_pipeline):
        heartbeat_app = HeartbeatApp(base_pipeline)

        logon_message.HeartBtInt = 45
        await heartbeat_app.on_logon(logon_message)

        assert heartbeat_app.heartbeat_interval == 45

    @pytest.mark.asyncio
    async def test_sends_heartbeat_on_test_request(self, zero_heartbeat_app):
        request_message = TestRequestMessage("test123")
        await zero_heartbeat_app.on_test_request(request_message)

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        zero_heartbeat_app.pipeline.send.assert_called_with(
            admin.HeartbeatMessage("test123")
        )

    @pytest.mark.asyncio
    async def test_resets_request_id_when_heartbeat_received(self, zero_heartbeat_app):
        heartbeat_message = HeartbeatMessage("test123")
        zero_heartbeat_app._test_request_id = "test123"

        await zero_heartbeat_app.on_heartbeat(heartbeat_message)

        assert zero_heartbeat_app._test_request_id is None

    @pytest.mark.asyncio
    async def test_on_heartbeat_handles_empty_request_id(self, zero_heartbeat_app):
        test_request = OptimizedGenericMessage(
            (connection.protocol.Tag.MsgType, connection.protocol.MsgType.TestRequest)
        )

        assert await zero_heartbeat_app.on_heartbeat(test_request) == test_request

    @pytest.mark.asyncio
    async def test_on_receive_updated_timestamp(self, zero_heartbeat_app):
        prev_timestamp = HeartbeatTimers.RECEIVE.timestamp

        await zero_heartbeat_app.on_receive(TestRequestMessage("test123"))
        assert HeartbeatTimers.RECEIVE.timestamp != prev_timestamp


class TestSeqNumManagerApp:
    @pytest.fixture
    async def pipeline_with_messages(self, base_pipeline, messages):
        message_store_app = MessageStoreApp(base_pipeline, store=MemoryStore)
        await message_store_app.initialize()

        base_pipeline.apps[MessageStoreApp.name] = message_store_app

        for message in messages[0:3]:  # 3 sent messages
            await message_store_app.set_sent(message)

        for message in messages:  # 5 received messages
            tmp = message.SenderCompID
            message.SenderCompID = message.TargetCompID
            message.TargetCompID = tmp
            await message_store_app.set_received(message)

        return base_pipeline

    @pytest.mark.asyncio
    async def test_start_resumes_sequence_numbers(self, pipeline_with_messages):

        pipeline_with_messages.apps[ClientSessionApp.name]._new_session = False
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        await seq_num_app.start()

        assert seq_num_app.send_seq_num == 3
        assert seq_num_app.receive_seq_num == 5

    @pytest.mark.asyncio
    async def test_start_resets_sequence_numbers_for_new_session(
        self, pipeline_with_messages
    ):

        pipeline_with_messages.apps[ClientSessionApp.name]._new_session = True
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        await seq_num_app.start()

        assert seq_num_app.send_seq_num == 0
        assert seq_num_app.receive_seq_num == 0

    def test_handle_sequence_number_too_low_raises_exception_if_number_too_low(
        self, user_notification_message
    ):
        with pytest.raises(SessionError):
            pipeline_mock = MagicMock(BasePipeline)
            seq_num_app = SeqNumManagerApp(pipeline_mock)
            seq_num_app.receive_seq_num = 10

            user_notification_message.MsgSeqNum = 1

            seq_num_app._handle_sequence_number_too_low(user_notification_message)

    def test_handle_sequence_number_too_low_skips_duplicates_with_low_sequence_numbers(
        self, user_notification_message
    ):
        with pytest.raises(StopMessageProcessing):
            pipeline_mock = MagicMock(BasePipeline)
            seq_num_app = SeqNumManagerApp(pipeline_mock)
            seq_num_app.receive_seq_num = 10

            user_notification_message.MsgSeqNum = 1
            user_notification_message.PossDupFlag = True

            seq_num_app._handle_sequence_number_too_low(user_notification_message)

    @pytest.mark.asyncio
    async def test_handle_seq_num_too_high_starts_buffer_and_sends_resend_request(
        self, pipeline_with_messages, user_notification_message
    ):
        with pytest.raises(StopMessageProcessing):
            seq_num_app = SeqNumManagerApp(pipeline_with_messages)
            seq_num_app.startup_time = datetime.utcnow() - timedelta(
                seconds=5
            )  # Don't wait

            user_notification_message.MsgSeqNum = 99
            await seq_num_app._handle_sequence_number_too_high(
                user_notification_message
            )

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert len(seq_num_app.receive_buffer) == 1
        assert seq_num_app.receive_buffer[0] == user_notification_message
        assert pipeline_with_messages.send.call_count == 1

    @pytest.mark.asyncio
    async def test_handle_seq_num_too_high_buffers_messages_received_out_of_order(
        self, pipeline_with_messages, user_notification_message
    ):
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        seq_num_app.startup_time = datetime.utcnow() - timedelta(
            seconds=5
        )  # Don't wait

        for idx in range(5):
            out_of_sequence_msg = user_notification_message.copy()
            out_of_sequence_msg.MsgSeqNum = 5 + idx
            try:
                await seq_num_app._handle_sequence_number_too_high(out_of_sequence_msg)
            except StopMessageProcessing:
                # Expected
                pass

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert len(seq_num_app.receive_buffer) == 5
        assert pipeline_with_messages.send.call_count == 1

    @pytest.mark.asyncio
    async def test_send_resend_request_waits_for_target_before_doing_gapfill(
        self, pipeline_with_messages
    ):

        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        seq_num_app.startup_time = datetime.utcnow() - timedelta(
            seconds=5
        )  # Don't wait
        assert not seq_num_app.waited_for_resend_request_event.is_set()

        await seq_num_app._send_resend_request([1, 2])

        assert seq_num_app.waited_for_resend_request_event.is_set()

    @pytest.mark.asyncio
    async def test_send_resend_request_sends_resend_request(
        self, pipeline_with_messages
    ):
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        seq_num_app.startup_time = datetime.utcnow() - timedelta(
            seconds=5
        )  # Don't wait

        await seq_num_app._send_resend_request([1, 2])

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert pipeline_with_messages.send.call_count == 1

    @pytest.mark.asyncio
    async def test_handle_resend_request_sends_resend_request(
        self, pipeline_with_messages
    ):
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        seq_num_app.send_seq_num = 3  # 3 messages sent so far
        resend_begin_seq_num = 2  # Simulate resend request of 2 and 3

        await seq_num_app._handle_resend_request(
            admin.ResendRequestMessage(resend_begin_seq_num)
        )

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert pipeline_with_messages.send.call_count == 2

        for idx in range(pipeline_with_messages.send.call_count):
            message = pipeline_with_messages.send.mock_calls[idx][1][0]
            # Check sequence number
            assert message.seq_num == resend_begin_seq_num + idx
            # Check PossDup flag
            assert bool(message.PossDupFlag) is True
            # Check sending time
            assert str(message.OrigSendingTime) == str(message.SendingTime)

    @pytest.mark.asyncio
    async def test_handle_resend_request_converts_admin_messages_to_sequence_reset_messages(
        self, logon_message, pipeline_with_messages, messages
    ):
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)

        admin_messages = [logon_message, HeartbeatMessage("test123")]

        # Inject admin messages
        messages = admin_messages + messages

        # Reset sequence numbers
        for idx, message in enumerate(messages):
            message.MsgSeqNum = idx + 1

        message_store_app = pipeline_with_messages.apps[MessageStoreApp.name]
        await message_store_app.initialize()
        message_store_app.store._store.clear()

        for message in messages:
            await message_store_app.set_sent(message)

        seq_num_app.send_seq_num = max(
            message.seq_num
            for message in pipeline_with_messages.apps[
                MessageStoreApp.name
            ].store._store.values()
        )

        resend_begin_seq_num = 1

        await seq_num_app._handle_resend_request(
            admin.ResendRequestMessage(resend_begin_seq_num)
        )

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert pipeline_with_messages.send.call_count == 6

        admin_messages_resend = pipeline_with_messages.send.mock_calls[0][1][0]
        # Check SequenceReset message is constructed correctly
        assert admin_messages_resend.seq_num == 1
        assert int(admin_messages_resend.NewSeqNo) == 3
        assert bool(admin_messages_resend.PossDupFlag) is True

        # Check first non-admin message starts with correct sequence number
        first_non_admin_message_resend = pipeline_with_messages.send.mock_calls[1][1][0]
        assert first_non_admin_message_resend.seq_num == 3

    @pytest.mark.asyncio
    async def test_on_receive_handles_gapfill(
        self, pipeline_with_messages, user_notification_message
    ):
        seq_num_app = SeqNumManagerApp(pipeline_with_messages)
        seq_num_app.startup_time = datetime.utcnow() - timedelta(
            seconds=10
        )  # Don't wait for resend requests

        seq_num_app.receive_seq_num = 5  # 5 Messages received so far
        user_notification_message.seq_num = 8  # Simulate missing messages 6 and 7

        try:
            await seq_num_app.on_receive(user_notification_message)
            assert pipeline_with_messages.send.call_count == 1  # Resend request sent
        except StopMessageProcessing:
            # Expected
            pass

        # Simulate resend of 6 and 7
        for seq_num in [6, 7]:
            message = user_notification_message.copy()
            message.seq_num = seq_num
            message.PossDupFlag = True
            await seq_num_app.on_receive(message)

        # Wait for separate 'send' tasks to complete
        tasks = asyncio.all_tasks()
        await asyncio.wait(tasks, timeout=0.1)

        assert (
            pipeline_with_messages.receive.call_count == 1
        )  # One queued message (with sequence number 8) processed
