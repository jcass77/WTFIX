# This file is a part of WTFIX.
#
# Copyright (C) 2018,2019 John Cass <john.cass77@gmail.com>
#
# WTFIX is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# WTFIX is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import collections
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable

from unsync import unsync

from wtfix.apps.base import MessageTypeHandlerApp, on
from wtfix.apps.sessions import ClientSessionApp
from wtfix.apps.store import MessageStoreApp
from wtfix.conf import settings
from wtfix.core.exceptions import TagNotFound, StopMessageProcessing, SessionError
from wtfix.message import admin
from wtfix.core import utils
from wtfix.message.message import FIXMessage
from wtfix.protocol.common import MsgType


logger = settings.logger


class HeartbeatTimers(Enum):
    """Send / receive timers used by the heartbeat monitor"""

    SEND = None
    RECEIVE = None

    def __init__(self, timestamp: int):
        self.timestamp = timestamp


class HeartbeatApp(MessageTypeHandlerApp):
    """
    Manages heartbeats between the FIX server and client.
    """

    name = "heartbeat"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self._test_request_id = (
            None
        )  # A waiting TestRequest message for which no response has been received.

        self._received_monitor = None
        self._sent_monitor = None
        self._server_not_responding = asyncio.Event(loop=unsync.loop)

    @property
    def heartbeat_interval(self):
        try:
            return self._heartbeat_interval
        except AttributeError:
            self._heartbeat_interval = self.pipeline.settings.HEARTBEAT_INT

            return self._heartbeat_interval

    @heartbeat_interval.setter
    def heartbeat_interval(self, value: int):
        logger.debug(f"{self.name}: Heartbeat interval changed to {value}.")
        self._heartbeat_interval = value

    @property
    def test_request_response_delay(self) -> int:
        """
        The amount of time to wait for a TestRequest response from the server.
        """
        return 2 * self.heartbeat_interval + 4

    def seconds_to_next_check(self, timer: HeartbeatTimers) -> int:
        """
        :timer: The timer being checked (sent / received)
        :return: The number of seconds before the next check is due to occur.
        """
        if timer.timestamp is None:
            timer.timestamp = datetime.utcnow()

        elapsed = (datetime.utcnow() - timer.timestamp).total_seconds()
        return max(self.heartbeat_interval - elapsed, 0)

    def is_waiting(self) -> bool:
        """
        :return: True if this heartbeat monitor is waiting for a response from the server for a TestRequest
        message that was sent. False otherwise.
        """
        return self._test_request_id is not None

    @unsync
    async def start(self, *args, **kwargs):
        """
        Start the heartbeat monitor.
        """
        await super().start(*args, **kwargs)

        # Keep a reference to running monitors, so that we can cancel them if needed.
        self._received_monitor = self.heartbeat_monitor(
            HeartbeatTimers.RECEIVE, self.send_test_request
        )
        self._sent_monitor = self.heartbeat_monitor(
            HeartbeatTimers.SEND, self.send_heartbeat
        )

        logger.info(
            f"{self.name}: Started heartbeat monitor with {self.heartbeat_interval} second interval."
        )

    @unsync
    async def stop(self, *args, **kwargs):
        """
        Cancel the heartbeat monitor on the next iteration of the event loop.
        """
        await super().stop(*args, **kwargs)
        # Stop heartbeat monitors
        if self._received_monitor is not None:
            self._received_monitor.future.cancel()

        if self._sent_monitor is not None:
            self._sent_monitor.future.cancel()

    @unsync
    async def heartbeat_monitor(
        self, timer: HeartbeatTimers, interval_exceeded_response: Callable
    ):
        """
        Monitors the heartbeat, sending appropriate response as necessary.

        :timer: The timer to use as reference against the heartbeat interval
        :interval_exceeded_response: The response to take if the interval is exceeded. Must be an awaitable.
        """
        while not self._server_not_responding.is_set():
            # Keep sending heartbeats until the server stops responding.
            await asyncio.sleep(
                self.seconds_to_next_check(timer)
            )  # Wait until the next scheduled heartbeat check.

            if self.seconds_to_next_check(timer) == 0:
                # Heartbeat exceeded, send response
                await interval_exceeded_response()

        # No response received, force logout!
        logger.error(
            f"{self.name}: No response received for test request '{self._test_request_id}', "
            f"initiating shutdown..."
        )
        self.pipeline.stop()

    @unsync
    async def send_test_request(self):
        """
        Checks if the server is responding to TestRequest messages.
        """

        self._test_request_id = uuid.uuid4().hex
        logger.warning(
            f"{self.name}: Heartbeat exceeded, sending test request '{self._test_request_id}'..."
        )
        # Don't need to block while request is sent
        self.send(admin.TestRequestMessage(utils.encode(self._test_request_id)))

        # Sleep while we wait for a response on the test request
        await asyncio.sleep(self.test_request_response_delay)

        if self.is_waiting():
            self._server_not_responding.set()

    @unsync
    async def send_heartbeat(self):
        """
        Send our own heartbeat to indicate that the pipeline is still responding.
        """
        logger.debug(f"{self.name}: Pipeline idle, sending heartbeat...")

        # Update timer immediately to avoid flooding the target with heartbeats.
        HeartbeatTimers.SEND.timestamp = datetime.utcnow()

        self.send(
            admin.HeartbeatMessage()
        )  # Don't need to block while heartbeat is sent

    @unsync
    @on(MsgType.Logon)
    async def on_logon(self, message: FIXMessage) -> FIXMessage:
        """
        Start the heartbeat monitor as soon as a logon response is received from the server.

        :param message: The Logon message received. Should contain a HeartBtInt tag that will be used
        to set the heartbeat interval to monitor.
        """
        self.heartbeat_interval = int(message.HeartBtInt)

        return message

    @unsync
    @on(MsgType.TestRequest)
    async def on_test_request(self, message: FIXMessage) -> FIXMessage:
        """
        Send a HeartBeat message in response to a TestRequest received from the server.

        :param message: The TestRequest message. Should contain a TestReqID.
        """
        logger.debug(
            f"{self.name}: Sending heartbeat in response to request {message.TestReqID}."
        )
        # Don't need to block while heartbeat is sent
        self.send(admin.HeartbeatMessage(str(message.TestReqID)))

        return message

    @unsync
    @on(MsgType.Heartbeat)
    async def on_heartbeat(self, message: FIXMessage) -> FIXMessage:
        """
        Handle a TestRequest response from the server.
        :param message: The Heartbeat message that was received in response to our TestRequest. The
        TestReqID for the TestRequest and Heartbeat messages should match for this to be a valid response.
        """
        try:
            if message.TestReqID == self._test_request_id:
                # Response received - reset
                self._test_request_id = None
        except TagNotFound:
            # Random heartbeat message received - nothing more to do
            pass

        return message

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        """
        Update the send timer whenever any message is sent.
        """
        HeartbeatTimers.SEND.timestamp = (
            datetime.utcnow()
        )  # Update timestamp on every message sent

        return await super().on_send(message)

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        """
        Update the receive timer whenever any message is received.
        """
        HeartbeatTimers.RECEIVE.timestamp = (
            datetime.utcnow()
        )  # Update timestamp on every message received

        return await super().on_receive(message)


