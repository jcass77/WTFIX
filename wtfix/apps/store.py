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
import numbers
from collections import OrderedDict
from typing import Union, List

import aioredis
import abc
from unsync import unsync

from wtfix.apps.base import BaseApp
from wtfix.apps.sessions import ClientSessionApp
from wtfix.conf import settings
from wtfix.core import encoders, decoders, utils
from wtfix.message.message import FIXMessage

logger = settings.logger


class BaseStore(abc.ABC):
    """
    Base class for storing messages as part of a cache, queue, persistent database, etc.
    """

    @unsync
    async def initialize(self, *args, **kwargs):
        """
        Initialize the memory store.
        """
        pass

    @unsync
    async def finalize(self, *args, **kwargs):
        """
        Perform any cleanup or finalization of the memory store before the pipeline is stopped.
        """
        pass

    @unsync
    @abc.abstractmethod
    async def set(self, session_id: str, originator: str, message: FIXMessage):
        """
        Sets a message in this store.

        :param session_id: The current session ID
        :param originator: The originator of the message
        :param message: The message to store.
        """

    @unsync
    @abc.abstractmethod
    async def get(
        self, session_id: str, originator: str, seq_num: Union[str, int]
    ) -> Union[FIXMessage, None]:
        """
        Retrieves a message from the store.

        :param session_id: The current session ID
        :param originator: The originator of the message
        :param seq_num: The sequence number of the message to retrieve.
        :return: a FIXMessage object
        """

    @unsync
    @abc.abstractmethod
    async def delete(
        self, session_id: str, originator: str, seq_num: Union[str, int]
    ) -> int:
        """
        Deletes a message from the store.

        :param session_id: The current session ID
        :param originator: The originator of the message
        :param seq_num: The sequence number of the message to delete.
        :return: the number of messages that were deleted
        """

    @unsync
    @abc.abstractmethod
    async def filter(
        self, *, session_id: str = None, originator: str = None
    ) -> List[numbers.Integral]:
        """
        Retrieves all of the stored sequence numbers for the given session ID and originator.

        :param session_id: The session ID to retrieve the sequence numbers for.
        :param originator: The originator to retrieve the sequence numbers for.
        :return: a list of sequence numbers
        """

    @classmethod
    def get_key(cls, session_id: str, originator: str, seq_num: Union[str, int]) -> str:
        return f"{session_id}:{originator}:{seq_num}"


class MemoryStore(BaseStore):
    """
    Simple in-memory message store
    """

    def __init__(self):
        self._store = OrderedDict()

    @unsync
    async def set(self, session_id: str, originator: str, message: FIXMessage):
        self._store[self.get_key(session_id, originator, message.seq_num)] = message

    @unsync
    async def get(
        self, session_id: str, originator: str, seq_num: Union[str, int]
    ) -> Union[FIXMessage, None]:
        try:
            return self._store[self.get_key(session_id, originator, seq_num)]
        except KeyError:
            return None

    @unsync
    async def delete(
        self, session_id: str, originator: str, seq_num: Union[str, int]
    ) -> int:
        try:
            del self._store[self.get_key(session_id, originator, seq_num)]
            return 1
        except KeyError:
            # No key found to delete
            return 0

    @unsync
    async def filter(
        self, *, session_id: str = None, originator: str = None
    ) -> List[numbers.Integral]:

        matches = list()

        for key in self._store.keys():

            store_id, store_origin, seq_num = key.split(":")
            if session_id is None or session_id == store_id:

                if originator is None or originator == store_origin:
                    matches.append(int(seq_num))

        return sorted(matches)


class RedisStore(BaseStore):
    """
    Stores messages using redis.
    """

    def __init__(self):
        self.redis_pool = None

    @unsync
    async def initialize(self, *args, **kwargs):
        await super().initialize(*args, **kwargs)

        self.redis_pool = await aioredis.create_redis_pool(
            settings.REDIS_URI, loop=unsync.loop
        )

    @unsync
    async def finalize(self, *args, **kwargs):
        await super().finalize(*args, **kwargs)

        self.redis_pool.close()
        await self.redis_pool.wait_closed()  # Closing all open connections

    @unsync
    async def set(self, session_id: str, originator: str, message: FIXMessage):
        with await self.redis_pool as conn:
            return await conn.execute(
                "set",
                self.get_key(session_id, originator, message.seq_num),
                encoders.to_json(message),
            )

    @unsync
    async def get(
        self, session_id: str, originator: str, seq_num: Union[str, int]
    ) -> Union[FIXMessage, None]:

        with await self.redis_pool as conn:
            json_message = await conn.execute(
                "get", self.get_key(session_id, originator, seq_num)
            )

            if json_message is not None:
                return decoders.from_json(json_message)
            return json_message

    @unsync
    async def delete(
        self, session_id: str, originator: str, seq_num: Union[str, int]
    ) -> int:
        with await self.redis_pool as conn:
            return await conn.execute(
                "del", self.get_key(session_id, originator, seq_num)
            )

    @unsync
    async def filter(
        self, *, session_id: str = "*", originator: str = "*"
    ) -> List[numbers.Integral]:

        matches = list()

        with await self.redis_pool as conn:
            cur = b"0"  # set initial cursor to 0
            while cur:
                cur, keys = await conn.scan(cur, match=f"{session_id}:{originator}:*")
                for key in keys:
                    store_id, store_origin, seq_num = utils.decode(key).split(":")
                    matches.append(int(seq_num))

        return sorted(matches)


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
        self._session_app = None

    @property
    def store(self):
        return self._store

    @unsync
    async def initialize(self, *args, **kwargs):
        self._session_app = self.pipeline.apps[
            ClientSessionApp.name
        ]  # Micro-optimization: store local reference

        await self.store.initialize(*args, **kwargs)

    @unsync
    async def stop(self, *args, **kwargs):
        await self.store.finalize(*args, **kwargs)

    @unsync
    async def get_sent(self, seq_num: Union[str, int]) -> Union[FIXMessage, None]:
        return await self.store.get(
            self._session_app.session_id, self._session_app.sender, seq_num
        )

    @unsync
    async def set_sent(self, message: FIXMessage):
        return await self.store.set(
            self._session_app.session_id, self._session_app.sender, message
        )

    @unsync
    async def get_received(self, seq_num: Union[str, int]) -> Union[FIXMessage, None]:
        return await self.store.get(
            self._session_app.session_id, self._session_app.target, seq_num
        )

    @unsync
    async def set_received(self, message: FIXMessage):
        return await self.store.set(
            self._session_app.session_id, self._session_app.target, message
        )

    @unsync
    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        await self.set_received(message)

        return message

    @unsync
    async def on_send(self, message: FIXMessage) -> FIXMessage:
        await self.set_sent(message)

        return message
