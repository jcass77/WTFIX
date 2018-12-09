import logging
from datetime import datetime

from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core.exceptions import ParsingError, ValidationError, MessageProcessingError
from wtfix.message.field import Field
from wtfix.message.fieldset import Group
from wtfix.message.message import GenericMessage
from wtfix.protocol import utils
from wtfix.protocol.common import Tag

logger = logging.getLogger(__name__)


class EncoderApp(BaseApp):
    """
    This app can be used to encode a message, and generate its header tags, right before it is transmitted.
    """

    name = "encoder_app"

    # These tags will all be generated dynamically each time as part of the encoding process.
    DYNAMIC_TAGS = {
        Tag.BeginString,
        Tag.BodyLength,
        Tag.MsgType,
        Tag.MsgSeqNum,
        Tag.SenderCompID,
        Tag.TargetCompID,
        Tag.SendingTime,
        Tag.PossDupFlag,
        Tag.DeliverToCompID
    }

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)
        self.cur_seq_num = 1  # TODO: Move to a future sequence number manager app?

    def on_send(self, message):
        message = self.encode_message(message)
        self.cur_seq_num += 1

        return message

    def encode_message(self, message):
        """
        :param message: The message to encode.

        :return: The FIX-compliant, raw binary string representation for this message with freshly
        generated header tags.
        """
        message.validate()  # Make sure the message is valid before attempting to encode.
        body = (
            b"35="
            + utils.encode(message.type)
            + settings.SOH
            + b"34="
            + utils.encode(self.cur_seq_num)
            + settings.SOH
            + b"49="
            + utils.encode(message.sender_id)
            + settings.SOH
            + b"52="
            + utils.encode(datetime.utcnow().strftime(settings.DATETIME_FORMAT)[:-3])
            + settings.SOH
            + b"56="
            + utils.encode(message.target_id)
            + settings.SOH
        )

        for field in message.values():
            if field.tag in self.DYNAMIC_TAGS:  # These tags will be generated - ignore.
                continue
            body += field.raw

        header = (
            b"8="
            + utils.encode(settings.BEGIN_STRING)
            + settings.SOH
            + b"9="
            + utils.encode(len(body))
            + settings.SOH
        )

        trailer = (
            b"10="
            + utils.encode(f"{self._checksum(header + body):03}")
            + settings.SOH
        )

        return header + body + trailer

    @staticmethod
    def _checksum(*fields):
        """
        Calculates the checksum for a type of (tag, value) bytes.
        :param fields: A tuple of bytes representing the raw header and body for a message.
        :return: The checksum for the fields.
        """
        return sum(sum(byte for byte in iter(field)) for field in fields) % 256


class DecoderApp(BaseApp):
    # TODO: Add support for raw data?
    # See: https://github.com/da4089/simplefix/blob/88613f798b300757380ef0b3f332c6d3df2b712b/simplefix/parser.py)
    """
    Translates a FIX application messages in raw (wire) format into a GenericMessage instance.
    """

    name = "decoder_app"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)
        self._group_templates = {}

    def on_receive(self, data: bytes):
        try:
            return self.decode_message(data)
        except Exception as e:
            raise MessageProcessingError() from e

    # TODO: Refactor this method into smaller units.
    def _parse_fields(self, raw_pairs, group_index=None):
        """
        Parses the raw list of field pairs recursively into Field instances.

        :param raw_pairs: A string of bytes in format b'tag=value'
        :param group_index: The index at which the previous repeating group was detected.
        :return: A list of parsed Field objects.
        """
        fields = []
        tags_seen = set()
        idx = 0
        template = []

        if group_index is not None:
            # Parsing a repeating group - skip over previously parsed pairs.
            idx = group_index
            group_identifier = Field(*raw_pairs[idx].split(b"="))

            # Retrieve the template for this repeating group
            template = self._group_templates[group_identifier.tag]

            # Add the group identifier as the first field in the list.
            fields.append(group_identifier)
            idx += 1  # Skip over identifier tag that was just processed.

        template_tags = iter(template)

        while idx < len(raw_pairs):
            tag, value = raw_pairs[idx].split(b"=", maxsplit=1)
            tag = int(tag)
            if tag in tags_seen and tag not in template:
                raise ParsingError(
                    f"No repeating group template for duplicate tag {tag}."
                )

            if tag in self._group_templates:
                # Tag denotes the start of a new repeating group.
                group_fields = self._parse_fields(raw_pairs, group_index=idx)
                group = Group(group_fields[0], *group_fields[1:])

                fields.append(group)
                # Skip over all of the fields that were processed as part of the group.
                idx += len(group)
                continue

            if group_index is not None:
                # Busy parsing a template, see if the current tag forms part of it.
                if tag == next(template_tags):
                    fields.append(Field(tag, value))
                    if tag == template[-1]:
                        # We've reached the last tag in the template, reset iterator
                        # so that it is ready to parse next group instance (if any).
                        template_tags = iter(template)
                else:
                    # All group fields processed - done.
                    break
            else:
                # Busy parsing a non-group tag.
                fields.append(Field(tag, value))
                tags_seen.add(tag)

            idx += 1

        return fields

    def add_group_template(self, identifier_tag, *args):
        if len(args) == 0:
            raise ValidationError(
                f"At least one group instance tag needs to be defined for group {identifier_tag}."
            )

        self._group_templates[identifier_tag] = args

    def remove_group_template(self, identifier_tag):
        del self._group_templates[identifier_tag]

    def is_template_tag(self, tag):
        if tag in self._group_templates:
            return True

        for template in self._group_templates.values():
            return tag in template

    # TODO: check length and checksum!
    def decode_message(self, data):
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
        if checksum_location == -1 or (
            checksum_location != 0
            and data[checksum_location - 1] != settings.SOH_BYTE
        ):
            # Checksum could not be found
            raise ParsingError(
                f"Could not find Checksum (10) in: {utils.decode(data[:20])}..."
            )

        # TODO: Raise exception instead
        # Discard fields that precede begin_string
        message_start = data.find(b"8=")
        if message_start == -1 or (
            message_start != 0 and data[message_start - 1] != settings.SOH_BYTE
        ):
            # Beginning of Message could not be determined
            raise ParsingError(
                f"Could not find BeginString (8) in: {utils.decode(data[:20])}..."
            )

        if message_start > 0:
            logger.debug(
                f"{self.name}: Discarding bytes that precede BeginString (8): {utils.decode(data[:message_start])}"
            )
            data = data[message_start:]

        data = data.rstrip(settings.SOH).split(
            settings.SOH
        )  # Remove last SOH at end of byte stream and split into fields
        fields = self._parse_fields(data)

        return GenericMessage(*fields)