class AuthenticationApp(MessageTypeHandlerApp):
    """
    Handles logging on to and out of the FIX server.
    """

    name = "authentication"

    def __init__(
        self,
        pipeline,
        heartbeat_int=None,
        username=None,
        password=None,
        reset_seq_nums=True,
        test_mode=False,
        *args,
        **kwargs,
    ):
        super().__init__(pipeline, *args, **kwargs)

        if heartbeat_int is None:
            heartbeat_int = settings.default_connection.HEARTBEAT_INT

        self.heartbeat_int = heartbeat_int

        if username is None:
            username = self.pipeline.settings.USERNAME

        if password is None:
            password = self.pipeline.settings.PASSWORD

        self.username = username
        self.password = password

        self.reset_seq_nums = reset_seq_nums
        self.test_mode = test_mode

        self.logged_in_event = asyncio.Event(loop=unsync.loop)
        self.logged_out_event = asyncio.Event(loop=unsync.loop)

    @unsync
    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)

        await self.logon()

    @unsync
    async def stop(self, *args, **kwargs):
        await super().stop(*args, **kwargs)

        await self.logout()

    @unsync
    @on(MsgType.Logon)
    async def on_logon(self, message):
        """
        Confirms all of the session parameters that we sent when logging on.

        :param message: The logon FIX message received from the server.
        :raises: MessageProcessingError if any of the session parameters do not match what was sent to the server.
        """
        heartbeat_time = int(message.HeartBtInt)
        if heartbeat_time != self.heartbeat_int:
            raise SessionError(
                f"{self.name}: Heartbeat confirmation '{heartbeat_time}' does not match logon "
                f"value {self.heartbeat_int}."
            )

        try:
            test_mode = bool(message.TestMessageIndicator)
        except TagNotFound:
            test_mode = False

        if test_mode != self.test_mode:
            raise SessionError(
                f"{self.name}: Test mode confirmation '{test_mode}' does not match logon value {self.test_mode}."
            )

        try:
            reset_seq_nums = bool(message.ResetSeqNumFlag)
        except TagNotFound:
            reset_seq_nums = False

        if reset_seq_nums != self.reset_seq_nums:
            raise SessionError(
                f"{self.name}: Reset sequence number confirmation '{reset_seq_nums}' does not match "
                f"logon value {self.reset_seq_nums}."
            )

        self.logged_in_event.set()  # Login completed.

        return message

    @unsync
    @on(MsgType.Logout)
    async def on_logout(self, message):
        self.logged_out_event.set()  # FIX server has logged us out.

        await self.pipeline.stop()  # Stop the pipeline, in case this is not already underway.

        return message

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:

        # Block non-authentication messages until we've logged in successfully
        if (
            not self.logged_in_event.is_set()
            and message.type not in SeqNumManagerApp.ADMIN_MESSAGES
        ):
            logger.warning(
                f"{self.name}: Blocking message until logon is completed ({message})."
            )
            await self.logged_in_event.wait()

        return await super().on_receive(message)

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:

        # Block non-authentication messages until we've logged in successfully
        if (
            not self.logged_in_event.is_set()
            and message.type not in SeqNumManagerApp.ADMIN_MESSAGES
        ):
            logger.warning(
                f"{self.name}: Blocking message until logon is completed ({message})."
            )
            await self.logged_in_event.wait()

        return message

    @unsync
    async def logon(self):
        """
        Log on to the FIX server using the provided credentials.
        """
        logger.info(f"{self.name}: Logging in...")

        logon_msg = admin.LogonMessage(
            self.username, self.password, heartbeat_int=self.heartbeat_int
        )

        self.reset_seq_nums = not self.pipeline.apps[ClientSessionApp.name].is_resumed
        if self.reset_seq_nums:
            logon_msg.ResetSeqNumFlag = True

        if self.test_mode is True:
            logon_msg.TestMessageIndicator = True

        logger.info(f"{self.name}: Logging in with: {logon_msg:t}...")
        # Don't need to block while we send logon message
        self.send(logon_msg)

        await self.logged_in_event.wait()

        logger.info(f"Successfully logged on!")

    @unsync
    async def logout(self):
        """
        Log out of the FIX server.
        """
        if self.logged_in_event.is_set():

            logger.info(f"{self.name}: Logging out...")
            logout_msg = admin.LogoutMessage()
            # Fire and forget logout
            self.send(logout_msg)

            await self.logged_out_event.wait()

            logger.info(f"Logout completed!")
        else:
            self.logged_out_event.set()


