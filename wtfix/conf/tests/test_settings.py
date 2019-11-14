import pytest

from wtfix.conf import settings, ConnectionSettings
from wtfix.core.exceptions import ImproperlyConfigured
from wtfix.protocol.contextlib import connection


class TestSettings:
    def test_get_group_templates_returns_templates_for_only_those_identifiers_specified(
        self
    ):
        orig_templates = settings.CONNECTIONS[connection.name]["GROUP_TEMPLATES"]
        new_templates = {
            **orig_templates,
            **{1: [11, 12, 13], 2: [21, 22, 23], 3: [31, 32, 33]},
        }

        settings.CONNECTIONS[connection.name]["GROUP_TEMPLATES"] = new_templates

        group_templates = settings.get_group_templates(
            connection.name, identifiers=[1, 3]
        )
        assert len(group_templates) == 2
        assert all(key in group_templates.keys() for key in [1, 3])

        settings.CONNECTIONS[connection.name]["GROUP_TEMPLATES"] = orig_templates

    def test_get_group_templates_raises_exception_if_template_not_found(self):
        with pytest.raises(ImproperlyConfigured):
            settings.get_group_templates(connection.name, identifiers=["999"])


class TestConnectionSettings:
    def test_get_group_templates_returns_templates_for_only_those_identifiers_specified(
        self
    ):
        orig_templates = settings.CONNECTIONS[connection.name]["GROUP_TEMPLATES"]
        new_templates = {
            **orig_templates,
            **{1: [11, 12, 13], 2: [21, 22, 23], 3: [31, 32, 33]},
        }

        settings.CONNECTIONS[connection.name]["GROUP_TEMPLATES"] = new_templates

        conn_settings = ConnectionSettings(connection.name)

        group_templates = conn_settings.get_group_templates(identifiers=[1, 3])
        assert len(group_templates) == 2
        assert all(key in group_templates.keys() for key in [1, 3])

        settings.CONNECTIONS[connection.name]["GROUP_TEMPLATES"] = orig_templates

    def test_get_group_templates_raises_exception_if_template_not_found(self):
        with pytest.raises(ImproperlyConfigured):
            conn_settings = ConnectionSettings(connection.name)
            conn_settings.get_group_templates(identifiers=["999"])
