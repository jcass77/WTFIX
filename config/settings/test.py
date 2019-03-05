from wtfix.protocol.common import Tag
from .local import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True

# SESSION
# ------------------------------------------------------------------------------
HOST = "TEST_HOST"
PORT = "TEST_PORT"

SENDER_COMP_ID = "SENDER_ID"
TARGET_COMP_ID = "TARGET_ID"

USERNAME = "TEST_USER"
PASSWORD = "TEST_PASSWORD"

# REPEATING GROUPS
# ------------------------------------------------------------------------------
GROUP_TEMPLATES = {
    # Routing IDs
    Tag.NoRoutingIDs: [Tag.RoutingType, Tag.RoutingID]
}
