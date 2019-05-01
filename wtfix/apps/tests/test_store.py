import pytest

from wtfix.apps.store import BaseStore, MemoryStore, RedisStore, MessageStoreApp

import uuid


class TestBaseStore:
    def test_get_key(self):
        uuid_ = uuid.uuid4().hex
        assert BaseStore.get_key(uuid_, "TRADER", 123) == f"{uuid_}:TRADER:123"

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_get_returns_message(
        self, unsync_event_loop, store_class, user_notification_message
    ):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        session_id = uuid.uuid4().hex
        await store.set(session_id, "TRADER", user_notification_message)

        assert (
            await store.get(session_id, "TRADER", user_notification_message.seq_num)
            == user_notification_message
        )

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_get_not_found_returns_none(self, unsync_event_loop, store_class):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        assert await store.get(uuid.uuid4().hex, "TRADER", 123) is None

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_delete(
        self, unsync_event_loop, store_class, user_notification_message
    ):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        session_id = uuid.uuid4().hex

        # Add some messages
        for idx in range(5):
            await store.set(session_id, "TRADER", user_notification_message)
            user_notification_message.seq_num += 1

        assert await store.delete(session_id, "TRADER", 3) == 1
        assert await store.delete(session_id, "TRADER", 99) == 0  # Does not exist

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_filter_all(
        self, unsync_event_loop, store_class, user_notification_message
    ):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        session_id = uuid.uuid4().hex

        # Add some messages
        for idx in range(5):
            await store.set(session_id, "TRADER", user_notification_message)
            user_notification_message.seq_num += 1

        seq_nums = await store.filter()

        assert len(seq_nums) == 5
        assert all(seq_num in seq_nums for seq_num in range(1, 6))

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_filter_by_session_id(
        self, unsync_event_loop, store_class, user_notification_message
    ):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        session_id = uuid.uuid4().hex
        other_session_id = uuid.uuid4().hex

        # Add some messages
        for idx in range(5):
            await store.set(session_id, "TRADER", user_notification_message)
            await store.set(other_session_id, "TRADER", user_notification_message)
            user_notification_message.seq_num += 1

        seq_nums = await store.filter(session_id=session_id)

        assert len(seq_nums) == 5
        assert all(seq_num in seq_nums for seq_num in range(1, 6))

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_filter_by_originator_id(
        self, unsync_event_loop, store_class, user_notification_message
    ):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        session_id = uuid.uuid4().hex

        # Add some messages
        for idx in range(5):
            await store.set(session_id, "TRADER", user_notification_message)
            await store.set(session_id, "OTHER_TRADER", user_notification_message)
            user_notification_message.seq_num += 1

        seq_nums = await store.filter(originator="TRADER")

        assert len(seq_nums) == 5
        assert all(seq_num in seq_nums for seq_num in range(1, 6))

    @pytest.mark.parametrize("store_class", [MemoryStore, RedisStore])
    @pytest.mark.asyncio
    async def test_filter_by_session_and_originator_id(
        self, unsync_event_loop, store_class, user_notification_message
    ):
        store = store_class()
        await store.initialize()

        if isinstance(store, RedisStore):
            with await store.redis_pool as conn:
                await conn.execute("flushall")

        session_id = uuid.uuid4().hex
        other_session_id = uuid.uuid4().hex

        # Add some messages
        for idx in range(5):
            await store.set(session_id, "TRADER", user_notification_message)
            await store.set(other_session_id, "OTHER_TRADER", user_notification_message)
            user_notification_message.seq_num += 1

        seq_nums = await store.filter(session_id=session_id, originator="TRADER")

        assert len(seq_nums) == 5
        assert all(seq_num in seq_nums for seq_num in range(1, 6))


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_set(self, unsync_event_loop, user_notification_message):
        store = MemoryStore()
        await store.initialize()

        session_id = uuid.uuid4().hex
        await store.set(session_id, "TRADER", user_notification_message)

        assert len(store._store) == 1
        assert (
            store._store[f"{session_id}:TRADER:{user_notification_message.seq_num}"]
            == user_notification_message
        )


class TestRedisStore:
    @pytest.mark.asyncio
    async def test_initialize_creates_pool(
        self, unsync_event_loop, user_notification_message
    ):
        store = RedisStore()
        await store.initialize()

        assert await store.redis_pool is not None

    @pytest.mark.asyncio
    async def test_set(self, unsync_event_loop, user_notification_message):
        store = RedisStore()
        await store.initialize()

        session_id = uuid.uuid4().hex
        await store.set(session_id, "TRADER", user_notification_message)

        assert await store.redis_pool.exists(
            f"{session_id}:TRADER:{user_notification_message.seq_num}"
        )


class TestMessageStoreApp:
    @pytest.mark.asyncio
    async def test_on_receive_adds_message_to_store(
        self, unsync_event_loop, messages, base_pipeline
    ):
        store_app = MessageStoreApp(base_pipeline, store=MemoryStore())
        await store_app.initialize()

        for next_message in messages:
            await store_app.on_receive(next_message)

        for next_message in messages:
            assert await store_app.get_received(next_message.seq_num) == next_message

    @pytest.mark.asyncio
    async def test_on_send_adds_message_to_store(
        self, unsync_event_loop, messages, base_pipeline
    ):
        store_app = MessageStoreApp(base_pipeline, store=MemoryStore())
        await store_app.initialize()

        for next_message in messages:
            await store_app.on_send(next_message)

        for next_message in messages:
            assert await store_app.get_sent(next_message.seq_num) == next_message
