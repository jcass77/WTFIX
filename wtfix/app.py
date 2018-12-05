"""
Base classes to do wtfix client applications
"""
from .protocol import common


class BaseApp:
    """
    Base class to be used to make chainable applications that can be added to the
    application 'stack'.

    Inbound messages will be passed to apps higher up in the stack once processed.

    Outbound messages will be passed down to apps lower down in the stack once processed.
    """

    def __init__(self, upper_klass=None, lower_app=None):
        self.upper_app = upper_klass(lower_app=self) if upper_klass else None
        self.lower_app = lower_app

    def _on_receive(self, message):
        message = self.on_receive(message)
        if message and self.upper_app:
            message = self.upper_app._on_receive(message)

        return message

    def on_receive(self, message):
        """
        Override to define what to do when a message is received from the other party.

        :param message: Received message.
        :returns: message to be passed to the upper app. If None processing is stopped on the current
        level in the stack.
        """
        return message

    def _on_resend(self, message):
        message = self.on_resend(message)
        if message and self.upper_app:
            message = self.upper_app._on_resend(message)

        return message

    def on_resend(self, message):
        """
        Override to define what to do when a message was not received successfully by the other party.

        :param message: Message that was not received.
        :returns: message to be passed to the upper app. If None processing is stopped on the current
        level in the stack.
        """
        return message

    def send(self, message):
        """
        Send message to the other party.

        :param message: Message to be sent.
        """
        message = self._on_send(message)
        if message and self.lower_app:
            message = self.lower_app.send(message)

        return message

    def _on_send(self, message):
        """
        Override to define what to do with a message to be sent to the other party.
        This method is called when someone calls 'send' on this app or any app higher up in the
        stack.

        Can be used to prevent a message from being sent to the other party.

        :param message: Message to be sent.
        :returns: message to be passed to the lower app. If None processing is stopped on the current
        level in the stack.
        """
        return message


def stack(*args):
    """
    Builds a stack of apps. Each parameter represents a layer in the stack. Bottom first.

    :param *args: List of pairs (class, kwargs) for each app in the stack.
    :returns: stack of applications.

    Sample usage:

        stack = app.stack(
            (
                session.SessionApp,
                dict(
                    socket_klass = sb,
                    username = user,
                    password= password,
                    we = user,
                    you="NYSE",
                    reset_seq_nums=True
                )
            ),
            (
                MyStrategyApp,
                dict(
                    param1 = value1,
                    param2 = value2
                )
            )
        )
    """

    if not args:
        raise Exception("Cannot make an empty stack.")

    if len(args) == 1:
        raise Exception(
            "Cannot make a stack consisting of a single layer. Just run the app constructor instead!"
        )

    # Generate constructor
    def build_constructor(klass, kwargs, upper_klass):
        return lambda lower_app: klass(lower_app=lower_app, upper_klass=upper_klass, **kwargs)

    app_klass = None
    for klass, kwargs in reversed(args[1:]):
        app_klass = build_constructor(klass, kwargs, app_klass)

    # Generate base and return
    base_klass, kwargs = args[0]
    return base_klass(upper_klass=app_klass, **kwargs)


def on(type_):
    """
    Decorator to be used with a ByMessageTypeApp to handle messages received of a certain type.
    Compares field 35 of the message with type_.

    Sample usage:
        @on(MsgType.ExecutionReport)
        def on_execution_report(self, message):
            # do something with the execution report
            return message # pass the message to the upper app if exists.

    :param type_: The type of message to be handled.
    :returns: decorator to be used with a ByMessageTypeApp method.
    """

    def decorator(f):
        f.on_type = type_
        return f

    return decorator


class ByMessageTypeApp(BaseApp):
    """
    Utility class to handle each type of message received separately.

    Handlers for different types of messages can be defined using the on(type_) decorator.
    """

    def __init__(self, *args, **kwargs):

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

        super(ByMessageTypeApp, self).__init__(*args, **kwargs)

    def on_receive(self, message):
        t = message.get(common.Tag.MsgType)
        return self.handlers.get(t, self.on_unhandled)(message)

    def on_unhandled(self, message):
        """
        Method called when no handler has been defined for the type of message received.

        :param message: Unhandled message.
        :return: message to be passed to the upper app. If None processing is stopped on the current
        level in the stack.
        """
        return message
