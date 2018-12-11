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
        self._installed_apps = OrderedDict()

        self.load_apps(installed_apps=installed_apps)
        self.initialize()

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

            self._installed_apps[instance.name] = instance
        logger.info(f"Loaded apps: {list(self._installed_apps.keys())}...")

    def _prep_processing_pipeline(self, direction):
        if direction is self.INBOUND:
            return "on_receive", reversed(self._installed_apps.values())

        if direction is self.OUTBOUND:
            return "on_send", iter(self._installed_apps.values())

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
    def receive(self, message):
        """Receives a new message to be processed"""
        return self._process_message(message, self.INBOUND)

    @unsync
    def send(self, message):
        """Processes a new message to be sent"""
        return self._process_message(message, self.OUTBOUND)

    def initialize(self):
        logger.info("Initializing apps...")
        for app in reversed(self._installed_apps.values()):
            app.initialize()
        logger.info("All apps initialized!")
