import pytest

from wtfix.message.message import BaseMessage
from ..fieldset import Group, FieldSet


@pytest.fixture(scope="session")
def fieldset_a_b():
    return FieldSet((1, b"a"), (2, b"bb"))


@pytest.fixture(scope="session")
def routing_id_group():
    return Group((215, b"2"), (216, b"a"), (217, b"b"))


@pytest.fixture(scope="session")
def nested_parties_group():
    nested_party = Group((539, b"1"), (524, b"a"), (525, b"b"), (538, b"c"))
    nested_sub_party = Group((804, b"1"), (545, b"d"), (805, b"e"))
    nested_party[0].set_group(nested_sub_party)

    return nested_party


@pytest.fixture
def sdr_message():
    return BaseMessage(
        (35, b"c"),  # MsgType: SecurityDefinitionRequest
        (34, b"1"),  # MsgSeqNum: 1
        (49, b"SENDER"),  # SenderCompID
        (52, b"20181127-11:33:31.505"),  # SendingTime
        (56, b"TARGET"),  # TargetCompID
        (55, b"^.*$"),  # Symbol
        (167, b"CS"),  # SecurityType: CommonStock
        (320, b"37a0b5c8afb543ec8f29eca2a44be2ec"),  # SecurityReqID
        (321, b"3"),  # SecurityRequestType: all
    )
