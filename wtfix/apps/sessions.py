import asyncio

from unsync import unsync

from wtfix.apps.base import BaseApp, logger
from wtfix.conf import settings
from wtfix.message.message import GenericMessage
from wtfix.protocol.common import Tag


class SessionApp(BaseApp):
    def __init__(
        self,
        handler,
        sender=None,
        heartbeat_time=None,
        *args,
        **kwargs,
    ):
        super().__init__(handler, *args, **kwargs)
        if sender is None:
            sender = settings.SENDER_COMP_ID

        if heartbeat_time is None:
            heartbeat_time = settings.HEARTBEAT_TIME

        self.sender = sender
        self.heartbeat_time = heartbeat_time

        self.next_in_seq_num = 1


class ClientSessionApp(SessionApp):

    name = "client_session"

    def __init__(
        self,
        handler,
        sender=None,
        heartbeat_time=None,
        target=None,
        username=None,
        password=None,
        reset_seq_nums=True,
        test_mode=False,
        app_ver_id=None,
        *args,
        **kwargs,
    ):
        super().__init__(handler, sender=sender, heartbeat_time=heartbeat_time, *args, **kwargs)

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
        self.app_ver_id = app_ver_id

    def initialize(self):
        self.connect().result()
        # self.logon()

    @unsync
    async def connect(self):
        logger.info("Establishing connection...")
        self.reader, self.writer = await asyncio.open_connection(
            settings.HOST, settings.PORT
        )

        message = self.logon()

        logger.info(f"Logging in with {message}...")
        self.writer.write(message.raw)

        while True:
            data = await self.reader.read(1024)
            if len(data) > 0:
                logger.info(f"Received: {data.decode()!r}")

        # logger.info("Close the connection")
        # self.writer.close()
        # await self.writer.wait_closed()

    # connect().result()

    def logon(self):
        logon_msg = GenericMessage(
            (Tag.MsgType, "A"),
            (Tag.EncryptMethod, "0"),
            (Tag.HeartBtInt, self.heartbeat_time),
            (Tag.Username, self.username),
            (Tag.Password, self.password),
        )

        if self.app_ver_id:
            logon_msg[Tag.DefaultApplVerID] = self.app_ver_id

        if self.reset_seq_nums:
            logon_msg[Tag.ResetSeqNumFlag] = "Y"

        if self.test_mode is True:
            logon_msg[Tag.TestMessageIndicator] = "Y"

        return logon_msg

        # self.handler.send(logon_msg)
