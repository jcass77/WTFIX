from wtfix.protocol.common import Tag
from .local import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True

# SESSION
# ------------------------------------------------------------------------------
SESSIONS["default"]["HOST"] = "TEST_HOST"
SESSIONS["default"]["PORT"] = "TEST_PORT"

SESSIONS["default"]["SENDER"] = "SENDER_ID"
SESSIONS["default"]["TARGET"] = "TARGET_ID"

SESSIONS["default"]["USERNAME"] = "TEST_USER"
SESSIONS["default"]["PASSWORD"] = "TEST_PASSWORD"

# REPEATING GROUPS
SESSIONS["default"]["GROUP_TEMPLATES"] = {
    # Routing IDs
    Tag.NoRoutingIDs: [Tag.RoutingType, Tag.RoutingID]
}
