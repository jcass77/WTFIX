import pytest
from unsync import unsync

from wtfix.message import admin
from wtfix.protocol.common import MsgType, Tag
from wtfix.message.message import GenericMessage, OptimizedGenericMessage
from wtfix.message.collections import Group, FieldDict, FieldList

from pytest_socket import socket_allow_hosts


# https://github.com/miketheman/pytest-socket#usage
def pytest_runtest_setup():
    # Restrict all socket calls in order to prevent unintended web traffic during test runs. Use
    # @pytest.mark.enable_socket to enable socket connections on a per-test basis, or
    # @pytest.mark.allow_hosts(['<ip address>]) to allow connections to specific hosts.
    #
    # See: https://github.com/miketheman/pytest-socket for details.
    socket_allow_hosts(allowed=["localhost", "127.0.0.1", "::1"])


@pytest.fixture
def unsync_event_loop(event_loop):
    # Force unsync to use the same event loop as pytest-asyncio
    # See: https://github.com/pytest-dev/pytest-asyncio#event_loop

    # Stop the current unsync loop
    current_loop = unsync.loop
    if current_loop != event_loop:
        try:
            current_loop.call_soon_threadsafe(current_loop.stop)
        except RuntimeError:
            # Loop already closed.
            pass

    # Use pytest-asyncio's event loop instead
    unsync.loop = event_loop


# Add future implementations of FieldMap to this list to include in tests.
@pytest.fixture(params=[FieldDict, FieldList])
def fieldmap_class(request):
    return request.param


@pytest.fixture
def routing_id_group():
    """Example of a RoutingID repeating group"""
    return Group(
        (Tag.NoRoutingIDs, "2"),
        (Tag.RoutingType, "a"),
        (Tag.RoutingID, "b"),
        (Tag.RoutingType, "c"),
        (Tag.RoutingID, "d"),
        template=[Tag.RoutingType, Tag.RoutingID],
    )


@pytest.fixture(scope="session")
def nested_parties_group():
    """Sample of a nested group based on NoNestedPartyIDs"""
    nested_party = Group(
        (539, 2),
        (524, "a"),
        (525, "aa"),
        (538, "aaa"),
        (524, "b"),
        (525, "bb"),
        (538, "bbb"),
        template=[524, 525, 538, 804],
    )
    nested_sub_party_1 = Group(
        (804, 2), (545, "c"), (805, "cc"), (545, "d"), (805, "dd"), template=[545, 805]
    )
    nested_sub_party_2 = Group(
        (804, 2), (545, "e"), (805, "ee"), (545, "f"), (805, "ff"), template=[545, 805]
    )

    nested_party[0][nested_sub_party_1.tag] = nested_sub_party_1
    nested_party[1][nested_sub_party_2.tag] = nested_sub_party_2

    return nested_party


@pytest.fixture(params=[GenericMessage, OptimizedGenericMessage])
def generic_message_class(request):
    return request.param


@pytest.fixture
def logon_message():
    """Sample logon message"""
    message = admin.LogonMessage("USERNAME", "PASSWORD")

    message.MsgSeqNum = "1"
    message.SenderCompID = "SENDER"
    message.SendingTime = "20181206-10:24:27.018"
    message.TargetCompID = "TARGET"
    message.ResetSeqNumFlag = "Y"

    return message


@pytest.fixture
def sdr_message_fields():
    """Sample of a security definition request message fields"""
    return [
        (Tag.MsgType, MsgType.SecurityDefinitionRequest),
        (Tag.MsgSeqNum, "1"),  # MsgSeqNum: 1
        (Tag.SenderCompID, "SENDER"),  # SenderCompID
        (Tag.SendingTime, "20181127-11:33:31.505"),  # SendingTime
        (Tag.TargetCompID, "TARGET"),  # TargetCompID
        (Tag.Symbol, "^.*$"),  # Symbol
        (Tag.SecurityType, "CS"),  # SecurityType: CommonStock
        (Tag.SecurityReqID, "37a0b5c8afb543ec8f29eca2a44be2ec"),  # SecurityReqID
        (Tag.SecurityRequestType, "3"),  # SecurityRequestType: all
    ]


@pytest.fixture(scope="session")
def simple_encoded_msg():
    return b"8=FIX.4.4\x019=5\x0135=0\x0110=163\x01"
