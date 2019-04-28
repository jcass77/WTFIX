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

import importlib
from collections import OrderedDict
from typing import Union

import aioredis
import abc
from unsync import unsync

from wtfix.apps.base import BaseApp
from wtfix.apps.sessions import ClientSessionApp
from wtfix.conf import settings
from wtfix.core import encoders, decoders
from wtfix.message.message import FIXMessage

logger = settings.logger


class BaseStore(abc.ABC):
    @unsync
    @abc.abstractmethod
    async def initialize(self, *args, **kwargs):
        """
        Initialize the memory store.
        """

    @unsync
    @abc.abstractmethod
    async def set(self, message: FIXMessage, originator: str, session_id: str = None):
        """
        Sets a message in this store.

        :param message: The message to store.
        :param originator: The originator of the message
        :param session_id: The current session ID
        """

    @unsync
    @abc.abstractmethod
    async def get(
        self, seq_num: Union[str, int], originator: str, session_id: str = None
    ) -> Union[FIXMessage, None]:
        """
        Retrieves a message from the store.

        :param seq_num: The sequence number of the message to retrieve.
        :param originator: The originator of the message
        :param session_id: The current session ID
        :return: a FIXMessage object
        """

    @classmethod
    def get_key(
        cls, seq_num: Union[str, int], originator: str, session_id: str = None
    ) -> str:
        if session_id is None:
            return f"{originator}_{seq_num}"

        return f"{session_id}_{originator}_{seq_num}"


class MemoryStore(BaseStore):
    """
    Simple in-memory storage system
    """

    def __init__(self):
        self._store = OrderedDict()

    async def initialize(self, *args, **kwargs):
        pass  # Nothing to do

    @unsync
    async def set(self, message: FIXMessage, originator: str, session_id: str = None):
        self._store[
            self.get_key(message.seq_num, originator, session_id=session_id)
        ] = message

    @unsync
    async def get(
        self, seq_num: Union[str, int], originator: str, session_id: str = None
    ) -> Union[FIXMessage, None]:
        try:
            return self._store[self.get_key(seq_num, originator, session_id=session_id)]
        except KeyError:
            return None


class RedisStore(BaseStore):
    """
    Stores messages using redis.
    """

    def __init__(self):
        self.redis_pool = None

    async def initialize(self, *args, **kwargs):
        await super().initialize(*args, **kwargs)

        self.redis_pool = await aioredis.create_redis_pool(
            settings.REDIS_URI, loop=unsync.loop
        )

    @unsync
    async def set(self, message: FIXMessage, originator: str, session_id: str = None):
        with await self.redis_pool as conn:
            return await conn.execute(
                "set",
                self.get_key(message.seq_num, originator, session_id=session_id),
                encoders.to_json(message),
            )

    @unsync
    async def get(
        self, seq_num: Union[str, int], originator: str, session_id: str = None
    ) -> Union[FIXMessage, None]:

        with await self.redis_pool as conn:
            json_message = await conn.execute("get", self.get_key(seq_num, originator, session_id=session_id))

            if json_message is not None:
                return decoders.from_json(json_message)
            return json_message


class MessageStoreApp(BaseApp):
    """
    App for storing messages (either as part of a temporary cache or permanent persistence layer).
    """

    name = "message_store"

    def __init__(self, pipeline, *args, store: BaseStore = None, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        if store is None:
            store = settings.MESSAGE_STORE

            mod_name, class_name = store.rsplit(".", 1)
            module = importlib.import_module(mod_name)

            class_ = getattr(module, class_name)
            store = class_()

        self._store = store

    @unsync
    async def initialize(self, *args, **kwargs):
        await self.store.initialize(*args, **kwargs)

    @property
    def store(self):
        return self._store

    @unsync
    async def get_sent(self, seq_num: Union[str, int]) -> Union[FIXMessage, None]:
        session_app = self.pipeline.apps[ClientSessionApp.name]
        return await self.store.get(seq_num, session_app.sender, session_app.session_id)

    @unsync
    async def set_sent(self, message: FIXMessage):
        session_app = self.pipeline.apps[ClientSessionApp.name]
        return await self.store.set(message, session_app.sender, session_app.session_id)

    @unsync
    async def get_received(self, seq_num: Union[str, int]) -> Union[FIXMessage, None]:
        session_app = self.pipeline.apps[ClientSessionApp.name]
        return await self.store.get(seq_num, session_app.target, session_app.session_id)

    @unsync
    async def set_received(self, message: FIXMessage):
        session_app = self.pipeline.apps[ClientSessionApp.name]
        return await self.store.set(message, session_app.target, session_app.session_id)

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        session_app = self.pipeline.apps[ClientSessionApp.name]
        await self.store.set(message, session_app.target, session_app.session_id)

        return message

    def on_send(self, message: FIXMessage) -> FIXMessage:
        session_app = self.pipeline.apps[ClientSessionApp.name]
        self.store.set(message, session_app.sender, session_app.session_id)

        return message
