# This file is a part of WTFIX.
#
# Copyright (C) 2018-2020 John Cass <john.cass77@gmail.com>
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
import os
import uuid
from asyncio import IncompleteReadError, LimitOverrunError
from pathlib import Path

from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core import utils
from wtfix.protocol.contextlib import connection


logger = settings.logger


class SessionApp(BaseApp):
    """
    Base class for apps that manage client / server connections.
    """

    name = "session"

    def __init__(
        self, pipeline, new_session=False, sid_path=None, sender=None, *args, **kwargs
    ):
        super().__init__(pipeline, *args, **kwargs)

        self._new_session = new_session
        self._session_id = None

        if sid_path is None:
            sid_path = Path(settings.ROOT_DIR) / f"{self.pipeline.settings.TARGET}.sid"

        self._sid_path = sid_path

        if sender is None:
            sender = self.pipeline.settings.SENDER

        self.sender = sender

        self.reader = None
        self.writer = None

    @property
    def session_id(self):
        return self._session_id

    @property
    def is_resumed(self):
        return not self._new_session

    def _resume_session(self):
        with open(self._sid_path, "r") as read_file:
            self._session_id = read_file.read()
            logger.info(f"{self.name}: Resuming session with ID: {self._session_id}.")

    def _reset_session(self):
        try:
            os.remove(self._sid_path)
        except FileNotFoundError:
            # File does not exist - skip deletion
            pass

        with open(self._sid_path, "w") as write_file:
            self._session_id = uuid.uuid4().hex
            self._new_session = True

            write_file.write(self._session_id)
            logger.info(
                f"{self.name}: Starting a new session with ID: {self._session_id}."
            )

    async def initialize(self, *args, **kwargs):
        await super().initialize(*args, **kwargs)

        if self._new_session is True:
            self._reset_session()
        else:
            try:
                self._resume_session()
            except FileNotFoundError:
                logger.warning(
                    f"Session ID file '{self._sid_path}' not found. Starting a new session..."
                )
                self._reset_session()


class ClientSessionApp(SessionApp):
    """
    Establishes a connection to a FIX server.
    """

    name = "client_session"

    def __init__(
        self, pipeline, new_session=False, sender=None, target=None, *args, **kwargs
    ):
        super().__init__(
            pipeline, new_session=new_session, sender=sender, *args, **kwargs
        )

        if target is None:
            target = self.pipeline.settings.TARGET

        self.target = target
        self._listener_task = None

    async def initialize(self, *args, **kwargs):
        """
        Establish a connection to the FIX server and start listening for messages.
        """
        await super().initialize(*args, **kwargs)
        await self._open_connection()  # Block until connection is established

    async def _open_connection(self):
        """
        Connect to the FIX server, obtaining StreamReader and StreamWriter instances for receiving messages
        from and sending messages to the server.
        """
        logger.info(
            f"{self.name}: Establishing connection to {self.pipeline.settings.HOST}:{self.pipeline.settings.PORT}..."
        )
        self.reader, self.writer = await asyncio.open_connection(
            self.pipeline.settings.HOST,
            self.pipeline.settings.PORT,
            limit=2 ** 26,  # 64Mb
        )
        logger.info(f"{self.name}: Connected!")

    async def start(self, *args, **kwargs):
        """
        Start listening for messages and log on to the server.
        """
        await super().start(*args, **kwargs)

        self._listener_task = asyncio.create_task(
            self.listen(), name=f"Task-{self.name}:listener"
        )  # Start the listener in separate task

        # Wait for connection to stabilize to make sure that we are listening
        # and that we do not miss any rejection messages.
        await asyncio.sleep(1)

    async def stop(self, *args, **kwargs):
        """
        Close the writer.
        """
        await super().stop(*args, **kwargs)

        if self._listener_task is not None:
            logger.info(f"{self.name}: Cancelling listener task...")

            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.exceptions.CancelledError:
                # Cancellation request received - close writer
                logger.info(f"{self.name}: {self._listener_task.get_name()} cancelled!")

        if self.writer is not None:
            logger.info(
                f"{self.name}: Initiating disconnect from "
                f"{self.pipeline.settings.HOST}:{self.pipeline.settings.PORT}..."
            )

            self.writer.close()
            logger.info(f"{self.name}: Session closed!")

    async def listen(self):
        """
        Listen for new messages that are sent by the server.
        """
        begin_string = utils.encode(
            f"{connection.protocol.Tag.BeginString}="
        ) + utils.encode(settings.BEGIN_STRING)

        checksum_start = settings.SOH + utils.encode(
            f"{connection.protocol.Tag.CheckSum}="
        )

        data = []

        while not self.writer.is_closing():  # Listen forever for new messages
            try:
                # Try to read a complete message.
                data = await self.reader.readuntil(
                    begin_string
                )  # Detect beginning of message.
                # TODO: should there be a timeout for reading an entire message?
                data += await self.reader.readuntil(
                    checksum_start
                )  # Detect start of checksum field.
                data += await self.reader.readuntil(
                    settings.SOH
                )  # Detect final message delimiter.

                await self.pipeline.receive(data)
                data = None

            except IncompleteReadError as e:
                # Connection was closed before a complete message could be received.
                if (
                    data
                    and utils.encode(
                        f"{connection.protocol.Tag.MsgType}={connection.protocol.MsgType.Logout}"
                    )
                    + settings.SOH
                    in data
                ):
                    await self.pipeline.receive(
                        data
                    )  # Process logout message in the pipeline as per normal

                else:
                    logger.error(
                        f"{self.name}: Unexpected EOF waiting for next chunk of partial data "
                        f"'{utils.decode(e.partial)}' ({e})."
                    )

                    # Stop listening for messages
                    asyncio.create_task(self.pipeline.stop())
                    break

            except LimitOverrunError as e:
                # Buffer limit reached before a complete message could be read - abort!
                logger.error(
                    f"{self.name}: Stream reader buffer limit exceeded! ({e})."
                )

                # Stop listening for messages
                asyncio.create_task(self.pipeline.stop())
                break

    async def on_send(self, message):
        """
        Writes an encoded message to the StreamWriter.

        :param message: A valid, encoded, FIX message.
        """
        self.writer.write(message)
        await self.writer.drain()

        del message  # Encourage garbage collection of message once it has been sent