class SeqNumManagerApp(MessageTypeHandlerApp):
    """
    Monitors message sequence numbers to detect dropped messages
    """

    name = "seq_num_manager"

    ADMIN_MESSAGES = [
        MsgType.Logon,
        MsgType.Logout,
        MsgType.ResendRequest,
        MsgType.Heartbeat,
        MsgType.TestRequest,
        MsgType.SequenceReset,
    ]

    # How long to wait (in seconds) for resend requests from target before sending our own resend requests.
    RESEND_WAIT_TIME = 5

    def __init__(self, pipeline, *args, **kwargs):

        self.startup_time = (
            None
        )  # Needed to check if we should wait for resend requests from target
        self._send_seq_num = 0
        self._receive_seq_num = 0

        self.receive_buffer = collections.deque()

        self.resend_request_handled_event = asyncio.Event(loop=unsync.loop)
        self.resend_request_handled_event.set()  # Detect if a resend request has been responded to

        self.waited_for_resend_request_event = asyncio.Event(
            loop=unsync.loop
        )  # Wait for resend requests from target

        super().__init__(pipeline, *args, **kwargs)

    @property
    def send_seq_num(self):
        return self._send_seq_num

    @send_seq_num.setter
    def send_seq_num(self, value: int):
        self._send_seq_num = int(value)  # Make sure we received an int

    @property
    def receive_seq_num(self):
        return self._receive_seq_num

    @receive_seq_num.setter
    def receive_seq_num(self, value: int):
        self._receive_seq_num = int(value)  # Make sure we received an int

    @property
    def expected_seq_num(self):
        return self.receive_seq_num + 1

    @unsync
    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)

        client_session = self.pipeline.apps[ClientSessionApp.name]
        if client_session.is_resumed:
            message_store = self.pipeline.apps[MessageStoreApp.name].store

            sent_seq_nums = await message_store.filter(
                session_id=client_session.session_id, originator=client_session.sender
            )  # Get sequence number of last message sent

            received_seq_nums = await message_store.filter(
                session_id=client_session.session_id, originator=client_session.target
            )  # Get sequence number of last message received.

            try:
                self.send_seq_num = sent_seq_nums[-1]
            except IndexError:
                # No messages sent yet
                self.send_seq_num = 0

            try:
                self.receive_seq_num = received_seq_nums[-1]
            except IndexError:
                # No messages received yet
                self.receive_seq_num = 0

        else:
            self.send_seq_num = 0
            self.receive_seq_num = 0

        self.startup_time = datetime.utcnow()

    @unsync
    async def _check_sequence_number(self, message):

        if int(message.seq_num) < self.expected_seq_num:
            self._handle_sequence_number_too_low(message)

        elif int(message.seq_num) > self.expected_seq_num:
            message = await self._handle_sequence_number_too_high(message)

        else:
            # Message received in correct order.
            if message.type == MsgType.SequenceReset:
                # Special handling for SequenceReset admin message
                message = self._handle_sequence_reset(message)
            else:
                # Update counter as early as possible
                self.receive_seq_num = message.seq_num

            if len(self.receive_buffer) > 0:
                # See if the gap has been filled and we can replay buffered messages.
                self._replay_buffered_messages()

        return message

    def _replay_buffered_messages(self):
        try:
            if self.receive_buffer[0].seq_num == self.expected_seq_num:
                # We've just received the missing sequence numbers. Process and clear any messages that
                # were buffered since gap fill started.
                logger.info(
                    f"{self.name}: Gap fill completed, processing {len(self.receive_buffer)} queued "
                    f"messages (#{self.receive_buffer[0].seq_num} - #{self.receive_buffer[-1].seq_num})."
                )

                while len(self.receive_buffer) > 0:
                    resubmit_message = self.receive_buffer.popleft()
                    if resubmit_message.type in SeqNumManagerApp.ADMIN_MESSAGES:
                        # Don't re-submit admin messages
                        logger.info(
                            f"{self.name}: Skipping queued admin message #{resubmit_message.seq_num} "
                            f"({resubmit_message})."
                        )
                        self.receive_seq_num += 1
                        continue

                    logger.info(
                        f"{self.name}: Resubmitting queued message #{resubmit_message.seq_num} "
                        f"({resubmit_message})."
                    )
                    self.pipeline.receive(
                        bytes(resubmit_message)
                    )  # Separate, non-blocking task

        except IndexError:
            # Buffer is empty - continue
            pass

    def _handle_sequence_number_too_low(self, message):
        """
        According to the FIX specification, receiving a lower than expected sequence number, that is
        not a duplicate, is a fatal error that requires manual intervention. Throw an exception to
        force-stop the pipeline.

        :param message: The FIX message to check
        :raises: SessionError if a non-duplicate message is received with a lower than expected sequence number.
        """
        error_msg = f"Unexpected message sequence number '{message.seq_num}'. Expected '{self.expected_seq_num}'."
        try:
            if bool(message.PossDupFlag) is True:
                # Duplicate that must already have been processed - ignore
                raise StopMessageProcessing(
                    f"{self.name}: Ignoring duplicate with lower than "
                    f"expected sequence number ({message})."
                )

        except TagNotFound:
            raise SessionError(error_msg)

        raise SessionError(error_msg)

    @unsync
    async def _handle_sequence_number_too_high(self, message):

        # We've missed some incoming messages
        if len(self.receive_buffer) == 0:

            # Start a new gap fill operation
            logger.warning(
                f"{self.name}: Sequence number gap detected! Expected: "
                f"{self.expected_seq_num}, received: {message.seq_num})"
            )
            missing_seq_nums = [
                seq_num for seq_num in range(self.expected_seq_num, message.seq_num)
            ]

            logger.warning(
                f"{self.name}: Client missed {len(missing_seq_nums)} message(s). Sequence number(s): "
                f"{missing_seq_nums}."
            )

            # Start buffering out-of-sequence messages
            self.receive_buffer.append(message)

            self._send_resend_request(
                missing_seq_nums
            )  # Separate task - don't block while waiting for send!

        else:
            # Already busy processing gap fill, add to queue
            self.receive_buffer.append(message)

        # Delete messages that were received out of order from the message store
        session_id = self.pipeline.apps[ClientSessionApp.name].session_id
        await self.pipeline.apps[MessageStoreApp.name].store.delete(
            session_id, message.SenderCompID, message.seq_num
        )

        if message.type in SeqNumManagerApp.ADMIN_MESSAGES:
            # Always propagate admin messages to the rest of the pipeline apps, even if received out of order
            f"Propagating admin message #{message.seq_num} while gap fill is in progress "
            f"(waiting for #{self.expected_seq_num})..."
            return message

        # ALL OTHER MESSAGE TYPES: don't propagate any further!
        raise StopMessageProcessing(
            f"Queueing message #{message.seq_num} while gap fill is in progress "
            f"(waiting for #{self.expected_seq_num})..."
        )

    @unsync
    async def _send_resend_request(self, missing_seq_nums):
        # Wait for opportunity to send resend request. Must:
        #
        #   1.) Have waited for resend requests from the target; and
        #   2.) Not be busy handling a resend request from the target

        if not self.waited_for_resend_request_event.is_set():
            wait_time = self.startup_time + timedelta(
                seconds=SeqNumManagerApp.RESEND_WAIT_TIME
            )
            wait_time = wait_time.timestamp() - datetime.utcnow().timestamp()
            logger.info(
                f"{self.name}: Waiting {wait_time:0.2f}ms for ResendRequests from target "
                f"before doing gap fill..."
            )

            await asyncio.sleep(wait_time)
            self.waited_for_resend_request_event.set()

        # Don't send our own resend requests if we are busy handling one received from the target
        await self.resend_request_handled_event.wait()

        self.send(admin.ResendRequestMessage(missing_seq_nums[0], missing_seq_nums[-1]))

    @unsync
    async def _handle_resend_request(self, message):

        # Set event marker to block our own gap fill requests until we've responded to this request.
        self.resend_request_handled_event.clear()

        begin_seq_no = int(message.BeginSeqNo)
        end_seq_no = int(message.EndSeqNo)

        if end_seq_no == 0:
            # Server requested all messages
            end_seq_no = self.send_seq_num

        logger.info(f"Resending messages #{begin_seq_no} - #{end_seq_no}.")

        admin_seq_nums = (
            []
        )  # Admin messages are handled differently, need a place to buffer them
        next_seq_num = begin_seq_no

        message_store = self.pipeline.apps[MessageStoreApp.name]
        for seq_num in range(begin_seq_no, end_seq_no + 1):
            resend_msg = await message_store.get_sent(
                seq_num
            )  # Retrieve the message from the MessageStore

            if resend_msg.MsgType in SeqNumManagerApp.ADMIN_MESSAGES:
                # Admin message - continue: to see if there are more sequential ones after this one
                admin_seq_nums.append(resend_msg.seq_num)
                continue

            if len(admin_seq_nums) > 0:
                # Admin messages were found, submit SequenceReset
                self.send(
                    admin.SequenceResetMessage(next_seq_num, admin_seq_nums[-1] + 1)
                )
                next_seq_num = admin_seq_nums[-1] + 1
                admin_seq_nums.clear()

            # Resend message
            resend_msg = (
                resend_msg.copy()
            )  # Make a copy so that we do not change entries in the send log.
            resend_msg.MsgSeqNum = next_seq_num
            resend_msg.PossDupFlag = "Y"
            resend_msg.OrigSendingTime = resend_msg.SendingTime

            self.send(resend_msg)
            next_seq_num += 1

        else:
            # Handle situation where last message was itself an admin message
            if len(admin_seq_nums) > 0:
                # Admin messages were found, submit SequenceReset
                self.send(
                    admin.SequenceResetMessage(next_seq_num, admin_seq_nums[-1] + 1)
                )
                admin_seq_nums.clear()

        self.resend_request_handled_event.set()

        return message

    def _handle_sequence_reset(self, message: FIXMessage) -> FIXMessage:
        # Discard buffered messages with lower sequence numbers than SequenceReset
        try:
            while self.receive_buffer[0].seq_num < int(message.NewSeqNo):
                self.receive_buffer.popleft()
        except IndexError:
            # Buffer empty, continue
            pass

        # Reset sequence number: increment receive_seq_num so that the correct sequence number is expected next.
        self.receive_seq_num = int(message.NewSeqNo) - 1

        return message

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        """
        Check the sequence number for every message received
        """
        # Special handling for ResendRequest admin message: should be responded to even if received out of order
        if message.type == MsgType.ResendRequest:
            message = await self._handle_resend_request(
                message
            )  # Handle resend request immediately.

        message = await self._check_sequence_number(message)

        return await super().on_receive(message)

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        """
        Inject MsgSeqNum for every message to be sent, except duplicates.
        """
        try:
            is_duplicate = bool(message.PossDupFlag)
        except TagNotFound:
            is_duplicate = False

        if not is_duplicate:
            # Set sequence number
            self.send_seq_num += 1
            message.seq_num = self.send_seq_num

        return await super().on_send(message)
