import logging
import importlib
from collections import OrderedDict

from wtfix.conf import settings

logger = logging.getLogger(__name__)


class BaseHandler:
    """
    Propagates inbound messages up and down the layers of configured message handling app instances.
    """
    _installed_apps = OrderedDict()

    def load_apps(self, installed_apps=None):
        """
        Loads the list of apps to be used for processing messages.
        :param installed_apps: The list of class paths for the installed apps.
        """
        if installed_apps is None:
            installed_apps = settings.INSTALLED_APPS

        for app in installed_apps:
            last_dot = app.rfind(".")
            module = importlib.import_module(app[:last_dot])

            class_ = getattr(module, app[last_dot+1:])
            instance = class_()

            self._installed_apps[instance.name] = instance

    def _process_message(self, message, inbound=True):
        """
        Process a message by passing it on to the various app handlers.
        :param message: The GenericMessage instance to process
        :param inbound: True if this is an inbound message, False otherwise.

        :return: The processed message or None if processing was halted somewhere in the app stack.
        """
        app_chain = self._installed_apps.values()
        if inbound is False:
            # Process top-down.
            app_chain = reversed(app_chain)

        chain_iter = iter(app_chain)
        try:
            while message is not None:
                app = next(chain_iter)
                if inbound is True:
                    message = app.on_receive(message)
                else:
                    message = app.on_send(message)

            logger.debug(f"Processing of message {message} stopped at '{app.name}'.")
        except StopIteration:
            # Message propagated all the way to the top!
            logger.debug(f"Message {message} processed successfully!")

        return message

    def receive(self, message):
        """Receives a new message to be processed"""
        return self._process_message(message)

    def send(self, message):
        """Processes a new message to be sent"""
        return self._process_message(message, inbound=False)
