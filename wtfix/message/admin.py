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

from wtfix.conf import settings
from wtfix.message.message import OptimizedGenericMessage
from wtfix.protocol.common import MsgType, Tag


class LogonMessage(OptimizedGenericMessage):
    """Generic Logon message"""

    def __init__(self, username, password, encryption_method=0, heartbeat_int=None):

        if heartbeat_int is None:
            heartbeat_int = settings.default_connection.HEARTBEAT_INT

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
        super().__init__((Tag.MsgType, MsgType.Logout))


class HeartbeatMessage(OptimizedGenericMessage):
    """Generic Heartbeat message"""

    def __init__(self, test_request_id=None):
        super().__init__((Tag.MsgType, MsgType.Heartbeat))
        if test_request_id is not None:
            self.TestReqID = test_request_id


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
            (Tag.NewSeqNo, new_seq_num),
        )
