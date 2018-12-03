import numbers
from functools import singledispatch

from . import common


@singledispatch
def encode(value):
    """Encode a string value"""
    return value.encode(common.ENCODING, errors=common.ENCODING_ERRORS)


@encode.register(numbers.Integral)
def _(n):
    """Encode an numeric value"""
    return encode(str(n))


@encode.register(bytes)
def _(b):
    """Bytes are already encoded"""
    return b


@encode.register(bytearray)
def _(ba):
    """Encode a bytearray"""
    return encode(bytes(ba))


@singledispatch
def decode(value):
    """Decode bytes to string"""
    return value.decode(common.ENCODING, errors=common.ENCODING_ERRORS)


@decode.register(str)
def _(text):
    """Strings do not need to be decoded"""
    return text


@decode.register(numbers.Integral)
def _(n):
    """Numbers do not need to be decoded"""
    return n
