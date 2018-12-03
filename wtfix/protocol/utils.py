import numbers
from functools import singledispatch

from . import common


@singledispatch
def encode(obj):
    """Encode an object to bytes"""
    return obj.encode(common.ENCODING, errors=common.ENCODING_ERRORS)


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
def decode(obj):
    """Decode a bytes-like object to string"""
    return obj.decode(common.ENCODING, errors=common.ENCODING_ERRORS)


@decode.register(str)
def _(string):
    """Strings do not need to be decoded"""
    return string


@decode.register(numbers.Integral)
def _(n):
    """Numbers do not need to be decoded"""
    return n
