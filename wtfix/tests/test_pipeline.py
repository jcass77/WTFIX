from asyncio import futures
from unittest.mock import MagicMock

import pytest

from wtfix.conf import settings
from wtfix.core.exceptions import ValidationError, ImproperlyConfigured
from wtfix.message import admin
from wtfix.pipeline import BasePipeline
from wtfix.tests.conftest import get_mock_async, get_slow_mock_async


class TestBasePipeline:
    def test_load_apps_installs_apps_in_pipeline(self, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        assert len(pipeline.apps) == 3

    def test_load_apps_falls_back_to_settings(self):
        pipeline = BasePipeline()
        assert len(pipeline.apps) == len(pipeline.settings.PIPELINE_APPS)
        assert all(
            f"{app.__class__.__module__}.{app.__class__.__name__}"
            in pipeline.settings.PIPELINE_APPS
            for app in pipeline.apps.values()
        )

    def test_load_apps_raises_exception_if_no_apps_installed(self):
        with pytest.raises(ImproperlyConfigured):
            orig_apps = settings.default_connection.PIPELINE_APPS

            settings.CONNECTIONS["default"]["PIPELINE_APPS"] = []
            BasePipeline()

            settings.default_connection.PIPELINE_APPS = orig_apps

    def test_prep_processing_pipeline_inbound_order(self, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        func, app_chain = pipeline._setup_message_handling(pipeline.INBOUND_PROCESSING)
        assert func == "on_receive"
        assert next(app_chain).name == "below"
        assert next(app_chain).name == "middle"
        assert next(app_chain).name == "top"

    def test_pre_processing_pipeline_outbound_order(self, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)
        func, app_chain = pipeline._setup_message_handling(pipeline.OUTBOUND_PROCESSING)

        assert func == "on_send"
        assert next(app_chain).name == "top"
        assert next(app_chain).name == "middle"
        assert next(app_chain).name == "below"

    def test_prep_processing_pipeline_direction_unknown_raises_exception(
        self, three_level_app_chain
    ):
        with pytest.raises(ValidationError):
            pipeline = BasePipeline(installed_apps=three_level_app_chain)
            pipeline._setup_message_handling("inbound")

    @pytest.mark.asyncio
    async def test_initialize_initializes_each_app_exactly_once(
        self, unsync_event_loop, three_level_app_chain
    ):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        # Mock all of the apps that have been configured for this pipeline.
        for key, app in pipeline._installed_apps.items():
            app_mock = MagicMock(app.__class__)
            app_mock.name = app.name
            app_mock.initialize = get_mock_async()
            app_mock.stop = get_mock_async()

            pipeline._installed_apps[key] = app_mock

        await pipeline.initialize()

        for app in pipeline.apps.values():
            assert app.initialize.called
            assert app.initialize.call_count == 1

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_start_starts_apps_in_reverse_order(
        self, unsync_event_loop, three_level_app_chain
    ):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        mock_parent = MagicMock()

        # Mock all of the apps that have been configured for this pipeline.
        for key, app in pipeline._installed_apps.items():
            app_mock = MagicMock(app.__class__)
            app_mock.name = app.name
            app_mock.initialize = get_mock_async()
            app_mock.start = get_mock_async()

            setattr(mock_parent, app.name, app_mock)

            pipeline._installed_apps[key] = app_mock

        pipeline.stopped_event.set()  # Stop pipeline immediately after start has been executed
        await pipeline.start()

        for app in pipeline.apps.values():
            assert app.start.called
            assert app.start.call_count == 1

        call_order = [
            call[0].rstrip(".start")
            for call in mock_parent.method_calls[-len(pipeline.apps) :]
        ]
        assert call_order == list(reversed(pipeline.apps.keys()))

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_start_raises_exception_on_initialize_timeout(
        self, unsync_event_loop, three_level_app_chain
    ):
        with pytest.raises(futures.TimeoutError):
            pipeline = BasePipeline(installed_apps=three_level_app_chain)

            settings.INIT_TIMEOUT = 0.1
            # Mock all of the apps that have been configured for this pipeline.
            for key, app in pipeline._installed_apps.items():
                app_mock = MagicMock(app.__class__)
                app_mock.initialize = get_slow_mock_async(settings.INIT_TIMEOUT + 0.1)
                app_mock.stop = get_mock_async()

                pipeline._installed_apps[key] = app_mock

            await pipeline.start()

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_start_raises_exception_on_start_timeout(
        self, unsync_event_loop, three_level_app_chain
    ):
        with pytest.raises(futures.TimeoutError):
            pipeline = BasePipeline(installed_apps=three_level_app_chain)

            settings.STARTUP_TIMEOUT = 0.1
            # Mock all of the apps that have been configured for this pipeline.
            for key, app in pipeline._installed_apps.items():
                app_mock = MagicMock(app.__class__)
                app_mock.initialize = get_mock_async()
                app_mock.start = get_slow_mock_async(settings.STARTUP_TIMEOUT + 0.1)
                app_mock.stop = get_mock_async()

                pipeline._installed_apps[key] = app_mock

            await pipeline.start()

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_stop_stops_apps_in_top_down_order(
        self, unsync_event_loop, three_level_app_chain
    ):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        mock_parent = MagicMock()

        # Mock all of the apps that have been configured for this pipeline.
        for key, app in pipeline._installed_apps.items():
            app_mock = MagicMock(app.__class__)
            app_mock.name = app.name
            app_mock.stop = get_mock_async()

            setattr(mock_parent, app.name, app_mock)

            pipeline._installed_apps[key] = app_mock

        await pipeline.stop()

        for app in pipeline.apps.values():
            assert app.stop.called
            assert app.stop.call_count == 1

        call_order = [
            call[0].rstrip("stop").rstrip(".")
            for call in mock_parent.method_calls[-len(pipeline.apps) :]
        ]
        assert call_order == list(pipeline.apps.keys())

    @pytest.mark.asyncio
    async def test_stop_cancels_all_tasks_on_stop_timeout(
        self, unsync_event_loop, three_level_app_chain
    ):
        with pytest.raises(futures.CancelledError):
            pipeline = BasePipeline(installed_apps=three_level_app_chain)

            settings.STOP_TIMEOUT = 0.1
            # Mock all of the apps that have been configured for this pipeline.
            for key, app in pipeline._installed_apps.items():
                app_mock = MagicMock(app.__class__)
                app_mock.stop = get_slow_mock_async(settings.STOP_TIMEOUT + 0.1)

                pipeline._installed_apps[key] = app_mock

            await pipeline.stop()

    @pytest.mark.asyncio
    async def test_stop_allows_only_one_stop_process_to_run_concurrently(
        self, unsync_event_loop, three_level_app_chain
    ):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        # Mock all of the apps that have been configured for this pipeline.
        for key, app in pipeline._installed_apps.items():
            app_mock = MagicMock(app.__class__)
            app_mock.stop = get_mock_async()

            pipeline._installed_apps[key] = app_mock

        pipeline.stop()
        pipeline.stop()
        pipeline.stop()
        await pipeline.stop()

        for app in pipeline.apps.values():
            assert app.stop.called
            assert app.stop.call_count == 1

    @pytest.mark.asyncio
    async def test_stop_no_op_if_already_stopped(
        self, unsync_event_loop, three_level_app_chain
    ):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        # Mock all of the apps that have been configured for this pipeline.
        for key, app in pipeline._installed_apps.items():
            app_mock = MagicMock(app.__class__)
            app_mock.stop = get_mock_async()

            pipeline._installed_apps[key] = app_mock

        await pipeline.stop()
        await pipeline.stop()

        for app in pipeline.apps.values():
            assert app.stop.called
            assert app.stop.call_count == 1

    @pytest.mark.asyncio
    async def test_receive(self, unsync_event_loop, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        message = await pipeline.receive(admin.TestRequestMessage("Test"))
        assert message.TestReqID == "Test r1 r2 r3"

    @pytest.mark.asyncio
    async def test_receive_stop(self, unsync_event_loop, three_level_stop_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_stop_app_chain)

        message = await pipeline.receive(admin.TestRequestMessage("Test"))
        assert message.TestReqID == "Test r1"

    @pytest.mark.asyncio
    async def test_send(self, unsync_event_loop, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        message = await pipeline.send(admin.TestRequestMessage("Test"))
        assert message.TestReqID == "Test s3 s2 s1"

    @pytest.mark.asyncio
    async def test_send_stop(self, unsync_event_loop, three_level_stop_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_stop_app_chain)

        message = await pipeline.send(admin.TestRequestMessage("Test"))
        assert message.TestReqID == "Test s3"
