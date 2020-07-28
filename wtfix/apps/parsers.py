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

from wtfix.apps.base import BaseApp
from wtfix.core.utils import GroupTemplateMixin
from wtfix.message.field import Field
from wtfix.message.message import RawMessage, generic_message_factory, FIXMessage


class RawMessageParserApp(BaseApp, GroupTemplateMixin):
    """
    Parses RawMessage instances into GenericMessage instances.
    """

    name = "raw_message_parser"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self.group_templates = self.pipeline.settings.GROUP_TEMPLATES

    async def on_receive(self, message: RawMessage) -> FIXMessage:
        fields = (
            message.BeginString,
            message.BodyLength,
            message.MsgType,
            message.MsgSeqNum,
            *Field.fields_frombytes(message.encoded_body),
            message.CheckSum,
        )

        message = generic_message_factory(*fields, group_templates=self.group_templates)

        return message
