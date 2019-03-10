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


from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core.utils import GroupTemplateMixin
from wtfix.message.field import Field
from wtfix.message.message import RawMessage, generic_message_factory


class RawMessageParserApp(BaseApp, GroupTemplateMixin):
    """
    Parses RawMessage instances into GenericMessage instances.
    """

    name = "raw_message_parser"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self.group_templates = self.pipeline.settings.GROUP_TEMPLATES

    def on_receive(self, message: RawMessage):
        data = message.encoded_body.rstrip(settings.SOH).split(
            settings.SOH
        )  # Remove last SOH at end of byte stream and split into fields

        fields = [
            message.BeginString,
            message.BodyLength,
            message.MsgType,
            message.MsgSeqNum,
            *self._parse_fields(data),
            message.CheckSum,
        ]

        message = generic_message_factory(*fields, group_templates=self.group_templates)

        return message

    def _parse_fields(self, raw_pairs):
        """
        Parses the raw list of encoded field pairs into Field instances.

        :param raw_pairs: A string of bytes in format b'tag=value'
        :return: A list of parsed Field objects.
        """
        fields = []

        for raw_pair in raw_pairs:
            tag, value = raw_pair.split(b"=", maxsplit=1)
            fields.append(Field(tag, value))

        return fields
