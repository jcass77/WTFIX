from . import base


def fix_val(value):
    """Make a FIX value from a string, bytes, or number."""
    if type(value) == bytes:
        return value

    if type(value) == str:
        return bytes(value, base.DEFAULT_ENCODING)
    else:
        return bytes(str(value), base.DEFAULT_ENCODING)


def int_val(value):
    """Make an int value from string, bytes, or FIX tag value."""
    if type(value) == int:
        return value

    elif type(value) == str:
        return int(value)

    return int(value.decode(base.DEFAULT_ENCODING))


def fix_tag(value):
    """Make a FIX tag value from string, bytes, or integer."""
    if type(value) == bytes:
        return value

    elif type(value) == str:
        return value.encode(base.DEFAULT_ENCODING)

    return str(value).encode(base.DEFAULT_ENCODING)
