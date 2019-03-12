import asyncio
from unittest.mock import MagicMock

import pytest
import requests

from wtfix.apps.api.rest import RESTfulServiceApp
from wtfix.pipeline import BasePipeline


@pytest.fixture
@pytest.mark.asyncio
async def api_app(unsync_event_loop):
    pipeline_mock = MagicMock(BasePipeline)
    api_app = RESTfulServiceApp(pipeline_mock)

    try:
        await api_app.initialize()
    except OSError:
        # Address already in use? Wait for previous instance of flask to shut down properly.
        await asyncio.sleep(0.5)
        await api_app.initialize()

    yield api_app

    try:
        await api_app.stop()
    except (requests.exceptions.ConnectionError, RuntimeError):
        # App already stopped? Ignore
        pass
