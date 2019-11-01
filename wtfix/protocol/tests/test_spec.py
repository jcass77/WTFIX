import pytest

from wtfix.conf import settings
from wtfix.core.exceptions import UnknownType, UnknownTag

protocol = settings.active_protocol


class TestMsgType:
    def test_get_name(self):
        assert protocol.MsgType.get_name("A") == "Logon"

    def test_get_name_unknown_raises_exception(self):
        with pytest.raises(UnknownType):
            protocol.MsgType.get_name("1234567890")

    def test_get_type(self):
        assert protocol.MsgType.get_type("Advertisement") == "7"

    def test_get_type_unknown_raises_exception(self):
        with pytest.raises(UnknownType):
            protocol.MsgType.get_type("abcdefghijk")


class TestTag:
    def test_get_name(self):
        assert protocol.Tag.get_name(35) == "MsgType"

    def test_get_name_unknown_raises_exception(self):
        with pytest.raises(UnknownTag):
            protocol.Tag.get_name(1234567890)

    def test_get_tag(self):
        assert protocol.Tag.get_tag("MsgType") == 35

    def test_get_tag_unknown_raises_exception(self):
        with pytest.raises(UnknownTag):
            protocol.Tag.get_tag("abcdefghijk")
