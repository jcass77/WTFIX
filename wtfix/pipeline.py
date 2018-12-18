import asyncio
import importlib
from asyncio import futures
from collections import OrderedDict

from unsync import unsync

from wtfix.apps.sessions import SessionApp
from wtfix.conf import logger
from wtfix.conf import settings
from wtfix.core.exceptions import (
    MessageProcessingError,
    StopMessageProcessing,
    ValidationError,
    ImproperlyConfigured,
)


class BasePipeline:
    """
    Propagates inbound messages up and down the layers of configured message handling apps instances.
    """

    INBOUND = 0
    OUTBOUND = 1

    def __init__(self, installed_apps=None):
        self._installed_apps = self._load_apps(installed_apps=installed_apps)
        logger.info(f"Created new FIX application pipeline: {list(self.apps.keys())}.")
        self._session_app = None

    @property
    def apps(self):
        return self._installed_apps

    def _load_apps(self, installed_apps=None):
        """
        Loads the list of apps to be used for processing messages.
        :param installed_apps: The list of class paths for the installed apps.
        """
        loaded_apps = OrderedDict()

        if installed_apps is None:
            installed_apps = settings.PIPELINE_APPS

        if len(installed_apps) == 0:
            raise ImproperlyConfigured(
                f"At least one application needs to be added to the pipeline using the PIPELINE_APPS setting."
            )

        for app in installed_apps:
            last_dot = app.rfind(".")
            module = importlib.import_module(app[:last_dot])

            class_ = getattr(module, app[last_dot + 1 :])
            instance = class_(self)

            loaded_apps[instance.name] = instance

            if isinstance(instance, SessionApp):
                self._session_app = instance  # Keep reference to session in order to monitor connections.

        return loaded_apps

    @unsync
    async def initialize(self):
        for app in reversed(self.apps.values()):
            logger.info(f"Initializing app '{app.name}'...")
            await app.initialize()

        logger.info("All apps initialized!")

    @unsync
    async def start(self):
        logger.info("Starting pipeline...")

        await self.initialize()
        for app in reversed(self.apps.values()):
            await app.start()

        # Block for as long as we are connected to the server.
        await self._session_app._disconnected.wait()

        logger.info("Pipeline stopped.")

    @unsync
    async def stop(self):
        logger.info("Shutting down pipeline...")
        try:
            for app in self.apps.values():
                await asyncio.wait_for(app.stop(), 5)

            logger.info("Pipeline stopped.")
        except futures.TimeoutError:
            logger.error(
                f"Timeout waiting for app {app} to stop - session terminated abnormally!"
            )

    def _prep_processing_pipeline(self, direction):
        if direction is self.INBOUND:
            return "on_receive", reversed(self.apps.values())

        if direction is self.OUTBOUND:
            return "on_send", iter(self.apps.values())

        raise ValidationError(
            f"Unknown application chain processing direction '{direction}'."
        )

    @unsync
    async def _process_message(self, message, direction):
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
            logger.exception(
                f"Error processing message {message}. Processing stopped at '{app.name}': {e}."
            )
        except StopMessageProcessing:
            logger.info(f"Processing of message {message} interrupted at '{app.name}'.")

        return message

    @unsync
    async def receive(self, message):
        """Receives a new message to be processed"""
        return await self._process_message(message, self.INBOUND)

    @unsync
    async def send(self, message):
        """Processes a new message to be sent"""
        logger.info(f" --> {message}")
        return await self._process_message(message, self.OUTBOUND)
