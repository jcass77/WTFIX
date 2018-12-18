from wtfix.apps.base import BaseApp
from wtfix.conf import settings, logger
from wtfix.message.field import Field
from wtfix.message.message import RawMessage, generic_message_factory
from wtfix.protocol.common import Tag


class BasicMessageParserApp(BaseApp):
    """
    Parses RawMessage instances into GenericMessage instances.
    """

    name = "basic_message_parser"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)
        self._group_templates = {}

    def on_receive(self, message: RawMessage):
        data = message.encoded_body.rstrip(settings.SOH).split(
            settings.SOH
        )  # Remove last SOH at end of byte stream and split into fields

        fields = [message[Tag.BeginString], message[Tag.BodyLength], message[Tag.MsgType], *self._parse_fields(data),
                  message[Tag.CheckSum]]

        message = generic_message_factory(*fields)
        logger.info(f" <-- {message}")

        return message

    def _parse_fields(self, raw_pairs):
        """
        Parses the raw list of encoded field pairs into Field instances.

        :param raw_pairs: A string of bytes in format b'tag=value'
        :return: A list of parsed Field objects.
        """
        fields = []

        for raw_pair in raw_pairs:
            tag, value = raw_pair.split(b"=", maxsplit=1)
            fields.append(Field(tag, value))

        return fields
