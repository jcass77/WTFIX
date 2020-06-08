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

from wtfix.core.klass import get_class_from_module_string
from wtfix.conf import ConnectionSettings
from wtfix.conf import settings
from wtfix.core.exceptions import (
    MessageProcessingError,
    StopMessageProcessing,
    ValidationError,
    ImproperlyConfigured,
)
from wtfix.protocol.contextlib import connection

logger = settings.logger


class BasePipeline:
    """
    Propagates inbound messages up and down the layers of configured message handling apps instances.
    """

    INBOUND_PROCESSING = 0
    OUTBOUND_PROCESSING = 1

    def __init__(self, connection_name, installed_apps=None, **kwargs):
        self.settings = ConnectionSettings(connection_name)

        self._installed_apps = self._load_apps(installed_apps=installed_apps, **kwargs)
        logger.info(
            f"Created new WTFIX application pipeline: {list(self.apps.keys())}."
        )

        self.stop_lock = asyncio.Lock()
        self.stopping_event = asyncio.Event()
        self.stopped_event = asyncio.Event()

    @property
    def apps(self):
        return self._installed_apps

    def _load_apps(self, installed_apps=None, **kwargs):
        """
        Loads the list of apps to be used for processing messages.

        :param installed_apps: The list of class paths for the installed apps.
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

        init_calls = (app.initialize for app in reversed(self.apps.values()))
        await asyncio.gather(*(call() for call in init_calls))

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

    async def stop(self):
        """
        Tries to shut down the pipeline in an orderly fashion.

        :raises: TimeoutError if STOP_TIMEOUT is exceeded.
        """
        async with self.stop_lock:  # Ensure that more than one app does not attempt to initiate a shutdown at once
            if self.stopping_event.is_set() or self.stopped_event.is_set():
                # Pipeline has already been stopped or is in the process of shutting down - nothing more to do.
                return

            self.stopping_event.set()  # Mark start of shutdown event.

            logger.info("Shutting down pipeline...")
            for app in self.apps.values():
                # Stop apps in the reverse order that they were initialized.
                logger.info(f"Stopping app '{app}'...")
                try:
                    await asyncio.wait_for(app.stop(), settings.STOP_TIMEOUT)
                except asyncio.exceptions.TimeoutError:
                    logger.error(f"Timeout waiting for app '{app}' to stop!")
                    continue  # Continue trying to stop next app.

            self.stopped_event.set()
            logger.info("Pipeline stopped.")

            # Report tasks that are still running after shutdown.
            tasks = [
                task
                for task in asyncio.all_tasks()
                if task is not asyncio.current_task() and not task.cancelled()
            ]

            if tasks:
                task_output = "\n".join(str(task) for task in tasks)
                logger.warning(
                    f"There are still {len(tasks)} tasks running that have not been cancelled! Cancelling them now...\n"
                    f"{task_output}."
                )

                for task in tasks:
                    task.cancel()

    def _setup_message_handling(self, direction):
        if direction is self.INBOUND_PROCESSING:
            return "on_receive", reversed(self.apps.values())

        if direction is self.OUTBOUND_PROCESSING:
            return "on_send", iter(self.apps.values())

        raise ValidationError(
            f"Unknown application chain processing direction '{direction}'."
        )

    async def _process_message(self, message, direction):
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

                # Log exception in case it is not handled properly in the Future object.
                logger.exception(
                    f"Unhandled exception while doing {method_name}: {e} ({message})."
                )
                await asyncio.wait_for(
                    self.stop(), None
                )  # Block while we try to stop the pipeline
                raise e

        return message

    async def receive(self, message):
        """Receives a new message to be processed"""
        return await self._process_message(message, BasePipeline.INBOUND_PROCESSING)

    async def send(self, message):
        """Processes a new message to be sent"""
        return await self._process_message(message, BasePipeline.OUTBOUND_PROCESSING)
