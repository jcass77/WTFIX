import pytest

from wtfix.core import utils
from wtfix.core.exceptions import TagNotFound


def test_find_tag_start_of_message(simple_encoded_msg):
    assert utils.index_tag(8, simple_encoded_msg) == (b"FIX.4.4", 0, 9)


def test_find_tag(simple_encoded_msg):
    assert utils.index_tag(9, simple_encoded_msg) == (b"5", 9, 13)


def test_find_tag_not_found_raises_exception(simple_encoded_msg):
    with pytest.raises(TagNotFound):
        utils.index_tag(123, simple_encoded_msg)


def test_rfind(simple_encoded_msg):
    assert utils.rindex_tag(10, simple_encoded_msg) == (b"163", 19, 25)


def test_checksum():
    assert (
            utils.calculate_checksum(
                b"8=FIXT.1.1\x019=75\x0135=A\x0134=1\x0149=ROFX\x0152=20170417-18:29:09.599\x0156=eco\x0198=0\x01"
                + b"108=20\x01141=Y\x011137=9\x01",
                )
            == 79
    )


def test_encode_str():
    assert utils.encode("abc") == b"abc"


def test_encode_int():
    assert utils.encode(123) == b"123"


def test_encode_bytes():
    assert utils.encode(b"abc") == b"abc"


def test_encode_bytearray():
    assert utils.encode(bytearray("abc", encoding="utf-8")) == b"abc"


def test_encode_none():
    assert utils.encode(None) == b"None"


def test_decode_bytes():
    assert utils.decode(b"abc") == "abc"


def test_decode_bytearray():
    assert utils.decode(bytearray("abc", encoding="utf-8")) == "abc"


def test_decode_str():
    assert utils.decode("abc") == "abc"


def test_decode_int():
    assert utils.decode(123) == 123


def test_decode_none():
    assert utils.decode(None) == "None"
