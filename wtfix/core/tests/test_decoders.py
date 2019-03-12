import json

import pytest

from wtfix.core import decoders, encoders
from wtfix.core.exceptions import DuplicateTags
from wtfix.message.fieldset import OrderedDictFieldSet, ListFieldSet


class TestFieldSetJSONDecoder:
    def test_default_nested_orderedfieldset_decodes_as_expected(
        self, nested_parties_group, encoded_dict_sample
    ):
        fs = OrderedDictFieldSet(
            (1, "a"),
            (2, "b"),
            nested_parties_group.identifier,
            *nested_parties_group.fields,
            (3, "c"),
            group_templates={539: [524, 525, 538, 804], 804: [545, 805]},
        )

        assert decoders.from_json(encoded_dict_sample) == fs

    def test_default_nested_orderedfieldset_raises_exception_on_duplicate_tags_without_template_defined(
        self, nested_parties_group, encoded_dict_sample
    ):
        with pytest.raises(DuplicateTags):
            broken_encoding = {**json.loads(encoded_dict_sample)}
            broken_encoding.pop("group_templates")
            broken_encoding = json.dumps(broken_encoding)

            decoders.from_json(broken_encoding)

    def test_default_nested_listfieldset_encodes_as_expected(
        self, nested_parties_group, encoded_list_sample
    ):
        fs = ListFieldSet(
            (1, "a"),
            (2, "b"),
            nested_parties_group.identifier,
            *nested_parties_group.fields,
            (3, "c"),
        )

        assert decoders.from_json(encoded_list_sample) == fs


def test_serialization_is_idempotent(fieldset_class, nested_parties_group):
    kwargs = {}
    fields = [
        (1, "a"),
        (2, "b"),
        nested_parties_group.identifier,
        *nested_parties_group.fields,
        (3, "c"),
    ]

    if fieldset_class.__name__ == OrderedDictFieldSet.__name__:
        kwargs["group_templates"] = {539: [524, 525, 538, 804], 804: [545, 805]}

    fs = fieldset_class(*fields, **kwargs)

    encoded = encoders.to_json(fs)
    decoded = decoders.from_json(encoded)

    assert fs == decoded

    encoded = encoders.to_json(decoded)
    decoded = decoders.from_json(encoded)

    assert fs == decoded
