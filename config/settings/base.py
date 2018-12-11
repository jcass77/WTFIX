"""
Base settings to build other settings files upon.
"""
import logging
import os
from distutils.util import strtobool

from dotenv import load_dotenv

load_dotenv()

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

# APPS
# ------------------------------------------------------------------------------
PIPELINE_APPS = [
    "wtfix.apps.admin.HeartbeatApp",
    "wtfix.apps.parsers.BasicMessageParserApp",
    "wtfix.apps.wire.WireCommsApp",
    "wtfix.apps.sessions.ClientSessionApp",
]
