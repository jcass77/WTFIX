import logging

from ..message.field import Field
from ..message.message import GenericMessage
from ..protocol import common, utils


logger = logging.getLogger(__name__)


class ParsingError(Exception):
    pass


class MessageParser:
    # TODO: Add support for raw data?
    # See: https://github.com/da4089/simplefix/blob/88613f798b300757380ef0b3f332c6d3df2b712b/simplefix/parser.py)
    """
    Translates FIX application messages in raw (wire) format to GenericMessage instances.
    """
    def parse(self, data: bytes):
        # TODO: Cater for nested repeating groups
        """
        Constructs a GenericMessage from the provided data.

        If the byte string starts with FIX fields other than BeginString (8), these are discarded until the
        start of a message is found.

        If no BeginString (8) field is found, this function returns None.  Similarly, if (after a BeginString)
        no Checksum (10) field is found, the function returns None.

        Otherwise, it returns a GenericMessage instance initialised with the fields from the first complete message
        found in the data.
        :param data: The raw FIX message (probably received from a FIX server via a StreamReader) as a string of bytes.
        """
        checksum_location = data.find(b"10=")
        if checksum_location == -1 or (checksum_location != 0 and data[checksum_location-1] != common.SOH_BYTE):
            # Checksum could not be found
            raise ParsingError(f"Could not find Checksum (10) in: {utils.decode(data[:20])}...")

        # Discard fields that precede begin_string
        message_start = data.find(b"8=")
        if message_start == -1 or (message_start != 0 and data[message_start-1] != common.SOH_BYTE):
            # Beginning of Message could not be determined
            raise ParsingError(f"Could not find BeginString (8) in: {utils.decode(data[:20])}...")

        if message_start > 0:
            logger.debug(f"Discarding bytes that precede BeginString (8): {utils.decode(data[:message_start])}")
            data = data[message_start:]

        fields = []

        for raw_field in data.rstrip(common.SOH).split(common.SOH):
            tag, value = raw_field.split(b"=")
            fields.append(Field(tag, value))

        return GenericMessage(*fields)
