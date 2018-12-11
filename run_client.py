import logging

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
        fix_pipeline.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt!")
        fix_pipeline.shutdown()
