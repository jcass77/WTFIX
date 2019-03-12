import json

import pytest

from wtfix.core import encoders, decoders
from wtfix.core.exceptions import DuplicateTags
from wtfix.message.fieldset import OrderedDictFieldSet, ListFieldSet


class TestFieldSetJSONEncoder:
    def test_to_json_encodes_nested_orderedfieldset_as_expected(
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

        assert encoders.to_json(fs) == encoded_dict_sample

    def test_to_json_orderedfieldset_raises_exception_on_duplicate_tags_without_template_defined(
        self, nested_parties_group
    ):
        with pytest.raises(DuplicateTags):
            fs = OrderedDictFieldSet(
                (1, "a"),
                (2, "b"),
                nested_parties_group.identifier,
                *nested_parties_group.fields,
                (3, "c"),
            )

            encoders.to_json(fs)

    def test_to_json_nested_listfieldset_encodes_as_expected(
        self, nested_parties_group, encoded_list_sample
    ):
        fs = ListFieldSet(
            (1, "a"),
            (2, "b"),
            nested_parties_group.identifier,
            *nested_parties_group.fields,
            (3, "c"),
        )

        assert encoders.to_json(fs) == encoded_list_sample

    def test_to_json_encodes_bytestrings(
        self, nested_parties_group, encoded_list_sample
    ):
        fs = ListFieldSet(
            (1, "a"),
            (2, b"b"),
            (3, "c"),
        )

        assert encoders.to_json(fs) == json.dumps([[1, "a"], [2, "b"], [3, "c"]])


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
