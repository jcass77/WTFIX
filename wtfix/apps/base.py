import logging

from wtfix.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BaseApp:
    """
    Performs some sort of processing on inbound and outbound messages.
    """

    name = None

    def __init__(self, handler, *args, **kwargs):
        """
        :param name: A unique name that can be used to retrieve this apps from the base
        message handler.
        :raises: ValidationError if no name has been specified for this apps.
        """
        if self.name is None:
            raise ValidationError(
                f"No name specified for apps '{self.__class__.__name__}'."
            )

        self.handler = handler

    def on_receive(self, message):
        """
        Override this method in order to define what to do when a message is received.

        :param message: Received message.
        :return: a processed message.
        :raises: StopMessageProcessing if message should not be processed further.
        :raises: MessageProcessingError if an error occurred during message processing.
        """
        return message

    def on_resend(self, message):
        """
        Override this message in order to define what to do when a message was not received successfully
        by the counter party.

        :param message: Message that was not received.
        :return: a processed message.
        :raises: StopMessageProcessing if message should not be processed further.
        :raises: MessageProcessingError if an error occurred during message processing.
        """
        return message

    def on_send(self, message):
        """
        Override this method in order to define what to do with a message needs to be transmitted.

        :param message: Message to be sent.
        :raises: StopMessageProcessing if message should not be processed further.
        :raises: MessageProcessingError if an error occurred during message processing.
        """
        return message

    def send(self, message):
        """
        Send a message.
        :param message: The message to be sent.
        """
        self.handler.send(message)

    def initialize(self):
        """
        Initialization that needs to be performed before this apps can start processing messages.
        """
        pass
