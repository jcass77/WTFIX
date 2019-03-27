import pytest

from wtfix.message.fieldset import OrderedDictFieldSet, ListFieldSet


@pytest.fixture
def ordered_dict_fieldset_ab():
    return OrderedDictFieldSet((1, "a"), (2, "bb"))


def pytest_generate_tests(metafunc):
    """A test generator for testing all permutations of FieldSet implementations."""
    if "fieldset_impl_abc_123" in metafunc.fixturenames:
        list_impl = ListFieldSet((1, "abc"), (2, 123))
        dict_impl = OrderedDictFieldSet((1, "abc"), (2, 123))
        metafunc.parametrize("fieldset_impl_abc_123", [list_impl, dict_impl])
