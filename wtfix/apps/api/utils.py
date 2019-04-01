# This file is a part of WTFIX.
#
# Copyright (C) 2018,2019 John Cass <john.cass77@gmail.com>
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

from typing import Optional, Any


class JsonResultResponse(dict):
    """
    Provides a predictable JSON response structure that also indicates whether the call was successful or not, and
    contains a user-friendly message that can be displayed on-screen.
    """

    def __init__(self, success: bool, message: str, data: Optional[Any] = None):
        """
        Given the input parameters, return a new JsonResponse.

        :param success: Whether the request was successful or not (True / False).
        :param message: A user-friendly application message that can be shown on-screen.
        :param data: The actual result of the response. Must be a serializable dictionary.
        :return: A response structure containing the above parameters.
        """

        super().__init__()

        if data is None:
            data = {}

        self["success"] = success
        self["message"] = message
        self["data"] = data
