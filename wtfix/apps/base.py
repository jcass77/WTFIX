from functools import wraps

from wtfix.conf import logger
from wtfix.core.exceptions import ValidationError


class BaseApp:
    """
    Base class for applications that perform some sort of processing on inbound and outbound messages.
    """

    name = None

    def __init__(self, pipeline, *args, **kwargs):
        """
        :param pipeline: The pipeline that this app will be added to.
        :raises: ValidationError if no name has been specified for this apps.
        """
        if self.name is None:
            raise ValidationError(
                f"No name specified for apps '{self.__class__.__name__}'."
            )

        self.pipeline = pipeline

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
        self.pipeline.send(message)

    def initialize(self, *args, **kwargs):
        """
        Initialization that needs to be performed before this apps can start processing messages.
        """
        pass


def on(message_type):
    """
    Decorator to be used with a MessageTypeHandlerApp to handle messages of a specific type.

    Compares tag 35 of the message with message_type.

    Sample usage:
        @on(MsgType.ExecutionReport)
        def on_execution_report(self, message):
            # Do something with the execution report
            return message # Pass the message on for further processing.

    :param message_type: The type of message to be processed.
    :return: a decorator that can be used with a MessageTypeHandlerApp method.
    """
    @wraps(message_type)
    def wrapper(f):
        f.on_type = message_type
        return f

    return wrapper


class MessageTypeHandlerApp(BaseApp):
    """
    Allows for the definition of 'on_' method handlers to process specific types of messages as they are received.
    """

    name = "type_filter"

    def __init__(self, name, *args, **kwargs):
        super().__init__(name)

        self.type_handlers = {}

        # Find all callable methods for this app
        method_list = [
            getattr(self, func)
            for func in dir(self)
            if callable(getattr(self, func)) and not func.startswith("__")
        ]

        # See if an 'on_' handler is defined for each method
        for method in method_list:
            try:
                self.type_handlers[getattr(method, "on_type")] = method
            except AttributeError:
                # Method is not a message type pipeline, ignore
                pass

    def on_receive(self, message):
        """
        Calls the relevant on_<message_type> handler for this type of message, or 'on_unhandled' if no
        handler has been defined.

        :param message: The message to process
        :return: The result after processing the on_<message_type> method.
        """
        return self.type_handlers.get(message.type, self.on_unhandled)(message)

    def on_unhandled(self, message):
        """
        Default message handler. Will process any messages that are not handled by a type-specific
        on_<message_type> method.

        :param message: Unhandled message.
        :return: the processed Message.
        """
        return message
