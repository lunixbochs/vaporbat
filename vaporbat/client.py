import Queue
import StringIO
import gzip
import hashlib
import random
import socket
import struct
import thread
import time
import traceback

import steam
from steam import Buffer, Connection, encrypt, steamd
from steam.mapping import PROTO_MAPPING, WANTS_HEADER, EMSGS
from steam.steamd import (
    EClientPersonaStateFlag, EAccountType, EUniverse, EMsg,
    EPersonaState, EResult, EFriendRelationship, proto_mask,
    MsgClientLogon, EOSType,
)
from steam.protobuf import steam_server, steam_server2, steam_base


class SteamClient:
    def __init__(self):
        self.steam_id = None
        self.session_id = None
        self.in_game = None

        self.friends = {}
        self.users = {}
        self.chat_rooms = {}
        self.connect_tokens = []
        self.login_key = None
        self.web_login = None
        self.ready = False
        self.handlers = {
            EMsg.ChannelEncryptRequest: [self.on_encrypt_request],
            EMsg.ChannelEncryptResult: [self.on_encrypt_result],
            EMsg.ClientAccountInfo: [self.on_account_info],
            EMsg.ClientCMList: [self.on_cm_list],
            EMsg.ClientEmailAddrInfo: [self.on_addrinfo],
            EMsg.ClientFriendMsgIncoming: [self.on_friend_msg],
            EMsg.ClientFriendsList: [self.on_friend_list],
            EMsg.ClientFromGC: [self.on_from_gc],
            EMsg.ClientGameConnectTokens: [self.on_connect_token],
            EMsg.ClientLogOnResponse: [self.on_login],
            EMsg.ClientNewLoginKey: [self.on_login_key],
            EMsg.ClientPersonaState: [self.on_friend_state],
            EMsg.ClientRequestValidationMailResponse: [self.on_validate_email],
            EMsg.ClientUpdateMachineAuth: [self.on_sentry],
        }

        self.persona_name = ''
        self.persona_state = EPersonaState.Offline

    def dispatch(self, emsg, hdr, data):
        handlers = self.handlers.get(emsg, [])
        for handler in handlers:
            if emsg in WANTS_HEADER:
                handler(hdr, data)
            else:
                handler(data)

    def login(self, username, password, sentry_hash=None, code=None):
        self.steam_id = steam.SteamID(0)
        self.steam_id.universe = EUniverse.Public
        self.steam_id.account_type = EAccountType.Individual
        self.session_id = None

        self.username = username
        self.password = password
        self.sentry_hash = sentry_hash
        self.code = code

        self.jobs = {}
        self.msg_queue = Queue.Queue()
        self.current_job = 0

        for i in xrange(3):
            for server in random.sample(steam.servers, len(steam.servers)):
                print 'connecting to:', server
                try:
                    self.connection = Connection(*server)
                    return
                except Exception:
                    print 'timeout'
        raise socket.error('could not connect to server')

    def set_persona(self, name=None, state=None):
        # FIXME: online state doesn't seem to work
        msg = steam_server.CMsgClientChangeStatus()
        self.persona_name = name or self.persona_name
        self.persona_state = state or self.persona_state
        msg.player_name = self.persona_name
        msg.persona_state = self.persona_state
        self.send(EMsg.ClientChangeStatus | proto_mask, msg)

    def add_friend(self, friend):
        msg = steam_server.CMsgClientAddFriend()
        msg.steamid_to_add = friend
        self.send(EMsg.ClientAddFriend | proto_mask, msg)

    def remove_friend(self, friend):
        msg = steam_server.CMsgClientRemoveFriend()
        msg.friendid = friend
        self.send(EMsg.ClientRemoveFriend | proto_mask, msg)

    def get_friend(self, steamid):
        friend = self.friends.get(steamid) or steam.Friend(self, steamid)
        self.friends[steamid] = friend
        return friend

    def play(self, app_id):
        game = steam_server.CMsgClientGamesPlayed()
        played = steam_server.CMsgClientGamesPlayed.GamePlayed()
        played.game_id = app_id
        played.game_extra_info = steam.games[app_id]
        played.process_id = 1234
        played.token = self.connect_tokens.pop(-1)
        game.games_played.extend([played])
        self.send(EMsg.ClientGamesPlayedWithDataBlob | proto_mask, game)
        self.in_game = app_id

    def pump(self):
        thread.start_new_thread(self.msg_pump, ())
        while True:
            try:
                msg = self.msg_queue.get(False)
                if msg:
                    msgs = self.on_net_msg(msg)
                    for emsg, hdr, msg in msgs:
                        yield emsg, msg
            except Queue.Empty:
                time.sleep(0.1)
            except Exception:
                print '-' * 20
                traceback.print_exc()
                print '-' * 20

    def on_net_msg(self, data):
        d = data.read('<I')
        emsg = d & ~proto_mask
        is_proto = d & proto_mask
        if not EMSGS.get(emsg):
            print 'WARNING: skipping', emsg
            return []
        # TODO: use steamd on these headers
        elif emsg in (EMsg.ChannelEncryptRequest,
                    EMsg.ChannelEncryptResult):
            # TODO: not going to actual implement a deserializer for a type that
            # only gets used for 2 message types, RIGHT HERE
            target = data.read('Q')
            source = data.read('Q')
            hdr = (target, source)
            rest = data.truncate()
            self.dispatch(emsg, hdr, rest)
            return [(emsg, hdr, rest)]
        elif is_proto:
            length = data.read('I')
            proto = data.read_len(length)
            hdr = steam_base.CMsgProtoBufHeader()
            hdr.ParseFromString(proto)
            if not self.session_id:
                self.session_id = hdr.client_sessionid
            if emsg in PROTO_MAPPING:
                msg = PROTO_MAPPING[emsg]()
                msg.ParseFromString(data.read_rest())
                if emsg == EMsg.Multi:
                    return self.on_multi(msg)
                else:
                    self.dispatch(emsg, hdr, msg)
                    return [(emsg, hdr, msg)]
            else:
                rest = data.truncate()
                self.dispatch(emsg, hdr, rest)
                return [(emsg, hdr, rest)]
        return []

    def on_encrypt_request(self, data):
        key, crypted_key, crc32 = encrypt.make_session_key()
        resp = steamd.MsgChannelEncryptResponse.dumps({})
        resp += crypted_key
        resp += struct.pack('<i', crc32)
        self.send(EMsg.ChannelEncryptResponse, resp)
        self._tmpkey = key

    def on_encrypt_result(self, data):
        result = data.read('<I')
        if result == EResult.OK:
            self.connection.key = self._tmpkey
            logon = steam_server.CMsgClientLogon()
            logon.obfustucated_private_ip = 0
            logon.account_name = self.username
            logon.password = self.password
            logon.should_remember_password = 0
            logon.protocol_version = MsgClientLogon.CurrentProtocol
            logon.client_os_type = EOSType.Win311
            if self.code:
                logon.auth_code = self.code
            # latest package version is required to get a sentry file
            logon.client_package_version = 1771
            if self.sentry_hash:
                logon.sha_sentryfile = self.sentry_hash
                logon.eresult_sentryfile = EResult.OK
            else:
                logon.eresult_sentryfile = EResult.FileNotFound
            self.send(EMsg.ClientLogon | proto_mask, logon)

    def on_multi(self, msg):
        if msg.size_unzipped:
            gf = StringIO.StringIO(msg.message_body)
            gp = gzip.GzipFile(fileobj=gf)
            payload = gp.read()
            payload = Buffer(payload)
        else:
            payload = Buffer(msg.message_body)
        msgs = []
        while payload.data:
            l = payload.read('<I')
            msgs += self.on_net_msg(Buffer(payload.read_len(l)))
            payload = payload.truncate()
        return msgs

    def on_login(self, d):
        if d.eresult == EResult.OK:
            self.steam_id.id = d.client_supplied_steamid
            thread.start_new_thread(self.heartbeat, (d.out_of_game_heartbeat_seconds,))
            self.set_persona(state=EPersonaState.Online)
        elif d.eresult == EResult.TryAnotherCM:
            self.login(self.username, self.password, self.sentry_hash, self.code)

    def on_login_key(self, key):
        self.ready = True
        resp = steam_server.CMsgClientNewLoginKeyAccepted()
        resp.unique_id = key.unique_id
        self.unique_id = str(key.unique_id)
        self.send(EMsg.ClientNewLoginKeyAccepted | proto_mask, resp)
        key = self.login_key = key.login_key
        self.web_login = steam.web.login(self.steam_id, key)

    def on_sentry(self, hdr, msg):
        sha1 = hashlib.sha1(msg.bytes).digest()
        resp = steam_server2.CMsgClientUpdateMachineAuthResponse()
        resp.filename = msg.filename
        resp.eresult = EResult.OK
        resp.filesize = len(msg.bytes)
        resp.sha_file = sha1
        resp.getlasterror = 0
        resp.offset = msg.offset
        resp.cubwrote = msg.cubtowrite
        resp.otp_type = msg.otp_type
        resp.otp_value = 0
        resp.otp_identifier = msg.otp_identifier
        self.send(EMsg.ClientUpdateMachineAuthResponse | proto_mask, resp, job=hdr.jobid_source)

    def on_account_info(self, msg):
        self.persona_name = msg.persona_name

    def on_cm_list(self, msg):
        # TODO: do something with this server list
        addrs = []
        for ip, port in zip(msg.cm_addresses, msg.cm_ports):
            addrs.append(['.'.join(map(str, reversed(struct.unpack('<BBBB', struct.pack('<I', ip))))), port])
        print 'Server list:', addrs

    def on_friend_list(self, friends):
        more_info = steam_server.CMsgClientRequestFriendData()
        more_info.persona_state_requested = EClientPersonaStateFlag.PlayerName | EClientPersonaStateFlag.Presence
        if not friends.bincremental:
            self.friends = {}
        for friend in friends.friends:
            fid = friend.ulfriendid
            if friend.efriendrelationship == EFriendRelationship.none:
                if fid in self.friends:
                    del self.friends[fid]
            else:
                self.friends[fid] = steam.Friend(self, fid)
                self.friends[fid].relationship = friend.efriendrelationship
                more_info.friends.append(fid)
        self.send(EMsg.ClientRequestFriendData | proto_mask, more_info)

    def on_friend_state(self, msg):
        for friend in msg.friends:
            fid = friend.friendid
            if fid not in self.friends:
                self.friends[fid] = steam.Friend(self, fid)
            if msg.status_flags & EClientPersonaStateFlag.PlayerName:
                self.friends[fid].name = friend.player_name

    def on_friend_msg(self, msg):
        print msg

    def on_addrinfo(self, msg):
        # ask steam to send us a validation email if we don't have a verified email address
        if not msg.email_is_validated:
            source = steam.GID(0)
            source.process = 0
            source.box = 0
            source.sequence = self.sequence + 1
            source.start_time = int(time.time())
            self.send(EMsg.ClientRequestValidationMail, '', job=long(source), target=0xFFFFFFFFFFFFFFFF)

    def on_validate_email(self, msg):
        # TODO: check our email for the validation message and hit the verify URL
        pass

    def on_from_gc(self, msg):
        print 'From GC:', repr(msg.payload)

    def on_connect_token(self, msg):
        print 'Connect tokens:', len(msg.tokens)
        for t in msg.tokens:
            self.connect_tokens.insert(0, t)
        self.connect_tokens = self.connect_tokens[:msg.max_tokens_to_keep]

    def heartbeat(self, wait=9):
        while 1:
            self.send(
                EMsg.ClientHeartBeat | proto_mask, steam_server.CMsgClientHeartBeat())
            time.sleep(wait)

    def msg_pump(self):
        while True:
            try:
                for msg in self.connection.pump():
                    self.msg_queue.put(msg)
            except socket.error:
                pass
            except Exception:
                print '-' * 20
                print traceback.format_exc()
                print '-' * 20

    def send(self, emsg, body, job=None, target=None):
        if not isinstance(body, str):
            body = body.SerializeToString()
        if isinstance(job, type(lambda: 0)):
            self.current_job += 1
            src_id = self.current_job
            self.jobs[src_id] = job
            target_id = src_id
        else:
            src_id = job
            target_id = job
        if target:
            target_id = target

        if emsg == EMsg.ChannelEncryptResponse:
            hdr = {
                'msg': emsg,
                'sourceJobID': target_id,
                'targetJobID': src_id,
            }
            hdr = {k: v for (k, v) in hdr.items() if v is not None}
            header = steamd.MsgHdr.dumps(hdr)
        elif emsg & proto_mask:
            proto = {
                'steamid': long(self.steam_id),
                'client_sessionid': self.session_id,
                'jobid_target': target_id,
                'jobid_source': src_id,
            }
            proto = {k: v for (k, v) in proto.items() if v is not None}
            proto = steam_base.CMsgProtoBufHeader(**proto).SerializeToString()
            # '\t\x00\x00\x00\x00\x01\x00\x10\x01' # proto
            header = struct.pack('<II', emsg, len(proto)) + proto
        else:
            hdr = {
                # 'msg': emsg,
                # 'targetJobID': target_id,
                # 'sourceJobID': src_id,
                'steamID': long(self.steam_id),
                'sessionID': self.session_id,
            }
            header = steamd.ExtendedClientMsgHdr.dumps(hdr)
        self.connection.send(header + body)
