import pytest

from wtfix.conf import settings
from wtfix.core.exceptions import ValidationError, ImproperlyConfigured
from wtfix.pipeline import BasePipeline


class TestBasePipeline:
    def test_load_apps(self, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        assert len(pipeline.apps) == 3

    def test_load_apps_falls_back_to_settings(self):
        pipeline = BasePipeline()
        assert len(pipeline.apps) == len(settings.PIPELINE_APPS)
        assert all(
            f"{app.__class__.__module__}.{app.__class__.__name__}"
            in settings.PIPELINE_APPS
            for app in pipeline.apps.values()
        )

    def test_load_apps_raises_exception_if_no_apps_installed(self):
        with pytest.raises(ImproperlyConfigured):
            settings.PIPELINE_APPS = []
            BasePipeline()

    def test_prep_processing_pipeline_inbound(self, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        func, app_chain = pipeline._prep_processing_pipeline(
            pipeline.INBOUND_PROCESSING
        )
        assert func == "on_receive"
        assert next(app_chain).name == "below"
        assert next(app_chain).name == "middle"
        assert next(app_chain).name == "top"

    def test_prep_processing_pipeline_outbound(self, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)
        func, app_chain = pipeline._prep_processing_pipeline(
            pipeline.OUTBOUND_PROCESSING
        )

        assert func == "on_send"
        assert next(app_chain).name == "top"
        assert next(app_chain).name == "middle"
        assert next(app_chain).name == "below"

    def test_prep_processing_pipeline_direction_unknown(self, three_level_app_chain):
        with pytest.raises(ValidationError):
            pipeline = BasePipeline(installed_apps=three_level_app_chain)
            pipeline._prep_processing_pipeline("inbound")

    @pytest.mark.asyncio
    async def test_receive(self, unsync_event_loop, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        assert await pipeline.receive("Test") == "Test r1 r2 r3"

    @pytest.mark.asyncio
    async def test_receive_stop(self, unsync_event_loop, three_level_stop_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_stop_app_chain)

        assert await pipeline.receive("Test") == "Test r1"

    @pytest.mark.asyncio
    async def test_send(self, unsync_event_loop, three_level_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_app_chain)

        assert await pipeline.send("Test") == "Test s3 s2 s1"

    @pytest.mark.asyncio
    async def test_send_stop(self, unsync_event_loop, three_level_stop_app_chain):
        pipeline = BasePipeline(installed_apps=three_level_stop_app_chain)

        assert await pipeline.send("Test") == "Test s3"
