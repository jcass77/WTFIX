import numbers
from functools import singledispatch

from wtfix.conf import settings
from wtfix.core.exceptions import TagNotFound


def index_tag(tag, data, start=0):
    """
    Finds a tag in an encoded message byte string.

    :param tag: The tag number to find.
    :param data: The encoded FIX message data to search.
    :param start: Optimization: position at which to start the search.
    :return: A tuple consisting of the tag value, the index at which the tag was found, and the index that
    denotes the end of the field in the byte string.
    :raises: TagNotFound if the tag could not be found in the encoded message data.
    """
    search_bytes = encode(tag) + b"="

    if data.startswith(search_bytes):
        start_of_field = 0
    else:
        # Ensure that the tag is prefixed by SOH to avoid partial matches.
        search_bytes = settings.SOH + search_bytes
        try:
            start_of_field = data.index(search_bytes, start)
        except ValueError as e:
            raise TagNotFound(tag, data) from e

    end_of_field = data.find(settings.SOH, start_of_field + 1)

    return (
        data[start_of_field + len(search_bytes): end_of_field],
        start_of_field,
        end_of_field,
    )


def rindex_tag(tag, data, start=0):
    """
    Finds a tag in an encoded message byte string, searching from right to left.

    :param tag: The tag number to find.
    :param data: The encoded FIX message data to search.
    :param start: Optimization: position at which to start the search.
    :return: A tuple consisting of the tag value, the index at which the tag was found, and the index that
    denotes the end of the field in the byte string.
    :raises: TagNotFound if the tag could not be found in the encoded message data.
    """
    search_bytes = encode(tag) + b"="
    try:
        start_of_field = data.rindex(search_bytes, start)
    except ValueError as e:
        raise TagNotFound(tag, data) from e

    end_of_field = data.find(settings.SOH, start_of_field + 1)

    return (
        data[start_of_field + len(search_bytes): end_of_field],
        start_of_field,
        end_of_field,
    )


def calculate_checksum(bytes_):
    """
    Calculates the checksum for bytes_.

    :param bytes_: A string of bytes representing the raw header and body of a FIX message.
    :return: The checksum value calculated over bytes_.
    """
    return sum(bytes_) % 256


@singledispatch
def encode(obj):
    """Encode an object to bytes"""
    if obj is None:
        return b"None"

    return obj.encode(settings.ENCODING, errors=settings.ENCODING_ERRORS)


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
    if obj is None:
        return "None"

    return obj.decode(settings.ENCODING, errors=settings.ENCODING_ERRORS)


@decode.register(str)
def _(string):
    """Strings do not need to be decoded"""
    return string


@decode.register(numbers.Integral)
def _(n):
    """Numbers do not need to be decoded"""
    return n
