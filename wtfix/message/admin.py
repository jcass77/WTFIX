from wtfix.conf import settings
from wtfix.message.message import OptimizedGenericMessage
from wtfix.protocol.common import MsgType, Tag


class LogonMessage(OptimizedGenericMessage):
    """Generic Logon message"""

    def __init__(self, username, password, encryption_method=0, heartbeat_int=None):

        if heartbeat_int is None:
            heartbeat_int = settings.HEARTBEAT_INTERVAL

        super().__init__(
            (Tag.MsgType, MsgType.Logon),
            (Tag.EncryptMethod, encryption_method),
            (Tag.HeartBtInt, heartbeat_int),
            (Tag.Username, username),
            (Tag.Password, password),
        )


class LogoutMessage(OptimizedGenericMessage):
    """Generic Logout message"""

    def __init__(self):
        super().__init__(
            (Tag.MsgType, MsgType.Logout),
        )


class HeartbeatMessage(OptimizedGenericMessage):
    """Generic Heartbeat message"""

    def __init__(self, test_request_id):
        super().__init__(
            (Tag.MsgType, MsgType.Heartbeat), (Tag.TestReqID, test_request_id)
        )


class TestRequestMessage(OptimizedGenericMessage):
    """Generic TestRequest message"""

    # Let pytest know that it should not try to collect this class as a test case just because it is named Test*
    __test__ = False

    def __init__(self, test_request_id):
        super().__init__(
            (Tag.MsgType, MsgType.TestRequest), (Tag.TestReqID, test_request_id)
        )


class ResendRequestMessage(OptimizedGenericMessage):
    """Generic ResendRequest message"""

    def __init__(self, from_seq_num, to_seq_num=0):
        super().__init__(
            (Tag.MsgType, MsgType.ResendRequest),
            (Tag.BeginSeqNo, from_seq_num),
            (Tag.EndSeqNo, to_seq_num),
        )


class SequenceResetMessage(OptimizedGenericMessage):
    """Generic SequenceReset message"""

    def __init__(self, next_seq_num, new_seq_num):
        super().__init__(
            (Tag.MsgType, MsgType.SequenceReset),
            (Tag.MsgSeqNum, next_seq_num),
            (Tag.PossDupFlag, "Y"),
            (Tag.NewSeqNo, new_seq_num)
        )
