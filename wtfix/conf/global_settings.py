# This file is a part of WTFIX.
#
# Copyright (C) 2018-2020 John Cass <john.cass77@gmail.com>
#
# WTFIX is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# WTFIX is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Default wtfix settings. Override these with settings in the module pointed to
by the WTFIX_SETTINGS_MODULE environment variable.
"""

####################
# CORE             #
####################
import logging

DEBUG = False
LOGGER = "wtfix"
LOGGING_LEVEL = logging.INFO

# Local time zone for this installation. All choices can be found here:
# https://en.wikipedia.org/wiki/List_of_tz_zones_by_name (although not all
# systems may support all possibilities). When USE_TZ is True, this is
# interpreted as the default user time zone.
TIME_ZONE = "America/Chicago"

# If you set this to True, wtfix will use timezone-aware datetimes.
USE_TZ = False

# The FIX standard relies on ASCII encoding. Well-behaving FIX counter parties should use the 'Encoded' range of
# fields for providing non-ASCII data, and specify the exact encoding in the MessageEncoding (347) field.

# Using cp1252 (a.k.a ANSI) here might be the most forgiving option while still ensuring that (a) the encoding is
# ASCII-compatible and (b) code points will always be encoded into a single byte. cp1252 is latin-1 (a.k.a. iso8859-1)
# superset defined by Microsoft that adds useful symbols like curly quotes and the euro symbol. Both cp1252 and
# iso8859-1 are ASCII-compatible. If you want to enforce strict adherence to the FIX protocol, then set this to 'ascii'.
ENCODING = "ascii"
ENCODING_ERRORS = (
    "strict"  # Valid options are 'strict', 'ignore', 'replace', and any other
)

BEGIN_STRING = b"FIX.4.4"

SOH = b"\x01"  # Start of header / field delimiter
SOH_INT = ord(SOH)  # Used for parsing raw byte streams.

# Timeouts for app initialization and startup
INIT_TIMEOUT = 10
STARTUP_TIMEOUT = 10
STOP_TIMEOUT = 5

# Default formatting for datetime objects.
DATETIME_FORMAT = "%Y%m%d-%H:%M:%S.%f"
