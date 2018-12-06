import pytest

from wtfix.message.message import GenericMessage
from wtfix.message.fieldset import Group

from pytest_socket import disable_socket


# https://github.com/miketheman/pytest-socket#usage
def pytest_runtest_setup():
    disable_socket()


@pytest.fixture(scope="session")
def routing_id_group():
    """Example of a RoutingID repeating group"""
    return Group((215, "2"), (216, "a"), (217, "b"), (216, "c"), (217, "d"))


@pytest.fixture(scope="session")
def nested_parties_group():
    """Example of a nested group based on NoNestedPartyIDs"""
    nested_party = Group(
        (539, "2"),
        (524, "a"),
        (525, "aa"),
        (538, "aaa"),
        (524, "b"),
        (525, "bb"),
        (538, "bbb"),
    )
    nested_sub_party_1 = Group(
        (804, "2"), (545, "c"), (805, "cc"), (545, "d"), (805, "dd")
    )
    nested_sub_party_2 = Group(
        (804, "2"), (545, "e"), (805, "ee"), (545, "f"), (805, "ff")
    )

    nested_party[0].set_group(nested_sub_party_1)
    nested_party[1].set_group(nested_sub_party_2)

    return nested_party


@pytest.fixture
def sdr_message():
    """Example of a security definition request message"""
    return GenericMessage(
        (35, "c"),  # MsgType: SecurityDefinitionRequest
        (34, "1"),  # MsgSeqNum: 1
        (49, "SENDER"),  # SenderCompID
        (52, "20181127-11:33:31.505"),  # SendingTime
        (56, "TARGET"),  # TargetCompID
        (55, "^.*$"),  # Symbol
        (167, "CS"),  # SecurityType: CommonStock
        (320, "37a0b5c8afb543ec8f29eca2a44be2ec"),  # SecurityReqID
        (321, "3"),  # SecurityRequestType: all
    )
