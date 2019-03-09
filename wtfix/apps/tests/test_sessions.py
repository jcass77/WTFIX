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

from unittest import mock

import asyncio

import pytest

from wtfix.apps.sessions import ClientSessionApp
from wtfix.message import admin
from wtfix.tests.conftest import get_mock_async


class TestClientSessionApp:
    @pytest.mark.asyncio
    async def test_listen_reads_a_complete_message(self, unsync_event_loop, base_pipeline, encoder_app):
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

        session_app.writer.transport.is_closing.return_value = True  # Close listener after this message
        session_app.reader.feed_data(encoded_msg[-1:])  # Feed second part of message

        await asyncio.sleep(0.1)

        assert session_app.pipeline.receive.mock_calls[0][1][0] == encoded_msg
