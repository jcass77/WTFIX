import logging

from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

logger = logging.getLogger(__name__)

LOGGING_LEVEL = logging.INFO

if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Initiating new FIX session...")
    handler = BasePipeline()
    logger.info("Ending session...")
    # apps.logout()
    logger.info("Scheduler shut down successfully!")
