import pytest

from wtfix.message.fieldset import OrderedDictFieldSet, ListFieldSet


@pytest.fixture
def ordered_dict_fieldset_ab():
    return OrderedDictFieldSet((1, "a"), (2, "bb"))


@pytest.fixture(params=[OrderedDictFieldSet, ListFieldSet])
def fieldset_class(request):
    return request.param


def pytest_generate_tests(metafunc):
    """A test generator for testing all permutations of FieldSet implementations."""
    if "fieldset_impl_ab" in metafunc.fixturenames:
        list_impl = ListFieldSet((1, "a"), (2, "bb"))
        dict_impl = OrderedDictFieldSet((1, "a"), (2, "bb"))
        metafunc.parametrize("fieldset_impl_ab", [list_impl, dict_impl])
