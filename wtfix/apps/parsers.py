from wtfix.apps.base import BaseApp
from wtfix.conf import settings
from wtfix.core.exceptions import ParsingError, ValidationError
from wtfix.message.field import Field
from wtfix.message.fieldset import Group
from wtfix.message.message import BasicMessage, GenericMessage
from wtfix.protocol.common import Tag


class BasicMessageParserApp(BaseApp):
    """
    Parses BasicMessage instances into GenericMessage instances.
    """

    name = "basic_message_parser"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)
        self._group_templates = {}

    def on_receive(self, message: BasicMessage):
        data = message.encoded_body.rstrip(settings.SOH).split(
            settings.SOH
        )  # Remove last SOH at end of byte stream and split into fields

        fields = [message[Tag.BeginString], message[Tag.BodyLength], message[Tag.MsgType], *self._parse_fields(data),
                  message[Tag.CheckSum]]

        return GenericMessage(*fields)

    # TODO: Refactor this method into smaller units.
    def _parse_fields(self, raw_pairs, group_index=None):
        """
        Parses the raw list of encoded field pairs recursively into Field instances.

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
