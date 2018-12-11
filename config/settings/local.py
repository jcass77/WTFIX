import logging

from .base import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True
LOGGING_LEVEL = logging.DEBUG

# APPS
# ------------------------------------------------------------------------------
# PIPELINE_APPS += [
#     "wtfix.wire.apps.MessageTypeHandlerApp",
# ]

# SESSION
# ------------------------------------------------------------------------------
HOST = "13.84.152.44"
PORT = 35850

SENDER_COMP_ID = "J_TRADER"
TARGET_COMP_ID = "market_data"

BEGIN_STRING = "FIX.4.4"
HEARTBEAT_TIME = 30

USERNAME = os.getenv("USERNAME", SENDER_COMP_ID)
PASSWORD = os.getenv("PASSWORD")
