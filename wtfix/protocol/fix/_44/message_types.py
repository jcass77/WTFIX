# This file is a part of WTFIX.
#
# Copyright (C) 2018-2021 John Cass <john.cass77@gmail.com>
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

from wtfix.protocol.message_types import _BaseMsgType


class MsgType(_BaseMsgType):
    Advertisement = "7"
    AllocationInstruction = "J"
    AllocationInstructionAck = "P"
    AllocationReport = "AS"
    AllocationReportAck = "AT"
    AssignmentReport = "AW"
    BidRequest = "k"
    BidResponse = "l"
    BusinessMessageReject = "j"
    CollateralAssignment = "AY"
    CollateralInquiry = "BB"
    CollateralInquiryAck = "BG"
    CollateralReport = "BA"
    CollateralRequest = "AX"
    CollateralResponse = "AZ"
    Confirmation = "AK"
    ConfirmationAck = "AU"
    ConfirmationRequest = "BH"
    CrossOrderCancelRequest = "u"
    CrossOrderCancelReplaceRequest = "t"
    DerivativeSecurityList = "AA"
    DerivativeSecurityListRequest = "z"
    DontKnowTrade = "Q"
    Email = "C"
    ExecutionReport = "8"
    Heartbeat = "0"
    IOI = "6"
    ListCancelRequest = "K"
    ListExecute = "L"
    ListStatus = "N"
    ListStatusRequest = "M"
    ListStrikePrice = "m"
    Logon = "A"
    Logout = "5"
    MarketDataIncrementalRefresh = "X"
    MarketDataSnapshotFullRefresh = "W"
    MarketDataRequest = "V"
    MarketDataRequestReject = "Y"
    MassQuote = "i"
    MassQuoteAcknowledgement = "b"
    MultilegOrderCancelReplace = "AC"
    NetworkCounterpartySystemStatusRequest = "BC"
    NetworkCounterpartySystemStatusResponse = "BD"
    NewOrderCross = "s"
    NewOrderList = "E"
    NewOrderMultileg = "AB"
    NewOrderSingle = "D"
    News = "B"
    OrderCancelReject = "9"
    OrderCancelRequest = "F"
    OrderCancelReplaceRequest = "G"
    OrderMassCancelReport = "r"
    OrderMassCancelRequest = "q"
    OrderMassStatusRequest = "AF"
    OrderStatusRequest = "H"
    PositionMaintenanceReport = "AM"
    PositionMaintenanceRequest = "AL"
    PositionReport = "AP"
    Quote = "S"
    QuoteCancel = "Z"
    QuoteRequest = "R"
    QuoteRequestReject = "AG"
    QuoteResponse = "AJ"
    QuoteStatusReport = "AI"
    QuoteStatusRequest = "a"
    RegistrationInstructions = "o"
    RegistrationInstructionsResponse = "p"
    Reject = "3"
    RequestForPositions = "AN"
    RequestForPositionsAck = "AO"
    ResendRequest = "2"
    RFQRequest = "AH"
    SecurityDefinition = "d"
    SecurityDefinitionRequest = "c"
    SecurityList = "y"
    SecurityListRequest = "x"
    SecurityStatus = "f"
    SecurityStatusRequest = "e"
    SecurityTypeRequest = "v"
    SecurityTypes = "w"
    SequenceReset = "4"
    SettlementInstructionRequest = "AV"
    SettlementInstructions = "T"
    TestRequest = "1"
    TradeCaptureReport = "AE"
    TradeCaptureReportAck = "AR"
    TradeCaptureReportRequest = "AD"
    TradeCaptureReportRequestAck = "AQ"
    TradingSessionStatus = "h"
    TradingSessionStatusRequest = "g"
    UserRequest = "BE"
    UserResponse = "BF"
    XMLMessage = "n"
