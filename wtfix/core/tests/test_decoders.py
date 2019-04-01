import json

import pytest

from wtfix.core import decoders, encoders
from wtfix.core.exceptions import DuplicateTags
from wtfix.message.collections import FieldDict, FieldList


class TestJSONMessageDecoder:
    def test_default_nested_fielddict_decodes_as_expected(
        self, nested_parties_group, encoded_dict_sample
    ):
        fm = FieldDict(
            (1, "a"),
            (2, "b"),
            *nested_parties_group.values(),
            (3, "c"),
            group_templates={539: [524, 525, 538, 804], 804: [545, 805]},
        )

        assert decoders.from_json(encoded_dict_sample) == fm

    def test_default_nested_fielddict_raises_exception_on_duplicate_tags_without_template_defined(
        self, nested_parties_group, encoded_dict_sample
    ):
        with pytest.raises(DuplicateTags):
            broken_encoding = {**json.loads(encoded_dict_sample)}
            broken_encoding.pop("group_templates")
            broken_encoding = json.dumps(broken_encoding)

            decoders.from_json(broken_encoding)

    def test_default_nested_fieldlist_encodes_as_expected(
        self, nested_parties_group, encoded_list_sample
    ):
        fm = FieldList((1, "a"), (2, "b"), *nested_parties_group.values(), (3, "c"))

        assert decoders.from_json(encoded_list_sample) == fm


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
