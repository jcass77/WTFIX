import uuid
from datetime import datetime
from unittest import mock

import asyncio

import pytest

from wtfix.apps.sessions import ClientSessionApp, SessionApp
from wtfix.conf import settings
from wtfix.message import admin


class TestSessionApp:
    def test_resume_session_sets_session_id(self, base_pipeline, tmp_path):
        sid_path = tmp_path / ".sid"
        uuid_ = uuid.uuid4().hex

        with open(sid_path, "w") as file:
            file.write(uuid_)

        session_app = SessionApp(base_pipeline, new_session=False, sid_path=sid_path)
        session_app._resume_session()

        assert session_app.session_id == uuid_
        assert session_app.is_resumed is True

    def test_reset_session_creates_file_if_not_exists(self, base_pipeline, tmp_path):
        sid_path = tmp_path / ".sid"

        with pytest.raises(FileNotFoundError):
            open(sid_path, "r")

        session_app = SessionApp(base_pipeline, new_session=True, sid_path=sid_path)
        session_app._reset_session()

        open(sid_path, "r")

    def test_reset_session_resets_session_id(self, base_pipeline, tmp_path):
        sid_path = tmp_path / ".sid"
        uuid_ = uuid.uuid4().hex

        session_app = SessionApp(base_pipeline, new_session=True, sid_path=sid_path)
        session_app._session_id = uuid_

        session_app._reset_session()

        assert session_app.session_id != uuid_
        assert session_app.is_resumed is False

    @pytest.mark.asyncio
    async def test_stop_file_does_not_exist_handled_gracefully(self, base_pipeline):
        session_app = SessionApp(base_pipeline)

        await session_app.stop()


class TestClientSessionApp:
    @pytest.mark.asyncio
    async def test_listen_reads_a_complete_message(self, base_pipeline, encoder_app):
        session_app = ClientSessionApp(base_pipeline)
        session_app.reader = asyncio.StreamReader()

        session_app.writer = mock.MagicMock(asyncio.StreamWriter)
        session_app.writer.write = mock.Mock()
        session_app.writer.is_closing = mock.Mock()
        session_app.writer.is_closing.return_value = False

        msg = admin.TestRequestMessage("Test123")
        msg.SendingTime = datetime.utcnow().strftime(settings.DATETIME_FORMAT)[:-3]

        encoded_msg = encoder_app.encode_message(msg)

        asyncio.create_task(session_app.listen())
        session_app.reader.feed_data(encoded_msg[:-1])  # Feed first part of message

        await asyncio.sleep(0.1)

        session_app.writer.is_closing.return_value = (
            True  # Close listener after this message
        )
        session_app.reader.feed_data(encoded_msg[-1:])  # Feed second part of message

        await asyncio.sleep(0.1)

        assert session_app.pipeline.receive.mock_calls[0][1][0] == encoded_msg
