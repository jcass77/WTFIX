import pytest

from wtfix.message.message import GenericMessage
from wtfix.message.fieldset import Group


@pytest.fixture(scope="session")
def routing_id_group():
    """Example of a RoutingID repeating group"""
    return Group((215, b"2"), (216, b"a"), (217, b"b"), (216, b"c"), (217, b"d"))


@pytest.fixture(scope="session")
def nested_parties_group():
    """Example of a nested group based on NoNestedPartyIDs"""
    nested_party = Group(
        (539, b"2"),
        (524, b"a"),
        (525, b"aa"),
        (538, b"aaa"),
        (524, b"b"),
        (525, b"bb"),
        (538, b"bbb"),
    )
    nested_sub_party_1 = Group(
        (804, b"2"), (545, b"c"), (805, b"cc"), (545, b"d"), (805, b"dd")
    )
    nested_sub_party_2 = Group(
        (804, b"2"), (545, b"e"), (805, b"ee"), (545, b"f"), (805, b"ff")
    )

    nested_party[0].set_group(nested_sub_party_1)
    nested_party[1].set_group(nested_sub_party_2)

    return nested_party


@pytest.fixture
def sdr_message():
    """Example of a security definition request message"""
    return GenericMessage(
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
