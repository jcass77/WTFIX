import logging
from datetime import datetime

from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core.exceptions import (
    ParsingError,
    ValidationError,
    MessageProcessingError,
    TagNotFound,
)
from wtfix.message.field import Field
from wtfix.message.fieldset import Group
from wtfix.message.message import GenericMessage
from wtfix.core import utils
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
        Tag.DeliverToCompID,
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
            b"10=" + utils.encode(f"{utils.calculate_checksum(header + body):03}") + settings.SOH
        )

        return header + body + trailer


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

    @classmethod
    def check_begin_string(cls, data, start=0):
        """
        Checks the BeginString tag (8) for the encoded message data provided.

        :param data: An encoded FIX message.
        :param start: Position at which to start the search. Usually 0.
        :return: A tuple consisting of the value of the BeginString tag in encoded byte format, and the
        index at which the tag ends.
        :raises: ParsingError if the BeginString tag can either not be found, or if it is not the first tag
        in the message.
        """
        try:
            begin_string, start, tag_end = utils.index_tag(8, data, start=start)
        except TagNotFound as e:
            raise ParsingError(f"BeginString (8) not found in {utils.decode(data)}.") from e

        if start != 0:
            # Begin string was not found at start of Message
            raise ParsingError(
                f"Message does not start with BeginString (8): {utils.decode(data)}."
            )

        return begin_string, tag_end

    @classmethod
    def check_body_length(cls, data, start=0, body_end=None):
        """
        Checks the BodyLength tag (9) for the encoded message data provided.

        :param data: An encoded FIX message.
        :param start: Optimization: the position at which to start the search.
        :param body_end: Optimization: the index at which the body terminates in data. If this value
        is not provided then the data byte string will be parsed to look for the Checksum (10) tag,
        which should denote the end of the message body.
        :return: A tuple consisting of the value of the BodyLength tag in encoded byte format, and the
        index at which the tag ends.
        :raises: ParsingError if the BodyLength tag can either not be found, or if the actual body
        length does not match the check value provided by the server.
        """
        try:
            if body_end is None:
                checksum_check, body_end, _ = utils.rindex_tag(10, data)

            body_length, _, tag_end = utils.index_tag(9, data, start=start)
        except TagNotFound as e:
            raise ParsingError(f"BodyLength (9) not found in {utils.decode(data)}.") from e

        body_length = int(body_length)
        actual_length = body_end - tag_end - 1
        if actual_length != body_length:
            raise ParsingError(
                f"Message has wrong body length. Expected: {body_length}, actual: {actual_length}."
            )

        return body_length, tag_end

    @classmethod
    def check_checksum(cls, data, body_start=0, body_end=None):
        """
        Checks the Checksum tag (10) for the encoded message data provided.

        :param data: An encoded FIX message.
        :param body_start: The index in the encoded message at which the message body starts.
        :param body_end: The index in the encoded message at which the message body ends.
        If this value is not provided, then it will default to the index at which the Checksum tag starts.
        :return: A tuple consisting of the value of the BeginString tag in encoded byte format, and the
        index at which the tag ends.
        :raises: ParsingError if the BeginString tag can either not be found, or if it is not the first tag
        in the message.
        """
        try:
            checksum, checksum_start, checksum_end = utils.rindex_tag(10, data)
        except TagNotFound as e:
            raise ParsingError(
                f"Checksum (10) not found in {utils.decode(data)}."
            ) from e

        if len(data) != checksum_end + 1:
            raise ParsingError(
                f"Unexpected bytes following checksum: {data[checksum_start:]}."
            )

        if body_end is None:
            body_end = checksum_start

        checksum = int(checksum)
        calc_checksum = utils.calculate_checksum(data[body_start:body_end])
        if checksum != calc_checksum:
            raise ParsingError(
                f"Checksum check failed. Calculated value of {calc_checksum} does not match {checksum}."
            )

        return checksum, checksum_end

    # TODO: check length and checksum!
    def decode_message(self, data):
        """
        Constructs a GenericMessage from the provided data. Also uses the BeginString (8), BodyLength (9),
        and Checksum (10) tags to verify the message before decoding.

        :param data: The raw FIX message (probably received from a FIX server via a StreamReader) as a string of bytes.
        :return: a GenericMessage instance initialised from the raw data.
        """
        # Message MUST start with begin_string
        begin_string, begin_tag_end = self.check_begin_string(data, start=0)

        # Optimization: Find checksum now so that we can re-use its
        # index in both the body_length and subsequent 'check_checksum' calls.
        checksum_check, checksum_tag_start, _ = utils.rindex_tag(10, data)

        # Body length must match what was sent by server
        self.check_body_length(
            data, start=begin_tag_end, body_end=checksum_tag_start
        )

        checksum, _ = self.check_checksum(data, body_start=0, body_end=checksum_tag_start)

        data = data.rstrip(settings.SOH).split(
            settings.SOH
        )  # Remove last SOH at end of byte stream and split into fields
        fields = self._parse_fields(data)

        return GenericMessage(*fields)
