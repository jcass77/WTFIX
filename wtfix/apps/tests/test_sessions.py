import uuid
from unittest import mock

import asyncio

import pytest

from wtfix.apps.sessions import ClientSessionApp, SessionApp
from wtfix.message import admin
from wtfix.tests.conftest import get_mock_async


class TestSessionApp:
    def test_get_session_new_session_creates_file_if_not_exists(
        self, base_pipeline, tmp_path
    ):
        sid_path = tmp_path / ".sid"

        with pytest.raises(FileNotFoundError):
            open(sid_path, "r")

        session_app = SessionApp(base_pipeline)
        session_app._get_session(new_session=True, sid_file=sid_path)

        open(sid_path, "r")

    def test_get_session_new_session_sets_attributes_correctly(
        self, base_pipeline, tmp_path
    ):
        sid_path = tmp_path / ".sid"

        session_app = SessionApp(base_pipeline)
        uuid_, is_resumed = session_app._get_session(
            new_session=True, sid_file=sid_path
        )

        assert uuid_ is not None
        assert is_resumed is False

    def test_get_session_resumed_session_sets_attributes_correctly(
        self, base_pipeline, tmp_path
    ):
        sid_path = tmp_path / ".sid"
        uuid_ = uuid.uuid4().hex

        with open(sid_path, "w") as file:
            file.write(uuid_)

        session_app = SessionApp(base_pipeline)
        read_uuid, is_resumed = session_app._get_session(sid_file=sid_path)

        assert read_uuid == uuid_
        assert is_resumed is True

    @pytest.mark.asyncio
    async def test_stop_file_does_not_exist_handled_gracefully(
        self, unsync_event_loop, base_pipeline
    ):
        session_app = SessionApp(base_pipeline)

        await session_app.stop()


class TestClientSessionApp:
    @pytest.mark.asyncio
    async def test_listen_reads_a_complete_message(
        self, unsync_event_loop, base_pipeline, encoder_app
    ):
        session_app = ClientSessionApp(base_pipeline)
        session_app.reader = asyncio.StreamReader()

        session_app.writer = mock.MagicMock(asyncio.StreamWriter)
        session_app.writer.write = mock.Mock()
        session_app.writer.transport.is_closing = mock.Mock()
        session_app.writer.transport.is_closing.return_value = False

        session_app.pipeline.receive = get_mock_async()

        msg = admin.TestRequestMessage("Test123")

        encoded_msg = encoder_app.encode_message(msg)

        session_app.listen()
        session_app.reader.feed_data(encoded_msg[:-1])  # Feed first part of message

        await asyncio.sleep(0.1)

        session_app.writer.transport.is_closing.return_value = (
            True
        )  # Close listener after this message
        session_app.reader.feed_data(encoded_msg[-1:])  # Feed second part of message

        await asyncio.sleep(0.1)

        assert session_app.pipeline.receive.mock_calls[0][1][0] == encoded_msg
