import pytest

from wtfix.apps.store import BaseStore, MemoryStore, RedisStore, MessageStoreApp

import uuid


class TestBaseStore:
    def test_get_key(self):
        uuid_ = uuid.uuid4().hex
        assert BaseStore.get_key(123, "TRADER", uuid_) == f"{uuid_}_TRADER_123"

    def test_get_key_no_session(self):
        assert BaseStore.get_key(123, "TRADER") == f"TRADER_123"

    @pytest.mark.parametrize(
        "store_class", [MemoryStore, RedisStore]
    )
    @pytest.mark.asyncio
    async def test_get_returns_message(self, unsync_event_loop, store_class, user_notification_message):
        store = store_class()
        await store.initialize()

        await store.set(user_notification_message, "TRADER")

        assert await store.get(user_notification_message.seq_num, "TRADER") == user_notification_message

    @pytest.mark.parametrize(
        "store_class", [MemoryStore, RedisStore]
    )
    @pytest.mark.asyncio
    async def test_get_not_found_returns_none(self, unsync_event_loop, store_class):
        store = store_class()
        await store.initialize()

        assert await store.get(123, "TRADER") is None


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_set(self, unsync_event_loop, user_notification_message):
        store = MemoryStore()
        await store.initialize()

        await store.set(user_notification_message, "TRADER")

        assert len(store._store) == 1
        assert store._store[f"TRADER_{user_notification_message.seq_num}"] == user_notification_message


class TestRedisStore:

    @pytest.mark.asyncio
    async def test_initialize_creates_pool(self, unsync_event_loop, user_notification_message):
        store = RedisStore()
        await store.initialize()

        assert await store.redis_pool is not None

    @pytest.mark.asyncio
    async def test_set(self, unsync_event_loop, user_notification_message):
        store = RedisStore()
        await store.initialize()
        await store.set(user_notification_message, "TRADER")

        assert await store.redis_pool.exists(f"TRADER_{user_notification_message.seq_num}")


class TestMessageStoreApp:

    @pytest.mark.asyncio
    async def test_on_receive_adds_message_to_store(
        self, unsync_event_loop, messages, base_pipeline
    ):
        store_app = MessageStoreApp(base_pipeline)

        for next_message in messages:
            await store_app.on_receive(next_message)

        for next_message in messages:
            assert await store_app.get_received(next_message.seq_num) == next_message

    @pytest.mark.asyncio
    async def test_on_send_adds_message_to_store(
        self, unsync_event_loop, messages, base_pipeline
    ):
        store_app = MessageStoreApp(base_pipeline)

        for next_message in messages:
            store_app.on_send(next_message)

        for next_message in messages:
            assert await store_app.get_sent(next_message.seq_num) == next_message
