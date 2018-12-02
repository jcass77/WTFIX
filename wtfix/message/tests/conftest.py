import pytest

from wtfix.message.fieldset import FieldSet


@pytest.fixture(scope="session")
def fieldset_a_b():
    """A simple fieldset consisting of just two dummy fields"""
    return FieldSet((1, b"a"), (2, b"bb"))
