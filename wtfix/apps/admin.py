import asyncio
import uuid
from datetime import datetime

from unsync import unsync

from wtfix.apps.base import MessageTypeHandlerApp, on
from wtfix.conf import logger, settings
from wtfix.core.exceptions import MessageProcessingError, TagNotFound
from wtfix.message import admin
from wtfix.core import utils
from wtfix.message.message import generic_message_factory
from wtfix.protocol.common import MsgType, Tag


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
        self._server_not_responding = asyncio.Event()

        super().__init__(pipeline, *args, **kwargs)

    @property
    def heartbeat(self):
        try:
            return self._heartbeat
        except AttributeError:
            self._heartbeat = 30

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
        self.send(admin.TestRequest(utils.encode(self._test_request_id)))

        # Sleep while we wait for a response on the test request
        await asyncio.sleep(self.test_request_response_delay)

        if self.is_waiting():
            self._server_not_responding.set()

    @on(MsgType.Logon)
    def on_logon(self, message):
        """
        Start the heartbeat monitor as soon as a logon response is received from the server.

        :param message: The Logon message received. Should contain a HeartBtInt tag that will be used
        to set the heartbeat interval to monitor.
        """
        self._heartbeat = message[Tag.HeartBtInt].as_int

        return message

    @on(MsgType.TestRequest)
    def on_test_request(self, message):
        """
        Send a HeartBeat message in response to a TestRequest received from the server.

        :param message: The TestRequest message. Should contain a TestReqID.
        """
        logger.debug(
            f"{self.name}: Sending heartbeat in response to request {message[Tag.TestReqID]}."
        )
        self.send(admin.Heartbeat(message[Tag.TestReqID].as_str))

        return message

    @on(MsgType.Heartbeat)
    def on_heartbeat(self, message):
        """
        Handle a TestRequest response from the server.
        :param message: The Heartbeat message that was received in response to our TestRequest. The
        TestReqID for the TestRequest and Heartbeat messages should match for this to be a valid response.
        """
        if message[Tag.TestReqID] == self._test_request_id:
            # Response received - reset
            self._test_request_id = None
        else:
            raise MessageProcessingError(
                f"Received an unexpected heartbeat message: {message}."
            )

        return message

    def on_receive(self, message):
        """
        Update the timestamp whenever any message is received.
        :param message:
        """
        self._last_receive = (
            datetime.utcnow()
        )  # Update timestamp on every message received

        return super().on_receive(message)


class AuthenticationApp(MessageTypeHandlerApp):
    """
    Handles logging on to and out of the FIX server.
    """

    name = "authentication"

    def __init__(
        self,
        pipeline,
        heartbeat_time=None,
        username=None,
        password=None,
        reset_seq_nums=True,
        test_mode=False,
        *args,
        **kwargs,
    ):
        super().__init__(pipeline, *args, **kwargs)

        if heartbeat_time is None:
            heartbeat_time = settings.HEARTBEAT_TIME

        self.heartbeat_time = heartbeat_time

        if username is None:
            username = settings.USERNAME

        if password is None:
            password = settings.PASSWORD

        self.username = username
        self.password = password

        self.reset_seq_nums = reset_seq_nums
        self.test_mode = test_mode

        self.logged_in_event = asyncio.Event()
        self.logged_out_event = asyncio.Event()

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

    @on(MsgType.Logon)
    def on_logon(self, message):
        """
        Confirms all of the session parameters that we sent when logging on.

        :param message: The logon FIX message received from the server.
        :raises: MessageProcessingError if any of the session parameters do not match what was sent to the server.
        """
        heartbeat_time = message.HeartBtInt.as_int
        if heartbeat_time != self.heartbeat_time:
            raise MessageProcessingError(
                f"{self.name}: Heartbeat confirmation '{heartbeat_time}' does not match logon value {self.heartbeat_time}."
            )

        try:
            test_mode = message.TestMessageIndicator.as_bool
        except TagNotFound:
            test_mode = False

        if test_mode != self.test_mode:
            raise MessageProcessingError(
                f"{self.name}: Test mode confirmation '{test_mode}' does not match logon value {self.test_mode}."
            )

        reset_seq_nums = message.ResetSeqNumFlag.as_bool
        if reset_seq_nums != self.reset_seq_nums:
            raise MessageProcessingError(
                f"{self.name}: Reset sequence number confirmation '{reset_seq_nums}' does not match logon value {self.reset_seq_nums}."
            )

        self.logged_in_event.set()  # Login completed.

        return message

    @on(MsgType.Logout)
    def on_logout(self, message):
        self.logged_out_event.set()  # FIX server has logged us out.

        self.pipeline.stop()  # Stop the pipeline, in case this is not already underway.

        return message

    @unsync
    async def logon(self):
        """
        Log on to the FIX server using the provided credentials.
        """
        logon_msg = generic_message_factory(
            (Tag.MsgType, MsgType.Logon),
            (Tag.EncryptMethod, "0"),  # TODO: should this be a configurable value?
            (Tag.HeartBtInt, self.heartbeat_time),
            (Tag.Username, self.username),
            (Tag.Password, self.password),
        )

        if self.reset_seq_nums:
            logon_msg[Tag.ResetSeqNumFlag] = "Y"

        if self.test_mode is True:
            logon_msg[Tag.TestMessageIndicator] = "Y"

        logger.info(f"{self.name}: Logging in with: {logon_msg}...")
        self.send(logon_msg)

    @unsync
    async def logout(self):
        """
        Log out of the FIX server.
        """
        logout_msg = generic_message_factory((Tag.MsgType, MsgType.Logout))
        self.send(logout_msg)
