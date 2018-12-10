import pytest

from wtfix.protocol.common import MsgType
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
    """Sample of a nested group based on NoNestedPartyIDs"""
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
def logon_message():
    """Sample logon message"""
    return GenericMessage(
        (35, MsgType.Logon),
        (34, "1"),
        (49, "SENDER"),
        (52, "20181206-10:24:27.018"),
        (56, "TARGET"),
        (98, "0"),
        (108, "30"),
        (553, "USERNAME"),
        (554, "PASSWORD"),
        (141, "Y"),
    )


@pytest.fixture
def sdr_message():
    """Sample of a security definition request message"""
    return GenericMessage(
        (35, MsgType.SecurityDefinitionRequest),
        (34, "1"),  # MsgSeqNum: 1
        (49, "SENDER"),  # SenderCompID
        (52, "20181127-11:33:31.505"),  # SendingTime
        (56, "TARGET"),  # TargetCompID
        (55, "^.*$"),  # Symbol
        (167, "CS"),  # SecurityType: CommonStock
        (320, "37a0b5c8afb543ec8f29eca2a44be2ec"),  # SecurityReqID
        (321, "3"),  # SecurityRequestType: all
    )


@pytest.fixture(scope="session")
def simple_encoded_msg():
    return b"8=FIX.4.4\x019=5\x0135=0\x0110=163\x01"
