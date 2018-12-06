from wtfix.conf import settings
from wtfix.core.exceptions import ValidationError, TagNotFound
from wtfix.protocol.common import Tag, MsgType
from .fieldset import FieldSet


class GenericMessage(FieldSet):
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
        :return: Value of tag 35.
        """
        return str(self[Tag.MsgType].value_ref)

    @property
    def name(self):
        """
        Human friendly name of this type of Message, based on tag 35.
        :return:
        """
        return MsgType.get_name(self.type)

    @property
    def seq_num(self):
        """
        :return: Message sequence number
        """
        return int(self.MsgSeqNum.value)

    @seq_num.setter
    def seq_num(self, value):
        self[Tag.MsgSeqNum] = value

    @property
    def sender_id(self):
        try:
            return self.SenderCompID.value
        except TagNotFound:
            return settings.SENDER_COMP_ID

    @sender_id.setter
    def sender_id(self, value):
        self[Tag.SenderCompID] = value

    @property
    def target_id(self):
        try:
            return self.TargetCompID.value
        except TagNotFound:
            return settings.TARGET_COMP_ID

    @target_id.setter
    def target_id(self, value):
        self[Tag.TargetCompID] = value

    def validate(self, begin_string=False, length=False, checksum=False):
        """
        A well-formed message should, at minimum, contain tag 35.

        :return: A valid Message.
        :raises: ValidationError if the message is not valid.
        """
        try:
            self[Tag.MsgType]
        except TagNotFound:
            raise ValidationError(f"No 'MsgType (35)' specified for {self}.")

        return self
