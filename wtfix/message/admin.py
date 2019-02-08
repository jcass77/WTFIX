from wtfix.message.message import OptimizedGenericMessage
from wtfix.protocol.common import MsgType, Tag


class Heartbeat(OptimizedGenericMessage):
    """Generic Heartbeat message"""

    def __init__(self, test_request_id):
        super().__init__(
            (Tag.MsgType, MsgType.Heartbeat), (Tag.TestReqID, test_request_id)
        )


class TestRequest(OptimizedGenericMessage):
    """Generic TestRequest message"""

    # Let pytest know that it should not try to collect this class as a test case just because it is named Test*
    __test__ = False

    def __init__(self, test_request_id):
        super().__init__(
            (Tag.MsgType, MsgType.TestRequest), (Tag.TestReqID, test_request_id)
        )
