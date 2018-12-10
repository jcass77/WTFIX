import pytest

from wtfix.conf import settings
from wtfix.core.exceptions import ValidationError, ParsingError
from wtfix.message.field import Field
from wtfix.message.message import BasicMessage


class TestBasicMessageParser:
    def test_add_group_template_too_short(self, basic_parser_app):
        with pytest.raises(ValidationError):
            basic_parser_app.add_group_template(35)

    def test_remove_group_template(self, basic_parser_app):
        basic_parser_app.add_group_template(215, 216, 217)

        assert 215 in basic_parser_app._group_templates

        basic_parser_app.remove_group_template(215)
        assert 215 not in basic_parser_app._group_templates

    def test_is_template_tag(self, basic_parser_app):
        basic_parser_app.add_group_template(215, 216, 216)

        assert basic_parser_app.is_template_tag(215) is True
        assert basic_parser_app.is_template_tag(216) is True

        assert basic_parser_app.is_template_tag(217) is False

    def test_parse_detects_duplicate_tags_without_template(self, basic_parser_app, routing_id_group):
        m = BasicMessage(message_type="a")
        m.encoded_body = routing_id_group.raw + settings.SOH + Field(1, "a").raw

        with pytest.raises(ParsingError):
            basic_parser_app.on_receive(m)

    def test_parse_repeating_group(self, basic_parser_app, routing_id_group):
        m = BasicMessage(message_type="a")
        m.encoded_body = routing_id_group.raw + Field(1, "a").raw + settings.SOH

        basic_parser_app.add_group_template(215, 216, 217)
        m = basic_parser_app.on_receive(m)

        assert 215 in m
        assert m[1].value_ref == "a"

        group = m.get_group(215)
        assert group.size == 2

        assert len(group[0]) == 2
        assert group[0][216] == "a"
        assert group[0][217] == "b"

        assert len(group[0]) == 2
        assert group[1][216] == "c"
        assert group[1][217] == "d"

    def test_parse_nested_repeating_group(self, basic_parser_app, nested_parties_group):
        m = BasicMessage(message_type="a")
        m.encoded_body = nested_parties_group.raw + Field(1, "a").raw + settings.SOH

        basic_parser_app.add_group_template(539, 524, 525, 538)
        basic_parser_app.add_group_template(804, 545, 805)

        m = basic_parser_app.on_receive(m)

        group = m.get_group(539)
        assert group.size == 2

        group_instance_1 = group[0]
        assert len(group_instance_1) == 8

        nested_group_1 = group_instance_1[804]
        assert len(nested_group_1) == 5

        nested_instance_1 = nested_group_1[0]
        assert len(nested_instance_1) == 2
        assert nested_instance_1[805] == "cc"

        assert m[1].value_ref == "a"
