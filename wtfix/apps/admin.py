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
from datetime import datetime

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


class HeartbeatApp(MessageTypeHandlerApp):
    """
    Manages heartbeats between the FIX server and client.
    """

    name = "heartbeat"

    def __init__(self, pipeline, *args, **kwargs):
        self._last_receive = datetime.utcnow()

        self._test_request_id = (
            None
        )  # A waiting TestRequest message for which no response has been received.

        self._heartbeat_monitor_unfuture = None
        self._server_not_responding = asyncio.Event(loop=unsync.loop)

        super().__init__(pipeline, *args, **kwargs)

    @property
    def heartbeat(self):
        try:
            return self._heartbeat
        except AttributeError:
            self._heartbeat = self.pipeline.settings.HEARTBEAT_INT

            return self._heartbeat

    @heartbeat.setter
    def heartbeat(self, value):
        logger.debug(f"{self.name}: Heartbeat changed to {value}.")
        self._heartbeat = value

    @property
    def test_request_response_delay(self):
        """
        The amount of time to wait for a TestRequest response from the server.
        """
        return 2 * self.heartbeat + 4

    def sec_since_last_receive(self):
        """
        :return: The number of seconds since the last message was received.
        """
        return (datetime.utcnow() - self._last_receive).total_seconds()

    def is_waiting(self):
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

        # Keep a reference to running monitor, so that we can cancel it if needed.
        self._heartbeat_monitor_unfuture = self.monitor_heartbeat()

        logger.info(
            f"{self.name}: Started heartbeat monitor with {self.heartbeat} second interval."
        )

    @unsync
    async def stop(self, *args, **kwargs):
        """
        Cancel the heartbeat monitor on the next iteration of the event loop.
        """
        await super().stop(*args, **kwargs)
        if self._heartbeat_monitor_unfuture is not None:
            # Heartbeat has been started - stop it now.
            self._heartbeat_monitor_unfuture.future.cancel()

    @unsync
    async def monitor_heartbeat(self):
        """
        Monitors the heartbeat, sending TestRequest messages as necessary.
        """
        while not self._server_not_responding.is_set():
            # Keep sending heartbeats until the server stops responding.
            next_check = max(self.heartbeat - self.sec_since_last_receive(), 0)
            await asyncio.sleep(
                next_check
            )  # Wait until the next scheduled heartbeat check.

            if self.sec_since_last_receive() > self.heartbeat:
                # Heartbeat exceeded, send test message
                await self.send_test_request()

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
        self.send(admin.TestRequestMessage(utils.encode(self._test_request_id)))

        # Sleep while we wait for a response on the test request
        await asyncio.sleep(self.test_request_response_delay)

        if self.is_waiting():
            self._server_not_responding.set()

    @unsync
    @on(MsgType.Logon)
    async def on_logon(self, message):
        """
        Start the heartbeat monitor as soon as a logon response is received from the server.

        :param message: The Logon message received. Should contain a HeartBtInt tag that will be used
        to set the heartbeat interval to monitor.
        """
        self._heartbeat = int(message.HeartBtInt)

        return message

    @unsync
    @on(MsgType.TestRequest)
    async def on_test_request(self, message):
        """
        Send a HeartBeat message in response to a TestRequest received from the server.

        :param message: The TestRequest message. Should contain a TestReqID.
        """
        logger.debug(
            f"{self.name}: Sending heartbeat in response to request {message.TestReqID}."
        )
        self.send(admin.HeartbeatMessage(str(message.TestReqID)))

        return message

    @unsync
    @on(MsgType.Heartbeat)
    async def on_heartbeat(self, message):
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
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        """
        Update the timestamp whenever any message is received.
        :param message:
        """
        self._last_receive = (
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
        logger.info(f"{self.name}: Logging in...")

        await self.logon()
        await self.logged_in_event.wait()

        logger.info(f"Successfully logged on!")

    @unsync
    async def stop(self, *args, **kwargs):
        await super().stop(*args, **kwargs)
        logger.info(f"{self.name}: Logging out...")

        await self.logout()
        await self.logged_out_event.wait()

        logger.info(f"Logout completed!")

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
    async def logon(self):
        """
        Log on to the FIX server using the provided credentials.
        """
        logon_msg = admin.LogonMessage(
            self.username, self.password, heartbeat_int=self.heartbeat_int
        )

        self.reset_seq_nums = not self.pipeline.apps[ClientSessionApp.name].is_resumed
        if self.reset_seq_nums:
            logon_msg.ResetSeqNumFlag = "Y"

        if self.test_mode is True:
            logon_msg.TestMessageIndicator = "Y"

        logger.info(f"{self.name}: Logging in with: {logon_msg:t}...")
        self.send(logon_msg)

    @unsync
    async def logout(self):
        """
        Log out of the FIX server.
        """
        logout_msg = admin.LogoutMessage()
        self.send(logout_msg)


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

    def __init__(self, pipeline, *args, **kwargs):
        self._send_seq_num = 0
        self._receive_seq_num = 0

        self.gapfill_deque = collections.deque()

        super().__init__(pipeline, *args, **kwargs)

    @property
    def send_seq_num(self):
        return self._send_seq_num

    @property
    def receive_seq_num(self):
        return self._receive_seq_num

    @property
    def expected_seq_num(self):
        return self._receive_seq_num + 1

    def _check_seq_num_gap(self, message):
        if message.seq_num > self.expected_seq_num:
            # We've missed some incoming messages

            if len(self.gapfill_deque) == 0:
                # Start a new gap fill operation
                missing_seq_nums = [seq_num for seq_num in range(self.receive_seq_num + 1, message.seq_num)]

                logger.error(
                    f"{self.name}: Client missed {len(missing_seq_nums)} messages. Sequence numbers: "
                    f"{missing_seq_nums}."
                )

                self.gapfill_deque.append(message)
                self._handle_seq_num_gaps(missing_seq_nums)
            else:
                # Busy processing gap fill, add to queue
                self.gapfill_deque.append(message)
                raise StopMessageProcessing(
                    f"Queueing message # {message.seq_num} while gap fill is in progress "
                    f"(waiting for # {self.expected_seq_num})..."
                )
        else:
            # Message received in expected order
            try:
                if self.gapfill_deque[0].seq_num == message.seq_num + 1:
                    # Also process and clear gapfill queue
                    logger.info(f"{self.name}: Gap fill completed, processing queued messages...")

                    for message in self.gapfill_deque:
                        logger.info(f"{self.name}: Resubmitting queued message # {message.seq_num}.")
                        self.pipeline.receive(bytes(message))

                    self.gapfill_deque.clear()
            except IndexError:
                # Gap fill not in progress - continue
                pass

    def _handle_seq_num_gaps(self, missing_seq_numbers):
        self.send(admin.ResendRequestMessage(missing_seq_numbers[0], missing_seq_numbers[-1]))

        raise StopMessageProcessing(
            f"Detected message sequence gap: {missing_seq_numbers}. Queueing message for gap fill."
        )

    def _check_poss_dup(self, message):
        if message.seq_num < self.expected_seq_num:
            error_msg = f"Unexpected message sequence number '{message.seq_num}'. Expected '{self.expected_seq_num}'."

            try:
                if bool(message.PossDupFlag) is True:
                    raise StopMessageProcessing(
                        f"Ignoring duplicate message {message}."
                    )
            # According to the FIX specification, receiving a lower than expected sequence number, that is
            # not a duplicate, is a fatal error that requires manual intervention. Throw an unhandled exception to
            # force-stop the pipeline.
            except TagNotFound:
                raise SessionError(error_msg)

            raise SessionError(error_msg)

    @unsync
    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)

        client_session = self.pipeline.apps[ClientSessionApp.name]
        if client_session.is_resumed:
            message_store = self.pipeline.apps[MessageStoreApp.name].store

            sent_seq_nums = await message_store.filter(
                session_id=client_session.session_id, originator=client_session.sender
            )

            received_seq_nums = await message_store.filter(
                session_id=client_session.session_id, originator=client_session.target
            )

            try:
                self._send_seq_num = sent_seq_nums[-1]
            except IndexError:
                # No messages sent yet
                self._send_seq_num = 0

            try:
                self._receive_seq_num = received_seq_nums[-1]
            except IndexError:
                # No messages received yet
                self._receive_seq_num = 0

        else:
            self._send_seq_num = 0
            self._receive_seq_num = 0

    @unsync
    @on(MsgType.ResendRequest)
    async def on_resend_request(self, message):
        begin_seq_no = int(message.BeginSeqNo)
        end_seq_no = int(message.EndSeqNo)

        if end_seq_no == 0:
            # Server requested all messages
            end_seq_no = self.send_seq_num

        logger.info(f"Resending messages {begin_seq_no} through {end_seq_no}.")

        admin_seq_nums = []
        next_seq_num = begin_seq_no

        message_store = self.pipeline.apps[MessageStoreApp.name]
        for seq_num in range(begin_seq_no, end_seq_no + 1):
            resend_msg = await message_store.get_sent(seq_num)

            if resend_msg.MsgType in self.ADMIN_MESSAGES:
                # Admin message - see if there are more sequential ones in the send log
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

        if len(admin_seq_nums) > 0:
            # Admin messages were found, submit SequenceReset
            self.send(
                admin.SequenceResetMessage(next_seq_num, admin_seq_nums[-1] + 1)
            )
            next_seq_num = admin_seq_nums[-1] + 1
            admin_seq_nums.clear()

        return message

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        """
        Check the sequence number for every message received
        """
        self._check_poss_dup(message)
        self._check_seq_num_gap(message)
        self._receive_seq_num = message.seq_num

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
            # Set sequence number and add to send log
            self._send_seq_num += 1
            message.seq_num = self.send_seq_num

        return await super().on_send(message)
