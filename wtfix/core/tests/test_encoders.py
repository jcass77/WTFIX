import json

import pytest

from wtfix.core import encoders, decoders
from wtfix.core.exceptions import DuplicateTags
from wtfix.message.collections import FieldDict, FieldList


class TestJSONMessageEncoder:
    def test_to_json_encodes_nested_fielddict_as_expected(
        self, nested_parties_group, encoded_dict_sample
    ):
        fm = FieldDict(
            (1, "a"),
            (2, "b"),
            *nested_parties_group.values(),
            (3, "c"),
            group_templates={539: [524, 525, 538, 804], 804: [545, 805]},
        )

        assert encoders.to_json(fm) == encoded_dict_sample

    def test_to_json_fielddict_raises_exception_on_duplicate_tags_without_template_defined(
        self, nested_parties_group
    ):
        with pytest.raises(DuplicateTags):
            fm = FieldDict((1, "a"), (2, "b"), *nested_parties_group.values(), (3, "c"))

            encoders.to_json(fm)

    def test_to_json_nested_fieldlist_encodes_as_expected(
        self, nested_parties_group, encoded_list_sample
    ):
        fm = FieldList((1, "a"), (2, "b"), *nested_parties_group.values(), (3, "c"))

        assert encoders.to_json(fm) == encoded_list_sample

    def test_to_json_encodes_bytestrings(
        self, nested_parties_group, encoded_list_sample
    ):
        fm = FieldList((1, "a"), (2, b"b"), (3, "c"))

        assert encoders.to_json(fm) == json.dumps([[1, "a"], [2, "b"], [3, "c"]])


def test_serialization_is_idempotent(fieldmap_class, nested_parties_group):
    kwargs = {}
    fields = [(1, "a"), (2, "b"), *nested_parties_group.values(), (3, "c")]

    if fieldmap_class.__name__ == FieldDict.__name__:
        kwargs["group_templates"] = {539: [524, 525, 538, 804], 804: [545, 805]}

    fm = fieldmap_class(*fields, **kwargs)

    encoded = encoders.to_json(fm)
    decoded = decoders.from_json(encoded)

    assert fm == decoded

    encoded = encoders.to_json(decoded)
    decoded = decoders.from_json(encoded)

    assert fm == decoded
