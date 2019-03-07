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
import logging
from asyncio import futures

from unsync import (
    unsync,
)  # Import unsync to set event loop and start ambient unsync thread

from wtfix.conf import logger
from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

parser = argparse.ArgumentParser(description="Start a FIX session")
parser.add_argument(
    "--session",
    default="default",
    help="the session to connect to (default: 'default')",
)


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    args = parser.parse_args()

    fix_pipeline = BasePipeline(session_name=args.session)
    try:
        fix_pipeline.start().result()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt! Initiating shutdown...")
        fix_pipeline.stop().result()
    except futures.CancelledError:
        logger.error("Cancelled: session terminated abnormally!")
