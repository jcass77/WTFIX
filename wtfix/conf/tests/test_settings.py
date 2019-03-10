import pytest

from wtfix.conf import settings, SessionSettings
from wtfix.core.exceptions import ImproperlyConfigured


class TestSettings:
    def test_has_defaults_true(self):
        assert settings.has_safe_defaults is True

    def test_has_defaults_false(self):
        settings.SESSIONS["another_session"] = {}
        assert settings.has_safe_defaults is False

        del settings.SESSIONS["another_session"]

    def test_default_session_name_returns_default_if_safe(self):
        assert settings.default_session_name == "default"

    def test_default_session_name_raises_exception_if_multiple_sessions_defined(self):
        settings.SESSIONS["another_session"] = {}

        try:
            settings.default_session_name
            assert False  # Should be unreachable
        except ImproperlyConfigured:
            # Expected
            pass

        del settings.SESSIONS["another_session"]

    def test_default_session_returns_default_if_safe(self):
        assert isinstance(settings.default_session, SessionSettings)

    def test_default_session_raises_exception_if_multiple_sessions_defined(self):
        settings.SESSIONS["another_session"] = {}

        try:
            settings.default_session
            assert False  # Should be unreachable
        except ImproperlyConfigured:
            # Expected
            pass

        del settings.SESSIONS["another_session"]

    def test_get_group_templates_returns_default_if_safe(self):
        assert settings.get_group_templates() == settings.SESSIONS["default"]["GROUP_TEMPLATES"]

    def test_get_group_templates_returns_templates_for_only_those_identifiers_specified(self):
        orig_templates = settings.SESSIONS["default"]["GROUP_TEMPLATES"]
        new_templates = {
            **orig_templates,
            **{
                1: [11, 12, 13],
                2: [21, 22, 23],
                3: [31, 32, 33]
            }
        }

        settings.SESSIONS["default"]["GROUP_TEMPLATES"] = new_templates

        group_templates = settings.get_group_templates(identifiers=[1, 3])
        assert len(group_templates) == 2
        assert all(key in group_templates.keys() for key in [1, 3])

        settings.SESSIONS["default"]["GROUP_TEMPLATES"] = orig_templates

    def test_get_group_templates_raises_exception_if_template_not_found(self):
        with pytest.raises(ImproperlyConfigured):
            settings.get_group_templates(identifiers=["999"])
