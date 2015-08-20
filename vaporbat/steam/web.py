from collections import OrderedDict
from steamid import SteamID

import crypto
import requests

base = 'api.steampowered.com'

def call(interface, func, version=1, data=None):
    url = 'http://{0}/{1}/{2}/v{3}'.format(
        base, interface, func, version,
    )
    if data is not None:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return requests.post(url, headers=headers, data=data)
    else:
        return requests.get(url)

def login(steamid, login_key):
    steamid = SteamID(steamid)
    session_key, crypted_key, _ = crypto.make_session_key()
    ticket = crypto.encrypt(login_key, session_key)
    key = call('ISteamUserAuth', 'AuthenticateUser', data={
        'steamid': steamid.id,
        'sessionkey': crypted_key,
        'encrypted_loginkey': ticket,
    })
    return key.json().get('authenticateuser', {}).get('token')
