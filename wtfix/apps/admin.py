import asyncio
import uuid
from datetime import datetime

from unsync import unsync

from wtfix.apps.base import MessageTypeHandlerApp, on
from wtfix.conf import logger
from wtfix.message import admin
from wtfix.message.message import GenericMessage
from wtfix.core import utils
from wtfix.protocol.common import MsgType, Tag


class HeartbeatApp(MessageTypeHandlerApp):
    """
    Manages heartbeats between the FIX server and client.
    """

    name = "heartbeat"

    def __init__(self, pipeline, *args, **kwargs):
        self._heartbeat = None
        self._last_receive = None
        self._test_request_id = None  # A waiting TestRequest message for which no response has been received.
        self._test_request_response_delay = None

        super().__init__(pipeline, *args, **kwargs)

    def sec_since_last_receive(self):
        """
        :return: The number of seconds since the last message was received.
        """
        return (datetime.utcnow() - self._last_receive).total_seconds()

    def update_last_receive_timestamp(self):
        """
        Update the timestamp on which the last message was received.
        """
        self._last_receive = datetime.utcnow()

    def is_waiting(self):
        """
        :return: True if this heartbeat monitor is waiting for a response from the server for a TestRequest
        message that was sent. False otherwise.
        """
        return self._test_request_id is not None

    @unsync
    async def start(self, heartbeat):
        """
        Start the heartbeat monitor.

        :param heartbeat: The heartbeat interval in seconds.
        """
        self._heartbeat = heartbeat
        self._test_request_response_delay = 2 * self._heartbeat + 4

        connection_is_active = True
        logger.info(f"{self.name}: Starting heartbeat monitor ({self._heartbeat} second interval)...")

        while connection_is_active:
            # Keep monitoring for as long as the connection is active
            connection_is_active = await self.monitor_heartbeat().result()

        logger.info(f"{self.name}: Heartbeat monitor stopped!")

    @unsync
    async def monitor_heartbeat(self):
        """
        Monitors the heartbeat, sending TestRequest messages as necessary.

        :return: True if the monitored connection is still active. False if the server has stopped responding.
        """
        next_check = max(self._heartbeat - self.sec_since_last_receive(), 0)
        await asyncio.sleep(
            next_check
        )  # Wait until the next scheduled heartbeat check.

        if self.sec_since_last_receive() > self._heartbeat:
            # Heartbeat exceeded, send test message
            return self.check_server_is_responding().result()

        # Everything ok.
        return True

    @unsync
    async def check_server_is_responding(self):
        """
        Checks if the server is responding to TestRequest messages.

        :return: True if the server responded to the TestRequest, False otherwise.
        """

        self._test_request_id = uuid.uuid4().hex
        logger.warning(
            f"{self.name}: Heartbeat exceeded, sending test request '{self._test_request_id}'..."
        )
        self.pipeline.send(admin.TestRequest(utils.encode(self._test_request_id)))

        # Sleep while we wait for a response on the test request
        await asyncio.sleep(self._test_request_response_delay)

        if self.is_waiting():
            # No response received, force logout!
            logger.error(
                f"{self.name}: No response to test request '{self._test_request_id}', "
                f"initiating logout..."
            )
            self.pipeline.send(GenericMessage((Tag.MsgType, MsgType.Logout)))

            return False

        return True

    @on(MsgType.Logon)
    def on_logon(self, message):
        """
        Start the heartbeat monitor as soon as a logon response is received from the server.

        :param message: The Logon message received. Should contain a HeartBtInt tag that will be used
        to set the heartbeat interval to monitor.
        """
        self.start(message[Tag.HeartBtInt].as_int)

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
        self.pipeline.send(admin.Heartbeat(message[Tag.TestReqID]))

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

        return message

    def on_receive(self, message):
        """
        Update the timestamp whenever any message is received.
        :param message:
        """
        self.update_last_receive_timestamp()
        return super().on_receive(message)
