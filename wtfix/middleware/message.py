from functools import wraps

from wtfix.middleware.core import BaseMiddleware, logger


def on(message_type):
    """
    Decorator to be used with a ByMessageTypeMiddleware to handle messages of a specific type.

    Compares tag 35 of the message with message_type.

    Sample usage:
        @on(MsgType.ExecutionReport)
        def on_execution_report(self, message):
            # Do something with the execution report
            return message # Pass the message on for further processing.

    :param message_type: The type of message to be processed.
    :returna: decorator that can be used with a ByMessageTypeMiddleware method.
    """
    @wraps(message_type)
    def wrapper(f):
        f.on_type = message_type
        return f

    return wrapper


class ByMessageTypeMiddleware(BaseMiddleware):
    """
    Allows for the definition of 'on_' method handlers to process specific types of messages.
    """
    def __init__(self, name, *args, **kwargs):
        super().__init__(name)

        self.handlers = {}

        method_list = [
            getattr(self, func)
            for func in dir(self)
            if callable(getattr(self, func)) and not func.startswith("__")
        ]

        for method in method_list:
            try:
                self.handlers[getattr(method, "on_type")] = method
            except AttributeError:
                # Method is not a message type handler, ignore
                pass

    def on_receive(self, message):
        """
        Calls the relevant on_<message_type> handler for this type of message, or 'on_unhandled' if no
        handler has been defined.

        :param message: The message to process
        :return: The result after processing the on_<message_type> method.
        """
        return self.handlers.get(message.type, self.on_unhandled)(message)

    def on_unhandled(self, message):
        """
        Default message handler. Will process any messages that are not handled by a type-specific
        on_<message_type> method.

        :param message: Unhandled message.
        :return: the processed Message.
        """
        logger.debug(f"No message handler defined for message: {message}.")
        return message
