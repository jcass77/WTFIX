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

import json
from json import JSONDecoder
from json.decoder import WHITESPACE

from wtfix.message.message import OptimizedGenericMessage, GenericMessage


def from_json(json_):
    return json.loads(json_, cls=JSONMessageDecoder)


class JSONMessageDecoder(JSONDecoder):
    def _decode_group(self, group_identifier, group_instances):
        """ Recursively decode a repeating group.

        :param group_identifier: The Group identifier tag.
        :param group_instances: A list of lists of (tag, value) tuples that make up each group instance.
        :return: The list of (tag, values) that form the entire repeating group.
        """
        fields = [
            (int(group_identifier), len(group_instances))
        ]  # Add identifier Field first

        for instance in group_instances:
            group_fields = []

            for k, v in instance.items():
                if isinstance(v, list):
                    group_fields += self._decode_group(k, v)
                else:
                    group_fields.append((int(k), v))

            fields += group_fields

        return fields

    def decode(self, s, _w=WHITESPACE.match):
        decoded = json.loads(s)

        if isinstance(decoded, list):
            return GenericMessage(*decoded)

        if isinstance(decoded, dict):
            fields = []
            group_templates = {
                int(k): v for k, v in decoded.pop("group_templates", {}).items()
            }

            for k, v in decoded.items():
                if isinstance(v, list):
                    # Group fields
                    fields += self._decode_group(k, v)
                else:
                    fields.append((int(k), v))

            return OptimizedGenericMessage(*fields, group_templates=group_templates)
