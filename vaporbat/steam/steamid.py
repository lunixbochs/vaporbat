# WIP: see https://developer.valvesoftware.com/wiki/SteamID
import re

class SteamID(object):
    id_re = re.compile(r'STEAM_(\d+):(\d+):(\d+)')

    class ChatInstanceFlags:
          Clan = 0x100000 >> 1
          Lobby = 0x100000 >> 2
          MMSLobby = 0x100000 >> 3

    def __init__(self, steamid):
        if isinstance(steamid, int) or isinstance(steamid, long):
            self.id = steamid
        elif isinstance(steamid, str):
            m = self.id_re.match(steamid)
            if not m:
                raise TypeError('SteamID has invalid format.')

            universe, part, account = m.groups()
            account = account * 2 + part
            self.universe = universe
            self.account = account
        elif isinstance(steamid, SteamID):
            self.id = steamid.id

    def __repr__(self):
        return str(self.id)

    def __getitem__(self, v):
        b, m = v
        return (self.id >> b) & m

    def __setitem__(self, b, v):
        b, m = b
        self.id = (self.id & ~(m << b)) | ((v & m) << b)

    def __long__(self):
        return self.id

    @property
    def account_type(self):
        return self[52, 0xF]
    
    @account_type.setter
    def account_type(self, value):
        self[52, 0xF] = value

    @property
    def universe(self):
        return self[56, 0xFF]

    @universe.setter
    def universe(self, value):
        self[56, 0xFF] = value

    @property
    def instance(self):
        return self[32, 0xFFFFF]
    
    @instance.setter
    def instance(self, value):
        self[32, 0xFFFFF] = value
