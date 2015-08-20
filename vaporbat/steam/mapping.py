from steam.protobuf import steam_server, steam_base
from steamd import EMsg
import steamd


PROTO_MAPPING = {
    EMsg.Multi: steam_base.CMsgMulti,
    EMsg.ClientCMList: steam_server.CMsgClientCMList,
    EMsg.ClientLogOnResponse: steam_server.CMsgClientLogonResponse,
    EMsg.ClientNewLoginKey: steam_server.CMsgClientNewLoginKey,
    EMsg.ClientUpdateMachineAuth: steam_server.CMsgClientUpdateMachineAuth,
    EMsg.ClientFriendsList: steam_server.CMsgClientFriendsList,
    EMsg.ClientEmailAddrInfo: steam_server.CMsgClientEmailAddrInfo,
    EMsg.ClientAccountInfo: steam_server.CMsgClientAccountInfo,
    EMsg.ClientLicenseList: steam_server.CMsgClientLicenseList,
    EMsg.ClientGameConnectTokens: steam_server.CMsgClientGameConnectTokens,
    EMsg.ClientFromGC: steam_server.CMsgGCClient,
    EMsg.EconTrading_InitiateTradeProposed: steam_server.CMsgTrading_InitiateTradeRequest,
    EMsg.EconTrading_InitiateTradeResult: steam_server.CMsgTrading_InitiateTradeResponse,
    EMsg.EconTrading_StartSession: steam_server.CMsgTrading_StartSession,
    EMsg.ClientPersonaState:steam_server.CMsgClientPersonaState,
}
WANTS_HEADER = [EMsg.ClientUpdateMachineAuth]
EMSGS = dict(map(reversed, steamd.EMsg.constants.items()))
EEconTradeResponse = dict(map(reversed, steamd.EEconTradeResponse.constants.items()))
