from wtfix.core.klass import get_class_from_module_string
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
# Get protocol Type so that we can configure repeating groups  on a per-protocol basis
protocol = get_class_from_module_string(CONNECTIONS["default"]["PROTOCOL"])
CONNECTIONS["default"]["GROUP_TEMPLATES"] = {
    # Routing IDs
    protocol.Tag.NoRoutingIDs: {"*": [protocol.Tag.RoutingType, protocol.Tag.RoutingID]}
}
