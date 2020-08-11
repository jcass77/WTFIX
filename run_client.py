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

import argparse
import asyncio
import logging
import os
import sys
import signal

from wtfix.conf import settings
from wtfix.core.exceptions import ImproperlyConfigured
from wtfix.pipeline import BasePipeline
from wtfix.protocol.contextlib import connection_manager

logger = settings.logger

parser = argparse.ArgumentParser(description="Start a FIX connection")

parser.add_argument(
    "--connection",
    default="default",
    help="the configuration settings to use for the connection (default: 'default')",
)

parser.add_argument(
    "-new_session",
    action="store_true",
    help=f"reset sequence numbers and start a new session",
)

_shutting_down = asyncio.Event()


async def graceful_shutdown(pipeline, sig_name=None):
    if _shutting_down.is_set():
        # Only try to shut down once
        logger.warning(f"Shutdown already in progress! Ignoring signal '{sig_name}'.")
        return

    _shutting_down.set()

    if sig_name is not None:
        logger.info(f"Received signal {sig_name}! Initiating graceful shutdown...")
    else:
        logger.info(f"Initiating graceful shutdown...")

    await pipeline.stop()


async def main():
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    args = parser.parse_args()
    exit_code = os.EX_UNAVAILABLE

    with connection_manager(args.connection) as conn:
        fix_pipeline = BasePipeline(
            connection_name=conn.name, new_session=args.new_session
        )

        try:
            # Graceful shutdown on termination signals.
            # See: https://docs.python.org/3.7/library/asyncio-eventloop.html#set-signal-handlers-for-sigint-and-sigterm
            loop = asyncio.get_running_loop()
            for sig_name in {"SIGINT", "SIGTERM"}:
                loop.add_signal_handler(
                    getattr(signal, sig_name),
                    lambda: asyncio.create_task(
                        graceful_shutdown(fix_pipeline, sig_name=sig_name)
                    ),
                )

            await fix_pipeline.start()

        except ImproperlyConfigured as e:
            logger.error(e)
            # User needs to fix config issue before restart is attempted. Set os.EX_OK so that system process
            # monitors like Supervisor do not attempt a restart immediately.
            exit_code = os.EX_OK

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt! Initiating shutdown...")
            exit_code = os.EX_OK

        except asyncio.exceptions.TimeoutError as e:
            logger.error(e)

        except asyncio.exceptions.CancelledError as e:
            logger.error(f"Cancelled: connection terminated abnormally! ({e})")

        except Exception as e:
            logger.exception(e)

        finally:
            await graceful_shutdown(fix_pipeline)

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

            sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
