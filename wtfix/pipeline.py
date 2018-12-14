import asyncio
import importlib
from collections import OrderedDict

from unsync import unsync

from wtfix.conf import logger
from wtfix.conf import settings
from wtfix.core.exceptions import (
    MessageProcessingError,
    StopMessageProcessing,
    ValidationError,
)


class BasePipeline:
    """
    Propagates inbound messages up and down the layers of configured message handling apps instances.
    """

    INBOUND = 0
    OUTBOUND = 1

    def __init__(self, installed_apps=None):
        logger.info(f"Creating new FIX pipeline...")
        self._installed_apps = OrderedDict()
        self._session_app = None
        self.is_closing = asyncio.Condition()

        self.load_apps(installed_apps=installed_apps)

    @property
    def apps(self):
        return self._installed_apps

    @property
    def session_app(self):
        if self._session_app is None:
            self._session_app = next(reversed(self.apps.values()))
        return self._session_app

    @unsync
    async def initialize(self):
        for app in reversed(self.apps.values()):
            logger.info(f"Initializing app '{app.name}'...")
            await app.initialize()

        logger.info("All apps initialized!")

    def load_apps(self, installed_apps=None):
        """
        Loads the list of apps to be used for processing messages.
        :param installed_apps: The list of class paths for the installed apps.
        """
        if installed_apps is None:
            installed_apps = settings.PIPELINE_APPS

        for app in installed_apps:
            last_dot = app.rfind(".")
            module = importlib.import_module(app[:last_dot])

            class_ = getattr(module, app[last_dot + 1:])
            instance = class_(self)

            self.apps[instance.name] = instance

        logger.info(f"Pipeline apps: {list(self.apps.keys())}...")

    @unsync
    async def start(self):
        logger.info("Starting pipeline...")

        await self.initialize()
        self.session_app.connect()

        async with self.is_closing:
            await self.is_closing.wait_for(self.session_app.writer.transport.is_closing)

        logger.info("Pipeline stopped.")

    @unsync
    async def stop(self):
        logger.info("Shutting down pipeline...")
        await asyncio.wait_for(self.session_app.disconnect(), 10)

    def _prep_processing_pipeline(self, direction):
        if direction is self.INBOUND:
            return "on_receive", reversed(self.apps.values())

        if direction is self.OUTBOUND:
            return "on_send", iter(self.apps.values())

        raise ValidationError(
            f"Unknown application chain processing direction '{direction}'."
        )

    def _process_message(self, message, direction):
        """
        Process a message by passing it on to the various apps in the pipeline.
        :param message: The GenericMessage instance to process
        :param direction: 0 if this is an inbound message, 1 otherwise.

        :return: The processed message or None if processing was halted somewhere in the apps stack.
        """

        process_func, app_chain = self._prep_processing_pipeline(direction)

        try:
            for app in app_chain:
                message = getattr(app, process_func)(message)

        except MessageProcessingError as e:
            logger.exception(f"Error processing message {message}. Processing stopped at '{app.name}': {e}.")
        except StopMessageProcessing:
            logger.info(f"Processing of message {message} interrupted at '{app.name}'.")

        return message

    @unsync
    async def receive(self, message):
        """Receives a new message to be processed"""
        return self._process_message(message, self.INBOUND)

    @unsync
    async def send(self, message):
        """Processes a new message to be sent"""
        return self._process_message(message, self.OUTBOUND)

