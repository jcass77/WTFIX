from unittest import mock

import pytest

from wtfix.apps.base import BaseApp
from wtfix.core.exceptions import ValidationError
from wtfix.pipeline import BasePipeline


class TestBaseApp:
    def test_check_name(self):
        with pytest.raises(ValidationError):
            BaseApp(mock.MagicMock(BasePipeline))
