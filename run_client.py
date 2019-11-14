# This file is a part of WTFIX.
#
# Copyright (C) 2018,2019 John Cass <john.cass77@gmail.com>
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
from asyncio import futures

from wtfix.conf import settings
from wtfix.core.exceptions import ImproperlyConfigured
from wtfix.pipeline import BasePipeline

logger = settings.logger

parser = argparse.ArgumentParser(description="Start a FIX connection")

try:
    # If only one connection has been configured then we have a safe default to fall back to.
    default_connection_name = settings.default_connection_name
except ImproperlyConfigured:
    default_connection_name = None

parser.add_argument(
    "--connection",
    default=default_connection_name,
    help=f"the configuration settings to use for the connection (default: '{default_connection_name}')",
)

parser.add_argument(
    "-new_session",
    action="store_true",
    help=f"reset sequence numbers and start a new session",
)


async def graceful_shutdown(sig_name_, pipeline):
    logger.info(f"Received signal {sig_name_}! Initiating shutdown...")

    try:
        await pipeline.stop()

    except futures.CancelledError as e:
        logger.error(f"Cancelled: connection terminated abnormally! ({e})")
        sys.exit(os.EX_UNAVAILABLE)


async def main():
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    args = parser.parse_args()

    fix_pipeline = BasePipeline(
        connection_name=args.connection, new_session=args.new_session
    )

    try:
        # Graceful shutdown on termination signals.
        # See: https://docs.python.org/3.7/library/asyncio-eventloop.html#set-signal-handlers-for-sigint-and-sigterm
        loop = asyncio.get_running_loop()
        for sig_name in {"SIGINT", "SIGTERM"}:
            loop.add_signal_handler(
                getattr(signal, sig_name),
                lambda: asyncio.ensure_future(
                    graceful_shutdown(sig_name, fix_pipeline)
                ),
            )

        await fix_pipeline.start()

    except asyncio.TimeoutError as e:
        logger.error(e)
        sys.exit(os.EX_UNAVAILABLE)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt! Initiating shutdown...")
        sys.exit(os.EX_OK)

    except futures.CancelledError as e:
        logger.error(f"Cancelled: connection terminated abnormally! ({e})")
        sys.exit(os.EX_UNAVAILABLE)

    except ImproperlyConfigured as e:
        logger.error(e)
        sys.exit(os.EX_OK)  # User needs to fix config issue before restart is attempted

    except Exception as e:
        logger.exception(e)
        sys.exit(os.EX_UNAVAILABLE)

    finally:
        try:
            await fix_pipeline.stop()
        except futures.CancelledError as e:
            logger.error(f"Cancelled: connection terminated abnormally! ({e})")
            sys.exit(os.EX_UNAVAILABLE)


if __name__ == "__main__":
    asyncio.run(main())
