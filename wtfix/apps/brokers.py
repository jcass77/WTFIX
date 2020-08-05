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

import aioredis

from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core import decoders, utils

logger = settings.logger


class RedisPubSubApp(BaseApp):
    """
    Pub/Sub redis broker
    """

    name = "redis_pubsub"

    SEND_CHANNEL = "channel:send"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self.redis_pool = None
        self._channel_reader_task = None

    async def _send_channel_reader(self):
        try:
            with await self.redis_pool as conn:
                await conn.subscribe(self.SEND_CHANNEL)

                send_channel = conn.channels[self.SEND_CHANNEL]

                while await send_channel.wait_message():
                    message = await send_channel.get()
                    message = decoders.from_json(utils.decode(message))
                    asyncio.create_task(
                        self.send(message)
                    )  # Pass message on to pipeline

        except aioredis.ChannelClosedError:
            # Shutting down...
            logger.info(f"{self.name}: Unsubscribed from {send_channel.name}.")

    async def initialize(self, *args, **kwargs):
        await super().initialize(*args, **kwargs)

        self.redis_pool = await aioredis.create_redis_pool(settings.REDIS_WTFIX_URI)

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)

        self._channel_reader_task = asyncio.create_task(
            self._send_channel_reader(), name=f"Task-{self.name}:channel_reader"
        )

    async def stop(self, *args, **kwargs):
        await super().stop(*args, **kwargs)

        if self._channel_reader_task is not None:
            self._channel_reader_task.cancel()
            try:
                await self._channel_reader_task
            except asyncio.exceptions.CancelledError:
                # Cancellation request received - close connections....
                logger.info(
                    f"{self.name}: {self._channel_reader_task.get_name()} cancelled!"
                )

        with await self.redis_pool as conn:
            await conn.unsubscribe(self.SEND_CHANNEL)

        self.redis_pool.close()
        await self.redis_pool.wait_closed()  # Closing all open connections
