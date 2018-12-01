from abc import ABCMeta
import collections

from ..protocol import base, utils
from .fieldset import FieldSet


class ValidationError(Exception):
    pass


class BaseMessage(FieldSet, metaclass=ABCMeta):
    """
    The most basic type of FIX Message, consisting of one or more Fields in a FieldSet.

    We think of FIX messages as lists of (tag, value) pairs, where tag is a number and value is a bytestring.
    """

    def __init__(self, *fields, begin_string=b"FIX.4.4"):
        """
        Constructor.

        :param fields: The fields that the message should consist of. Can be (tag, value) tuples,
        a list of Field instances, or tag, value arguments.
        :param begin_string: The being string that will be used for tag number 8 in this message's raw format.
        """
        super().__init__(*fields)
        self.begin_string = begin_string

    @property
    def type(self):
        """
        The type of this Message, as denoted by tag 35.
        :return: Bytestring for tag 35.
        """
        return self._fields[base.Tag.MsgType].value

    @property
    def name(self):
        """
        Human friendly name of this type of Message, based on tag 35.
        :return:
        """
        return base.MsgType.get_name(self.type)

    @property
    def seq_num(self):
        """
        :return: Message sequence number
        """
        return int(self.MsgSeqNum.decode())

    @property
    def sender_id(self):
        return self.SenderCompID.decode()

    @property
    def target_id(self):
        return self.TargetCompID.decode()

    @property
    def raw(self):
        """
        :returns: The FIX-compliant, raw binary string representation for this message.
        """
        self.validate()  # Make sure the message is valid before attempting to encode.

        body = b""
        for field in self.fields:
            if field.tag in (8, 9, 35, 10):  # Standard header and trailer fields will be handled separately - ignore.
                continue
            body += field.raw

        header = b"8=" + self.begin_string + base.SOH \
                 + b"9=" + utils.fix_val(len(body)) + base.SOH \
                 + b"35=" + utils.fix_val(self.type) + base.SOH

        trailer = b"10=" + utils.fix_val(self._checksum(header + body)) + base.SOH

        return header + body + trailer

    def validate(self):
        """
        A well-formed message should, at minimum, contain tag 35.

        :return: A valid Message.
        :raises: ValidationError if the message is not valid.
        """
        try:
            self._fields[base.Tag.MsgType]
        except KeyError:
            raise ValidationError("No 'MsgType (35)' specified.")

        return self

    @staticmethod
    def _checksum(*args):
        return sum(sum(byte for byte in iter(field)) for field in args) % 256

    def clear(self):
        """
        Clears all Fields from this Message.
        """
        self._fields = collections.OrderedDict()
