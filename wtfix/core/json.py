import json
from json import JSONEncoder, JSONDecoder
from json.decoder import WHITESPACE

from wtfix.message.field import FieldValue
from wtfix.message.fieldset import ListFieldSet, OrderedDictFieldSet, Group


class FieldSetEncoder(JSONEncoder):

    def _recursive_encode_group(self, group):
        fields = [(group.identifier.tag, group.size)]

        for instance in group.instances:
            for field in instance._fields:
                if isinstance(field, Group):
                    fields += (self._recursive_encode_group(field))
                else:
                    fields.append((field.tag, field.value_ref.value))

        return fields

    def default(self, o):

        if isinstance(o, ListFieldSet):
            return o._fields

        if isinstance(o, OrderedDictFieldSet):
            fields = []

            for k, v in o._fields.items():
                if isinstance(v, Group):
                    fields += self._recursive_encode_group(v)
                else:
                    fields.append((v.tag, v.value_ref.value))

            return {"fields": fields, "group_templates": o.group_templates}

        if isinstance(o, FieldValue):
            return o.value


class FieldSetDecoder(JSONDecoder):
    def decode(self, s, _w=WHITESPACE.match):
        decoded = json.loads(s)

        if isinstance(decoded, list):
            return ListFieldSet(*decoded)

        if isinstance(decoded, dict):
            fields = []

            for field in decoded["fields"]:
                fields.append((field[0], field[1]))

            return OrderedDictFieldSet(
                *fields, group_templates={int(k): v for k, v in decoded["group_templates"].items()}
            )
