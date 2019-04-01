from unittest.mock import MagicMock

import pytest
from flask import Flask

from wtfix.apps.api.rest import RESTfulServiceApp
from wtfix.pipeline import BasePipeline


@pytest.fixture
async def api_app(unsync_event_loop):
    pipeline_mock = MagicMock(BasePipeline)
    api_app = RESTfulServiceApp(pipeline_mock)

    api_app._flask_app = Flask(
        __name__
    )  # Need full Flask app to initialize RESTful APIs :(
    api_app._flask_app.config["TESTING"] = True

    await api_app.initialize()
    api_app._flask_app = (
        api_app.flask_app.test_client()
    )  # Switch to test client after initialization

    return api_app
