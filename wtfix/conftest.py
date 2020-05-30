import asyncio
import os
from unittest import mock
from unittest.mock import MagicMock

import pytest

from wtfix.apps.sessions import ClientSessionApp
from wtfix.conf import ConnectionSettings
from wtfix.message import admin
from wtfix.message.message import GenericMessage, OptimizedGenericMessage
from wtfix.message.collections import Group, FieldDict, FieldList
from wtfix.pipeline import BasePipeline
from wtfix.protocol.contextlib import connection, connection_manager

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
def create_mock_coro(monkeypatch):
    """
    Create a mock-coro pair.

    The coro can be used to patch an async method while the mock can be used to assert calls to the mocked out method.

    Based on https://www.roguelynn.com/words/asyncio-testing/
    """

    def _create_mock_coro_pair(runtime: int = None, to_patch: str = None):
        """
        :param runtime: The number of seconds to simulate the coroutine running for (useful for testing timeouts).
        :param to_patch: The method to patch. A string similar to what normally be passed to `mock.patch`.

        :return: A tuple consisting of the mock and coroutine.
        """
        mock_ = mock.Mock()

        async def _coro(*args, **kwargs):
            nonlocal runtime
            result = mock_(*args, **kwargs)

            if runtime is not None:
                await asyncio.sleep(runtime)

            return result

        if to_patch:
            monkeypatch.setattr(to_patch, _coro)

        return mock_, _coro

    return _create_mock_coro_pair


@pytest.fixture
def base_pipeline():
    """
    Basic mock pipeline that can be used to instantiate new apps in tests.

    :return: A pipeline mock with a client session initialized.
    """
    with connection_manager() as conn:
        pipeline = MagicMock(BasePipeline)
        pipeline.settings = ConnectionSettings(conn.name)

        client_session = ClientSessionApp(pipeline, new_session=True)
        client_session.sender = pipeline.settings.SENDER
        client_session.target = pipeline.settings.TARGET

        pipeline.apps = {ClientSessionApp.name: client_session}

        yield pipeline

        try:
            os.remove(client_session._sid_path)
        except FileNotFoundError:
            # File does not exist - skip deletion
            pass


# Add future implementations of FieldMap to this list to include in tests.
@pytest.fixture(params=[FieldDict, FieldList])
def fieldmap_class(request):
    return request.param


@pytest.fixture
def routing_id_group():
    """Example of a RoutingID repeating group"""
    return Group(
        (connection.protocol.Tag.NoRoutingIDs, "2"),
        (connection.protocol.Tag.RoutingType, "a"),
        (connection.protocol.Tag.RoutingID, "b"),
        (connection.protocol.Tag.RoutingType, "c"),
        (connection.protocol.Tag.RoutingID, "d"),
        template=[
            connection.protocol.Tag.RoutingType,
            connection.protocol.Tag.RoutingID,
        ],
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
        (
            connection.protocol.Tag.MsgType,
            connection.protocol.MsgType.SecurityDefinitionRequest,
        ),
        (connection.protocol.Tag.MsgSeqNum, "1"),  # MsgSeqNum: 1
        (connection.protocol.Tag.SenderCompID, "SENDER"),  # SenderCompID
        (connection.protocol.Tag.SendingTime, "20181127-11:33:31.505"),  # SendingTime
        (connection.protocol.Tag.TargetCompID, "TARGET"),  # TargetCompID
        (connection.protocol.Tag.Symbol, "^.*$"),  # Symbol
        (connection.protocol.Tag.SecurityType, "CS"),  # SecurityType: CommonStock
        (
            connection.protocol.Tag.SecurityReqID,
            "37a0b5c8afb543ec8f29eca2a44be2ec",
        ),  # SecurityReqID
        (connection.protocol.Tag.SecurityRequestType, "3"),  # SecurityRequestType: all
    ]


@pytest.fixture(scope="session")
def simple_encoded_msg():
    return b"8=FIX.4.4\x019=5\x0135=0\x0110=163\x01"
