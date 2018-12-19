import logging
from asyncio import futures

from unsync import unsync  # Import unsync to set event loop and start ambient unsync thread

from wtfix.conf import logger
from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    fix_pipeline = BasePipeline()
    try:
        fix_pipeline.start().result()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt!")
        fix_pipeline.stop().result()
    except futures.CancelledError:
        logger.error("Cancelled: session terminated abnormally!")
