import asyncio
from asyncio import IncompleteReadError

from unsync import unsync

from wtfix.conf import logger
from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.message.message import GenericMessage
from wtfix.core import utils
from wtfix.protocol.common import Tag, MsgType


class SessionApp(BaseApp):
    """
    Base class for apps that manage client / server connections.
    """
    def __init__(self, pipeline, sender=None, heartbeat_time=None, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)
        self.reader = None
        self.writer = None

        if sender is None:
            sender = settings.SENDER_COMP_ID

        if heartbeat_time is None:
            heartbeat_time = settings.HEARTBEAT_TIME

        self.sender = sender
        self.heartbeat_time = heartbeat_time

        self.next_in_seq_num = 1

    def connect(self, *args, **kwargs):
        """
        Override this method to establish a new connection to the FIX server
        """
        pass

    @unsync
    async def disconnect(self, *args, **kwargs):
        """
        Override this method to close a FIX server connection
        """
        pass


class ClientSessionApp(SessionApp):
    """
    Establishes a connection to a FIX server.
    """

    name = "client_session"

    def __init__(
        self,
        pipeline,
        sender=None,
        heartbeat_time=None,
        target=None,
        username=None,
        password=None,
        reset_seq_nums=True,
        test_mode=False,
        *args,
        **kwargs,
    ):
        super().__init__(
            pipeline, sender=sender, heartbeat_time=heartbeat_time, *args, **kwargs
        )

        if target is None:
            target = settings.TARGET_COMP_ID

        if username is None:
            username = settings.USERNAME

        if password is None:
            password = settings.PASSWORD

        self.target = target
        self.username = username
        self.password = password

        self.reset_seq_nums = reset_seq_nums
        self.test_mode = test_mode

        self._logout_initiated = False
        self._logged_out = False

    def initialize(self, *args, **kwargs):
        """
        Establish a connection to the FIX server and start listening for messages.
        """
        super().initialize(*args, **kwargs)

        self.open_connection().result()  # Block until connection is established

    @unsync
    async def open_connection(self):
        """
        Connect to the FIX server, obtaining StreamReader and StreamWriter instances for receiving messages
        from and sending messages to the server.
        """
        logger.info(f"{self.name}: Establishing connection to {settings.HOST}:{settings.PORT}...")
        self.reader, self.writer = await asyncio.open_connection(
            settings.HOST, settings.PORT
        )
        logger.info(f"{self.name}: Connected!")

    def connect(self, *args, **kwargs):
        super().connect(*args, **kwargs)
        self.listen()
        self.logon()

    @unsync
    async def listen(self):
        """
        Listen for new messages that are sent by the server.
        :return:
        """
        begin_string = b"8=" + utils.encode(settings.BEGIN_STRING)
        checksum_start = settings.SOH + b"10="

        data = b""
        while True:  # Listen forever for new messages
            try:
                # Try to read a complete message.
                data = await self.reader.readuntil(
                    begin_string
                )  # Detect beginning of message.
                data += await self.reader.readuntil(
                    checksum_start
                )  # Detect start of checksum field.
                data += await self.reader.readuntil(
                    settings.SOH
                )  # Detect final message delimiter.

            except IncompleteReadError as e:
                # Connection was closed before a complete message could be received.
                if b"35=5" + settings.SOH in e.partial:
                    # Process logout message that was sent by the server.
                    logger.warning(
                        f"{self.name}: Forced logout initiated by the FIX server!"
                    )
                    data = e.partial
                    break
                else:
                    if self._logout_initiated is True:
                        logger.info(f"{self.name}: Session closed by server.")
                        # Server closed connection at our request - done.
                        self._logged_out = True
                        return

                    logger.exception(
                        f"{self.name}: Unexpected EOF waiting for next chunk of partial data '{utils.decode(e.partial)}'."
                    )
                    break

            self.pipeline.receive(data)

        self.pipeline.receive(data)  # Process the last message in the buffer.

        logger.info(f"{self.name}: Closing the connection...")
        self.writer.close()
        # await self.writer.wait_closed()  Python 3.7 and up.

    @unsync
    async def logon(self):
        """
        Log on to the FIX server using the provided credentials.
        :return:
        """
        logon_msg = GenericMessage(
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
        self.pipeline.send(logon_msg)

    @unsync
    async def disconnect(self, *args, **kwargs):
        logger.info(f"{self.name}: Closing connection...")
        await super().disconnect(*args, **kwargs)

        await self.logout()
        self._logout_initiated = True

        while self._logged_out is False:
            await asyncio.sleep(1)  # Wait for server to confirm logout and close connection.

        self.writer.close()
        logger.info(f"{self.name}: Connection closed!")

    @unsync
    async def logout(self):
        """
        Log out of the FIX server.
        :return:
        """
        logout_msg = GenericMessage((Tag.MsgType, MsgType.Logout))
        self.pipeline.send(logout_msg)

    @unsync
    async def on_send(self, message):
        """
        Writes an encoded message to the StreamWriter.
        :param message: A valid, encoded, FIX message.
        """
        self.writer.write(message)
        await self.writer.drain()
