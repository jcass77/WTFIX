import asyncio
import uuid
from datetime import datetime

from unsync import unsync

from wtfix.apps.base import MessageTypeHandlerApp, on
from wtfix.conf import logger
from wtfix.core.exceptions import MessageProcessingError
from wtfix.message import admin
from wtfix.core import utils
from wtfix.protocol.common import MsgType, Tag


class HeartbeatApp(MessageTypeHandlerApp):
    """
    Manages heartbeats between the FIX server and client.
    """

    name = "heartbeat"

    def __init__(self, pipeline, *args, **kwargs):
        self._heartbeat = 30
        self._last_receive = datetime.utcnow()
        self._test_request_id = (
            None
        )  # A waiting TestRequest message for which no response has been received.
        self._test_request_response_delay = None
        self._server_not_responding = asyncio.Event()

        super().__init__(pipeline, *args, **kwargs)

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
    async def start(self, heartbeat=30, response_delay=None):
        """
        Start the heartbeat monitor.

        :param heartbeat: The heartbeat interval in seconds.
        :param response_delay: The amount of time to wait for a TestRequest response from the server. Defaults
        to 2 * heartbeat + 4.
        """
        self._heartbeat = heartbeat

        if response_delay is None:
            response_delay = 2 * self._heartbeat + 4

        self._test_request_response_delay = response_delay

        logger.info(
            f"{self.name}: Starting heartbeat monitor ({self._heartbeat} second interval)..."
        )

        while not self._server_not_responding.is_set():
            # Keep sending heartbeats until the server stops responding.
            await self.monitor_heartbeat()

        # No response received, force logout!
        logger.error(
            f"{self.name}: No response received for test request '{self._test_request_id}', "
            f"initiating shutdown..."
        )
        self.pipeline.stop()

    @unsync
    async def monitor_heartbeat(self):
        """
        Monitors the heartbeat, sending TestRequest messages as necessary.
        """
        next_check = max(self._heartbeat - self.sec_since_last_receive(), 0)
        await asyncio.sleep(
            next_check
        )  # Wait until the next scheduled heartbeat check.

        if self.sec_since_last_receive() > self._heartbeat:
            # Heartbeat exceeded, send test message
            await self.send_test_request()

    @unsync
    async def send_test_request(self):
        """
        Checks if the server is responding to TestRequest messages.
        """

        self._test_request_id = uuid.uuid4().hex
        logger.warning(
            f"{self.name}: Heartbeat exceeded, sending test request '{self._test_request_id}'..."
        )
        self.pipeline.send(admin.TestRequest(utils.encode(self._test_request_id)))

        # Sleep while we wait for a response on the test request
        await asyncio.sleep(self._test_request_response_delay)

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
        self.pipeline.send(admin.Heartbeat(message[Tag.TestReqID].as_str))

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
