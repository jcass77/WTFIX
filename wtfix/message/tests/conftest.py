import pytest

from wtfix.message.collections import FieldDict, FieldList


@pytest.fixture
def ordered_dict_fieldmap_ab():
    return FieldDict((1, "a"), (2, "bb"))


def pytest_generate_tests(metafunc):
    """A test generator for testing all permutations of FieldMap implementations."""
    if "fieldmap_impl_abc_123" in metafunc.fixturenames:
        list_impl = FieldList((1, "abc"), (2, 123))
        dict_impl = FieldDict((1, "abc"), (2, 123))
        metafunc.parametrize("fieldmap_impl_abc_123", [list_impl, dict_impl])
