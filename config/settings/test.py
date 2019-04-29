from wtfix.protocol.common import Tag
from .local import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True

# SESSION
# ------------------------------------------------------------------------------
CONNECTIONS["default"]["HOST"] = "TEST_HOST"
CONNECTIONS["default"]["PORT"] = "TEST_PORT"

CONNECTIONS["default"]["SENDER"] = "SENDER_ID"
CONNECTIONS["default"]["TARGET"] = "TARGET_ID"

CONNECTIONS["default"]["USERNAME"] = "TEST_USER"
CONNECTIONS["default"]["PASSWORD"] = "TEST_PASSWORD"

# REPEATING GROUPS
CONNECTIONS["default"]["GROUP_TEMPLATES"] = {
    # Routing IDs
    Tag.NoRoutingIDs: [Tag.RoutingType, Tag.RoutingID]
}
