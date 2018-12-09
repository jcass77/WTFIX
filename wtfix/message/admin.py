from wtfix.message.message import GenericMessage
from wtfix.protocol.common import MsgType, Tag


class Heartbeat(GenericMessage):
    """Generic Heartbeat message"""
    def __init__(self, test_request_id):
        super().__init__((Tag.MsgType, MsgType.Heartbeat), (Tag.TestReqID, str(test_request_id)))


class TestRequest(GenericMessage):
    """Generic TestRequest message"""
    def __init__(self, test_request_id):
        super().__init__((Tag.MsgType, MsgType.TestRequest), (Tag.TestReqID, str(test_request_id)))
