from . import common


def fix_val(value):
    """Make a FIX value from a string, bytes, or number."""
    if type(value) == bytes:
        return value

    if type(value) == str:
        return bytes(value, common.ENCODING, errors=common.ENCODING_ERRORS)
    else:
        return bytes(str(value), common.ENCODING, errors=common.ENCODING_ERRORS)


def int_val(value):
    """Make an int value from string, bytes, or FIX tag value."""
    if type(value) == int:
        return value

    elif type(value) == str:
        return int(value)

    return int(value.decode(common.ENCODING, errors=common.ENCODING_ERRORS))


def fix_tag(value):
    """Make a FIX tag value from string, bytes, or integer."""
    if type(value) == bytes:
        return value

    elif type(value) == str:
        return value.encode(common.ENCODING, errors=common.ENCODING_ERRORS)

    return str(value).encode(common.ENCODING, errors=common.ENCODING_ERRORS)
