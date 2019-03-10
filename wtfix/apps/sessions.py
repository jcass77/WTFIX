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
from asyncio import IncompleteReadError, LimitOverrunError

from unsync import unsync

from wtfix.conf import logger
from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core import utils
from wtfix.protocol.common import MsgType, Tag


class SessionApp(BaseApp):
    """
    Base class for apps that manage client / server connections.
    """

    def __init__(self, pipeline, sender=None, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)
        self.reader = None
        self.writer = None

        if sender is None:
            sender = self.pipeline.settings.SENDER

        self.sender = sender
        self.next_in_seq_num = 1


class ClientSessionApp(SessionApp):
    """
    Establishes a connection to a FIX server.
    """

    name = "client_session"

    def __init__(self, pipeline, sender=None, target=None, *args, **kwargs):
        super().__init__(pipeline, sender=sender, *args, **kwargs)

        if target is None:
            target = self.pipeline.settings.TARGET

        self.target = target

    @unsync
    async def initialize(self, *args, **kwargs):
        """
        Establish a connection to the FIX server and start listening for messages.
        """
        await super().initialize(*args, **kwargs)
        await self._open_connection()  # Block until connection is established

    @unsync
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

    @unsync
    async def start(self, *args, **kwargs):
        """
        Start listening for messages and log on to the server.
        """
        await super().start(*args, **kwargs)

        self.listen()  # Start the listener
        # Wait for connection to stabilize to make sure that we are listening
        # and that we do not miss any rejection messages.
        await asyncio.sleep(1)

    @unsync
    async def stop(self, *args, **kwargs):
        """
        Close the writer.
        """
        await super().stop(*args, **kwargs)

        logger.info(f"{self.name}: Initiating disconnect...")
        self.writer.close()
        logger.info(f"{self.name}: Session closed!")

    @unsync
    async def listen(self):
        """
        Listen for new messages that are sent by the server.
        """
        begin_string = utils.encode(f"{Tag.BeginString}=") + utils.encode(
            settings.BEGIN_STRING
        )
        checksum_start = settings.SOH + utils.encode(f"{Tag.CheckSum}=")

        while not self.writer.transport.is_closing():  # Listen forever for new messages
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

                self.pipeline.receive(data)
                data = None

            except IncompleteReadError as e:
                # Connection was closed before a complete message could be received.
                if (
                    utils.encode(f"{Tag.MsgType}={MsgType.Logout}") + settings.SOH
                    in data
                ):
                    # Process logout message that was sent by the server.
                    self.pipeline.receive(
                        data
                    )  # Process logout message in the pipeline as per normal

                else:
                    logger.exception(
                        f"{self.name}: Unexpected EOF waiting for next chunk of partial data "
                        f"'{utils.decode(e.partial)}'. Initiating shutdown..."
                    )
                    self.pipeline.stop()

                return

            except LimitOverrunError:
                # Buffer limit reached before a complete message could be read - abort!
                logger.exception(
                    f"{self.name}: Stream reader buffer limit exceeded! Initiating shutdown..."
                )

                self.pipeline.stop()

                return  # Stop trying to listen for more messages.

    @unsync
    async def on_send(self, message):
        """
        Writes an encoded message to the StreamWriter.

        :param message: A valid, encoded, FIX message.
        """
        self.writer.write(message)
        await self.writer.drain()
