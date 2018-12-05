import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class BaseHandler:
    """
    Propagates inbound messages up and down the layers of configured message handling middleware instances.
    """
    _middleware = OrderedDict()

    def load_middleware(self, middleware):
        """
        Loads the list of middleware to be used for processing messages.
        :param middleware: A list of BaseMiddleware instances
        """
        for mw in middleware:
            self._middleware[mw.name] = mw

    def _process_message(self, message, inbound=True):
        """
        Process a message by passing it on to the various middleware handlers.
        :param message: The GenericMessage instance to process
        :param inbound: True if this is an inbound message, False otherwise.

        :return: The processed message or None if processing was halted somewhere in the middleware stack.
        """
        middleware = self._middleware.values()
        if inbound is False:
            # Process top-down.
            middleware = reversed(middleware)

        mw_iter = iter(middleware)
        try:
            while message is not None:
                mw = next(mw_iter)
                if inbound is True:
                    message = mw.on_receive(message)
                else:
                    message = mw.on_send(message)

            logger.debug(f"Processing of message {message} stopped at '{mw.name}'.")
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
