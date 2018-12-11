from .base import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True
LOGGING_LEVEL = logging.DEBUG

# SESSION
# ------------------------------------------------------------------------------
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")

SENDER_COMP_ID = os.getenv("SENDER_COMP_ID")
TARGET_COMP_ID = os.getenv("TARGET_COMP_ID")

USERNAME = os.getenv("USERNAME", SENDER_COMP_ID)
PASSWORD = os.getenv("PASSWORD")
