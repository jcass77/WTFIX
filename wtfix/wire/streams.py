from abc import ABCMeta

from ..message.field import Field
from ..message.fieldset import DuplicateTags, InvalidGroup, Group
from ..message.message import GenericMessage
from ..protocol import common, utils


class MessageParser(metaclass=ABCMeta):
    # TODO: Add support for raw data?
    # See: https://github.com/da4089/simplefix/blob/88613f798b300757380ef0b3f332c6d3df2b712b/simplefix/parser.py)
    """
    Translates FIX application messages in raw (wire) format to GenericMessage instances.
    """
    @classmethod
    def _handle_duplicates(cls, duplicate_tag, pairs, dup_idx):
        """
        DuplicateTags exception handler. Tries to construct a repeating Group from the provided (tag, value) pairs.

        :param duplicate_tag: the tag number that caused the duplicate tag exception.
        :param pairs: a list of parsed (tag, value) pairs
        :param dup_idx: the index in pairs where the exception occurred
        :return: a new Group instance.
        :raises: InvalidGroup a group containing duplicate_tag(s) cannot be constructed from pairs.
        """
        identifier = None
        # Look for the previous occurrence of duplicate_tag
        for idx in reversed(range(dup_idx)):
            if pairs[idx][0] == duplicate_tag:
                first_instance_idx = idx
                # Identifier field should precede first instance of duplicate_tag
                identifier_idx = idx - 1
                identifier = Field(pairs[identifier_idx][0], pairs[identifier_idx][1])
                break

        if identifier is None:
            # This shouldn't happen unless _handle_duplicates was called incorrectly.
            raise InvalidGroup(duplicate_tag, pairs, f"Could not find first occurrence of {duplicate_tag} in {pairs} "
                                                     f"before index {idx}.")

        # Everything between identifier_tag and duplicate_tag should form one GroupInstance
        instance_length = dup_idx - first_instance_idx
        group_end = first_instance_idx + (instance_length * int(identifier.value))

        return Group(identifier, *pairs[first_instance_idx:group_end])

    @classmethod
    def _build_message(cls, pairs):
        """
        Constructs a new message from the (tag, value) tuples. Takes an optimistic processing approach assuming that
        there will be no repeating groups for most messages. If repeating groups are found, the relevant portion of
        the field pairs will be re-processed.

        :param pairs: a sequence of (tag, value) pairs comprising the entire message.
        :return: a new message instance.
        """
        message = GenericMessage()

        skip_ahead = 0  # Used to skip over pairs that form part of repeating groups.
        for idx in range(len(pairs)):
            if skip_ahead > 0:
                skip_ahead -= 1
                continue

            tag = pairs[idx][0]
            try:
                # Try to add the pair to the message
                message += (tag, pairs[idx][1])
            except DuplicateTags:
                # We might have encountered a repeating group: try to parse it separately.
                group = cls._handle_duplicates(tag, pairs, idx)

                # Remove group-related Fields that were added tot he message before: everything between the
                # group identifier tag and the current loop index.
                identifier_idx = list(message._fields.keys()).index(group.identifier.tag)
                message = message[0:identifier_idx]

                # Add the newly parsed group to the message
                message.set_group(group)

                # Skip over remainder of group fields
                skip_ahead = len(group) - (idx - identifier_idx) - 1

        return message

    @classmethod
    def parse(cls, data: bytes):
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
        # Break byte string into tag=value pairs.
        start = 0
        point = 0
        in_tag = True
        tag = 0

        soh_byte = ord(common.SOH)
        equals_byte = ord(b"=")
        
        pairs = []

        while point < len(data):
            if in_tag and data[point] == equals_byte:
                tag = int(data[start:point])
                point += 1

                in_tag = False
                start = point

            elif data[point] == soh_byte:
                value = data[start:point].decode(common.ENCODING, errors=common.ENCODING_ERRORS)
                pairs.append((tag, value))
                data = data[point + 1:]
                point = 0
                start = point
                in_tag = True

            point += 1

        if len(pairs) == 0:
            return None

        # Check first pair is FIX BeginString.
        while pairs and pairs[0][0] != 8:
            # Discard pairs until we find the beginning of a message.
            pairs.pop(0)

        if len(pairs) == 0:
            return None

        # Look for checksum.
        index = 0
        while index < len(pairs) and pairs[index][0] != 10:
            index += 1

        if index == len(pairs):
            return None

        # Found checksum, so we have a complete message.
        pairs = pairs[:index + 1]
        message = cls._build_message(pairs)

        return message
