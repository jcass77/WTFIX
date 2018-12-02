import pytest

from ..base import MsgType, UnknownType, Tag, UnknownTag


class TestMsgType:
    def test_get_name(self):
        assert MsgType.get_name("7") == "Advertisement"

    def test_get_name_unknown_raises_exception(self):
        with pytest.raises(UnknownType):
            MsgType.get_name("1234567890")

    def test_get_type(self):
        assert MsgType.get_type("Advertisement") == "7"

    def test_get_type_unknown_raises_exception(self):
        with pytest.raises(UnknownType):
            MsgType.get_type("abcdefghijk")


class TestTag:
    def test_get_name(self):
        assert Tag.get_name(35) == "MsgType"

    def test_get_name_unknown_raises_exception(self):
        with pytest.raises(UnknownTag):
            Tag.get_name(1234567890)

    def test_get_tag(self):
        assert Tag.get_tag("MsgType") == 35

    def test_get_tag_unknown_raises_exception(self):
        with pytest.raises(UnknownTag):
            Tag.get_tag("abcdefghijk")
