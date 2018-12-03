from .. import utils


def test_encode_str():
    assert utils.encode("abc") == b"abc"


def test_encode_int():
    assert utils.encode(123) == b"123"


def test_encode_bytes():
    assert utils.encode(b"abc") == b"abc"


def test_encode_bytearray():
    assert utils.encode(bytearray("abc", encoding="utf-8")) == b"abc"


def test_decode_bytes():
    assert utils.decode(b"abc") == "abc"


def test_decode_bytearray():
    assert utils.decode(bytearray("abc", encoding="utf-8")) == "abc"


def test_decode_str():
    assert utils.decode("abc") == "abc"


def test_decode_int():
    assert utils.decode(123) == 123
