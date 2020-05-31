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


async def graceful_shutdown(pipeline, sig_name=None):
    if sig_name is not None:
        logger.info(f"Received signal {sig_name}! Initiating graceful shutdown...")
    else:
        logger.info(f"Initiating graceful shutdown...")

    try:
        await pipeline.stop()

    except asyncio.exceptions.CancelledError as e:
        logger.error(f"Cancelled: connection terminated abnormally! ({e})")
        sys.exit(os.EX_UNAVAILABLE)


async def main():
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    args = parser.parse_args()

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
                    lambda: asyncio.ensure_future(
                        graceful_shutdown(fix_pipeline, sig_name=sig_name)
                    ),
                )

            await fix_pipeline.start()

        except ImproperlyConfigured as e:
            logger.error(e)
            # User needs to fix config issue before restart is attempted. Set os.EX_OK so that system process
            # monitors like Supervisor do not attempt a restart immediately.
            sys.exit(os.EX_OK)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt! Initiating shutdown...")
            sys.exit(os.EX_OK)

        except asyncio.exceptions.TimeoutError as e:
            logger.error(e)
            sys.exit(os.EX_UNAVAILABLE)

        except asyncio.exceptions.CancelledError as e:
            logger.error(f"Cancelled: connection terminated abnormally! ({e})")
            sys.exit(os.EX_UNAVAILABLE)

        except Exception as e:
            logger.exception(e)
            sys.exit(os.EX_UNAVAILABLE)

        finally:
            await graceful_shutdown(fix_pipeline)


if __name__ == "__main__":
    asyncio.run(main())
