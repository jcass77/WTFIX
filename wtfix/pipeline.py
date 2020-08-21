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

import asyncio
from collections import OrderedDict
from typing import Union, List, Tuple

from wtfix.core.klass import get_class_from_module_string
from wtfix.conf import ConnectionSettings
from wtfix.conf import settings
from wtfix.core.exceptions import (
    MessageProcessingError,
    StopMessageProcessing,
    ValidationError,
    ImproperlyConfigured,
    SessionError,
)
from wtfix.message.message import FIXMessage
from wtfix.protocol.contextlib import connection

logger = settings.logger


class BasePipeline:
    """
    Propagates inbound messages up and down the layers of configured message handling apps instances.
    """

    INBOUND_PROCESSING = 0
    OUTBOUND_PROCESSING = 1

    def __init__(self, connection_name: str, installed_apps: List = None, **kwargs):
        self.settings = ConnectionSettings(connection_name)

        self._installed_apps = self._load_apps(installed_apps=installed_apps, **kwargs)
        logger.info(
            f"Created new WTFIX application pipeline: {list(self._installed_apps.keys())}."
        )
        # An app is 'active' if it has (a) been initialized and (b) not been stopped.
        self._active_apps = OrderedDict()

        self.stop_lock = asyncio.Lock()
        self.stopping_event = asyncio.Event()
        self.stopped_event = asyncio.Event()

        self.errors = []

    @property
    def apps(self) -> OrderedDict:
        return self._installed_apps

    def _load_apps(self, installed_apps: List = None, **kwargs) -> OrderedDict:
        """
        Loads the list of apps to be used for processing messages.

        :param installed_apps: The list of class paths for the installed apps.
        :returns: An ordered dictionary containing all of the apps that have been loaded.
        """
        loaded_apps = OrderedDict()

        if installed_apps is None:
            installed_apps = self.settings.PIPELINE_APPS

        if len(installed_apps) == 0:
            raise ImproperlyConfigured(
                f"At least one application needs to be added to the pipeline by using the PIPELINE_APPS setting."
            )

        for app in installed_apps:
            class_ = get_class_from_module_string(app)
            instance = class_(self, **kwargs)

            loaded_apps[instance.name] = instance

        return loaded_apps

    async def initialize(self):
        """
        Initialize all applications that have been configured for this pipeline.

        All apps are initialized concurrently.
        """
        logger.info(f"Initializing applications...")

        init_calls = (app.initialize for app in self.apps.values())
        await asyncio.gather(*(call() for call in init_calls))

        for name, app in self.apps.items():
            self._active_apps[name] = app

        logger.info("All apps initialized!")

    async def start(self):
        """
        Starts each of the applications in turn.

        :raises: TimeoutError if either INIT_TIMEOUT or STARTUP_TIMEOUT is exceeded.
        """
        logger.info("Starting pipeline...")

        try:
            # Initialize all apps first
            await asyncio.wait_for(self.initialize(), settings.INIT_TIMEOUT)

        except asyncio.exceptions.TimeoutError as e:
            logger.error(f"Timeout waiting for apps to initialize!")
            raise e

        for app in reversed(self.apps.values()):
            if self.stopping_event.is_set():
                # Abort startup
                logger.info(f"Pipeline shutting down. Aborting startup of '{app}'...")
                break

            logger.info(f"Starting app '{app}'...")

            try:
                await asyncio.wait_for(app.start(), settings.STARTUP_TIMEOUT)
            except asyncio.exceptions.TimeoutError as e:
                logger.error(f"Timeout waiting for app '{app}' to start!")
                raise e

        logger.info("All apps in pipeline have been started!")

        # Block until the pipeline has been stopped again.
        await self.stopped_event.wait()

        if self.errors:
            # Re-raise exceptions so that calling process can set proper exit codes.
            raise SessionError(f"Pipeline terminated abnormally due to: {self.errors}")

    async def stop(self, error: Exception = None):
        """
        Tries to shut down the pipeline in an orderly fashion.

        :param: error: The exception that triggered the pipeline stop or None if the shutdown occurred normally.
        :raises: TimeoutError if STOP_TIMEOUT is exceeded.
        """
        if self.stop_lock.locked():
            # Stop already in progress - skip
            return

        async with self.stop_lock:  # Ensure that more than one app does not attempt to initiate a shutdown at once
            if error:
                logger.exception(
                    f"Pipeline shutting down due to exception: {error}.", exc_info=error
                )
                self.errors.append(error)

            if self.stopping_event.is_set() or self.stopped_event.is_set():
                # Pipeline has already been stopped or is in the process of shutting down - nothing more to do.
                return

            self.stopping_event.set()  # Mark start of shutdown event.

            logger.info("Shutting down pipeline...")
            for name, app in self.apps.items():
                # Stop apps in the reverse order that they were initialized.
                logger.info(f"Stopping app '{app}'...")
                try:
                    await asyncio.wait_for(app.stop(), settings.STOP_TIMEOUT)
                    del self._active_apps[name]

                except asyncio.exceptions.TimeoutError:
                    logger.error(f"Timeout waiting for app '{app}' to stop!")
                    continue  # Continue trying to stop next app.

                except Exception:
                    # Don't allow misbehaving apps to interrupt pipeline shutdown.
                    logger.exception(f"Error trying to stop app '{app}'.")
                    continue

            self.stopped_event.set()
            logger.info("Pipeline stopped.")

    def _setup_message_handling(self, direction: int) -> Tuple[str, iter]:
        if direction is self.INBOUND_PROCESSING:
            return "on_receive", reversed(self._active_apps.values())

        if direction is self.OUTBOUND_PROCESSING:
            return "on_send", iter(self._active_apps.values())

        raise ValidationError(
            f"Unknown application chain processing direction '{direction}'."
        )

    async def _process_message(
        self, message: Union[FIXMessage, bytes], direction: int
    ) -> Union[FIXMessage, bytes]:
        """
        Process a message by passing it on to the various apps in the pipeline.

        :param message: The GenericMessage instance to process
        :param direction: 0 if this is an inbound message, 1 otherwise.

        :return: The processed message.
        """

        method_name, app_chain = self._setup_message_handling(direction)

        try:
            for app in app_chain:
                # Call the relevant 'on_send' or 'on_receive' method for each application
                message = await getattr(app, method_name)(message)

        except MessageProcessingError as e:
            logger.exception(
                f"Message processing error at '{app.name}': {e} ({message})."
            )
        except StopMessageProcessing as e:
            logger.info(
                f"Processing of message interrupted at '{app.name}': {e} ({message})."
            )

        except ImproperlyConfigured as e:
            # Raise configuration errors up to 'run_client'.
            raise e

        except Exception as e:
            if (
                isinstance(e, ConnectionError)
                and hasattr(message, "type")
                and message.type == connection.protocol.MsgType.Logout
                and self.stopping_event.is_set()
            ):
                # Mute connection errors that occur while we are trying to shut down / log out - connection issues
                # are probably what triggered the shutdown in the first place. And, if we are wrong and our logout
                # message gets lost, then the worst that will happen is that the server will terminate our connection
                # when it does not receive any more responses to heartbeat requests.
                logger.warning(
                    f"Ignoring connection error during shutdown / logout: {e}"
                )
            else:
                # Unhandled exception - abort!
                asyncio.create_task(self.stop(e))

        return message

    async def receive(self, message: bytes) -> Union[FIXMessage, bytes]:
        """Receives a new message to be processed"""
        if self.errors:
            logger.warning(
                f"Pipeline errors have occurred, ignoring received message: {message}"
            )
            return message

        return await self._process_message(message, BasePipeline.INBOUND_PROCESSING)

    async def send(self, message: FIXMessage) -> Union[FIXMessage, bytes]:
        """Processes a new message to be sent"""
        if self.errors:
            logger.warning(
                f"Pipeline errors have occurred, ignoring send message: {message}"
            )
            return message

        return await self._process_message(message, BasePipeline.OUTBOUND_PROCESSING)
