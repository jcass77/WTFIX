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
from json import JSONEncoder

from wtfix.message.field import FieldValue
from wtfix.message.fieldset import ListFieldSet, OrderedDictFieldSet, Group


def to_json(message):
    return json.dumps(message, cls=FieldSetJSONEncoder)


class FieldSetJSONEncoder(JSONEncoder):
    def _encode_group(self, group):
        """
        Recursively encode a repeating group.

        :param group: The Group to be encoded.
        :return: A list of (tag, value) tuples for each GroupInstance in the Group.
        """
        fields = []

        for instance in group.instances:
            group_fields = {}

            for field in instance._fields:
                if isinstance(field, Group):
                    group_fields[field.identifier.tag] = self._encode_group(field)
                else:
                    group_fields[field.tag] = str(field.value_ref)

            fields.append(group_fields)

        return fields

    def default(self, o):
        if isinstance(o, ListFieldSet):
            fields = []
            for field in o._fields:
                fields.append([field.tag, str(field.value_ref)])

            return fields

        if isinstance(o, OrderedDictFieldSet):
            fields = {}

            for k, v in o._fields.items():
                if isinstance(v, Group):
                    fields[v.identifier.tag] = self._encode_group(v)
                else:
                    fields[v.tag] = str(v.value_ref)

            fields["group_templates"] = o.group_templates
            return fields

        if isinstance(o, FieldValue):
            return o.value
