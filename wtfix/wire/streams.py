import logging

import wtfix.conf.global_settings
from ..message.fieldset import Group
from ..message.field import Field
from ..message.message import GenericMessage
from wtfix.core.exceptions import ValidationError
from ..protocol import utils


logger = logging.getLogger(__name__)


class ParsingError(Exception):
    pass


class MessageParser:
    # TODO: Add support for raw data?
    # See: https://github.com/da4089/simplefix/blob/88613f798b300757380ef0b3f332c6d3df2b712b/simplefix/parser.py)
    """
    Translates FIX application messages in raw (wire) format to GenericMessage instances.
    """

    def __init__(self):
        self._group_templates = {}

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
            tag, value = raw_pairs[idx].split(b"=")
            tag = int(tag)
            if tag in tags_seen and tag not in template:
                raise ParsingError(f"No repeating group template for duplicate tag {tag}.")

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
            raise ValidationError(f"At least one group instance tag needs to be defined for group {identifier_tag}.")

        self._group_templates[identifier_tag] = args

    def remove_group_template(self, identifier_tag):
        del self._group_templates[identifier_tag]

    def is_template_tag(self, tag):
        if tag in self._group_templates:
            return True

        for template in self._group_templates.values():
            return tag in template

    def parse(self, data: bytes):
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
                checksum_location != 0 and data[checksum_location - 1] != wtfix.conf.global_settings.SOH_BYTE
        ):
            # Checksum could not be found
            raise ParsingError(
                f"Could not find Checksum (10) in: {utils.decode(data[:20])}..."
            )

        # Discard fields that precede begin_string
        message_start = data.find(b"8=")
        if message_start == -1 or (
                message_start != 0 and data[message_start - 1] != wtfix.conf.global_settings.SOH_BYTE
        ):
            # Beginning of Message could not be determined
            raise ParsingError(
                f"Could not find BeginString (8) in: {utils.decode(data[:20])}..."
            )

        if message_start > 0:
            logger.debug(
                f"Discarding bytes that precede BeginString (8): {utils.decode(data[:message_start])}"
            )
            data = data[message_start:]

        data = data.rstrip(wtfix.conf.global_settings.SOH).split(wtfix.conf.global_settings.SOH)  # Remove last SOH at end of byte stream and split into fields
        fields = self._parse_fields(data)

        return GenericMessage(*fields)
