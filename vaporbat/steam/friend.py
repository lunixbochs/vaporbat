from steamid import SteamID
from steamd import EChatEntryType, EMsg, proto_mask
from protobuf.steammessages_clientserver_pb2 import CMsgClientFriendMsg

class Friend:
    def __init__(self, client, steam_id):
        if not isinstance(steam_id, SteamID):
            steam_id = SteamID(steam_id)

        self.client = client
        self.steam_id = steam_id
        self.steam_64 = long(steam_id)
        # these get updated when steam provides us the info
        self.name = '[unknown]'
        self.relationship = 0

    def chat(self, msg):
        typ = EChatEntryType.ChatMsg
        if msg.startswith('/me '):
            msg = msg[4:]
            typ = EChatEntryType.Emote

        proto = CMsgClientFriendMsg()
        proto.steamid = self.steam_64
        proto.chat_entry_type = typ
        proto.message = msg
        self.client.send(EMsg.ClientFriendMsg|proto_mask, proto)

    def accept_trade(self, trade):
        raise NotImplemented

    def reject_trade(self, trade):
        raise NotImplemented

    def request_trade(self):
        msg = steam_server.CMsgTrading_InitiateTradeRequest()
        msg.other_steamid = self.steam_64
        self.client.send(EMsg.EconTrading_InitiateTradeRequest|proto_mask, msg)

    def cancel_trade(self):
        raise NotImplemented

    def __repr__(self):
        return '<Friend %s : %s>' % (self.name, self.steam_id)
