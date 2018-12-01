from .. import utils


def test_fix_val_byte():
    assert utils.fix_val(b"a") == b"a"


def test_fix_val_str():
    assert utils.fix_val("abc") == b"abc"


def test_fix_val_int():
    assert utils.fix_val(1) == b"1"


def test_fix_tag_byte():
    assert utils.fix_tag(b"1") == b"1"


def test_fix_tag_str():
    assert utils.fix_tag("1") == b"1"


def test_fix_tag_int():
    assert utils.fix_tag(1) == b"1"


def test_int_tag_byte():
    assert utils.int_tag(b"1") == 1


def test_int_tag_str():
    assert utils.int_tag("1") == 1


def test_int_tag_int():
    assert utils.int_tag(1) == 1
