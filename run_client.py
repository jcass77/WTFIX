import logging

from wtfix.conf import logger
from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    logger.info("Initiating new FIX session...")
    handler = BasePipeline()
    logger.info("Ending session...")
    # apps.logout()
    logger.info("Scheduler shut down successfully!")
