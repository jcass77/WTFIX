import pytest

from wtfix.app.base import BaseApp
from wtfix.core.exceptions import ValidationError


class TestBaseApp:
    def test_check_name(self):
        with pytest.raises(ValidationError):
            BaseApp()
