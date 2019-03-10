from typing import Optional, Any


class JsonResultResponse(dict):
    """
    Provides a predictable JSON response structure that also indicates whether the call was successful or not, and
    contains a user-friendly message that can be displayed on-screen.
    """

    def __init__(
        self, success: bool, message: str, data: Optional[Any] = None
    ):
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
