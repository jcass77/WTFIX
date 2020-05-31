# This file is a part of WTFIX.
#
# Copyright (C) 2018-2020 John Cass <john.cass77@gmail.com>
#
# WTFIX is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# WTFIX is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from functools import wraps

from wtfix.core.exceptions import ValidationError, MessageProcessingError
from wtfix.message.message import FIXMessage


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

    def __str__(self):
        return self.name

    async def initialize(self, *args, **kwargs):
        """
        Initialization that needs to be performed when the app is first loaded as part of an application processing
        pipeline.

        All apps are initialized concurrently and need to complete their initialization routines within the
        timeout specified by INIT_TIMEOUT.
        """
        pass

    async def start(self, *args, **kwargs):
        """
        Override this method for any app-specific routines that should be performed when the application
        pipeline is started.

        Apps are started in the order that they were added to the pipeline and it is safe to assume that
        apps lower down in the pipeline would have been initialized and started by the time that this method
        is executed.

        App startup is subject to the STARTUP_TIMEOUT timeout.
        """
        pass

    async def stop(self, *args, **kwargs):
        """
        Override this method for any app-specific routines that should be performed when the application
        pipeline is stopped.

        Apps are stopped sequentially in the order that they were added to the pipeline and each app is subject
        to the STOP_TIMEOUT timeout.
        """
        pass

    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        """
        Override this method in order to define what to do when a message is received.

        :param message: Received message.
        :return: a processed message.
        :raises: StopMessageProcessing if message should not be processed further.
        :raises: MessageProcessingError if an error occurred during message processing.
        """
        return message

    async def on_resend(self, message: FIXMessage) -> FIXMessage:
        """
        Override this message in order to define what to do when a message was not received successfully
        by the counter party.

        :param message: Message that was not received.
        :return: a processed message.
        :raises: StopMessageProcessing if message should not be processed further.
        :raises: MessageProcessingError if an error occurred during message processing.
        """
        return message

    async def on_send(self, message: FIXMessage) -> FIXMessage:
        """
        Override this method in order to define what to do with a message needs to be transmitted.

        :param message: Message to be sent.
        :raises: StopMessageProcessing if message should not be processed further.
        :raises: MessageProcessingError if an error occurred during message processing.
        """
        return message

    async def send(self, message: FIXMessage):
        """
        Send a message.
        :param message: The message to be sent.
        """
        await self.pipeline.send(message)


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

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

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

    async def on_receive(self, message: FIXMessage) -> FIXMessage:
        """
        Calls the relevant on_<message_type> handler for this type of message, or 'on_unhandled' if no
        handler has been defined.

        :param message: The message to process
        :return: The result after processing the on_<message_type> method.
        :raises: MessageProcessingError if the handler does not return a valid FIX message.
        """
        handler = self.type_handlers.get(message.type, self.on_unhandled)
        message = await handler(message)

        if message is None:
            raise MessageProcessingError(
                f"{self.name}: message handler '{handler.__name__}' did not provide a message to propagate "
                f"further up the pipeline. Perhaps you forgot to return a message instance in "
                f"{self.__module__}.{self.__class__.__name__}.{handler.__name__}?"
            )

        return message

    async def on_unhandled(self, message: FIXMessage) -> FIXMessage:
        """
        Default message handler. Will process any messages that are not handled by a type-specific
        on_<message_type> method.

        :param message: Unhandled message.
        :return: the processed Message.
        """
        return message
