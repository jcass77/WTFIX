import pytest

from wtfix.message.fieldset import FieldSet


@pytest.fixture(scope="session")
def fieldset_a_b():
    """A simple fieldset consisting of just two dummy fields"""
    return FieldSet((1, "a"), (2, "bb"))
