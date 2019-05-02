"""
Base settings to build other settings files upon.
"""
import logging
import os
from distutils.util import strtobool
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parents[3]  # (wtfix/config/settings/base.py - 3 = wtfix/)

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = strtobool(os.getenv("DEBUG", "False"))
LOGGING_LEVEL = logging.INFO

# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "Africa/Johannesburg"
USE_TZ = True

# REDIS
# ------------------------------------------------------------------------------
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")

# MESSAGE STORE
# ------------------------------------------------------------------------------
MESSAGE_STORE = os.getenv("MESSAGE_STORE", "wtfix.apps.store.MemoryStore")

# CONNECTIONS
# ------------------------------------------------------------------------------
CONNECTIONS = {
    "default": {
        "HEARTBEAT_INT": 30,
        "HOST": os.getenv("HOST"),
        "PORT": os.getenv("PORT"),
        "SENDER": os.getenv("SENDER"),
        "TARGET": os.getenv("TARGET"),
        "USERNAME": os.getenv("USERNAME", os.getenv("SENDER")),
        "PASSWORD": os.getenv("PASSWORD"),
        # APPS
        "PIPELINE_APPS": [
            "wtfix.apps.api.rest.RESTfulServiceApp",
            "wtfix.apps.brokers.RedisPubSubApp",
            "wtfix.apps.admin.HeartbeatApp",
            "wtfix.apps.admin.AuthenticationApp",
            "wtfix.apps.admin.SeqNumManagerApp",
            "wtfix.apps.store.MessageStoreApp",
            "wtfix.apps.utils.InboundLoggingApp",
            "wtfix.apps.parsers.RawMessageParserApp",
            "wtfix.apps.utils.OutboundLoggingApp",
            "wtfix.apps.wire.WireCommsApp",
            "wtfix.apps.sessions.ClientSessionApp",
        ],
        # REPEATING GROUPS
        "GROUP_TEMPLATES": {},
    }
}
