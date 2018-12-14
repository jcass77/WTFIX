import logging

from unsync import unsync

from wtfix.conf import logger
from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

# if __name__ == "__main__":


@unsync
async def main(*args, **kwargs):
    logging.basicConfig(
        level=settings.LOGGING_LEVEL,
        format="%(asctime)s - %(threadName)s - %(module)s - %(levelname)s - %(message)s",
    )

    fix_pipeline = BasePipeline()
    try:
        await fix_pipeline.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt!")
        fix_pipeline.shutdown()

main().result()
