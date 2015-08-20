import argparse
import getpass
import hashlib
import os
import sys

from client import SteamClient
from steam.steamd import EMsg, EResult

parser = argparse.ArgumentParser(description='Python Steam client.')
parser.add_argument('user')
args = parser.parse_args()

sentry_file = os.path.expanduser('~/.sentry-%s' % args.user)
sentry_hash = None
if os.path.exists(sentry_file):
    with open(sentry_file, 'r') as f:
        sentry_hash = f.read()
try:
    password = getpass.getpass()
except KeyboardInterrupt:
    sys.exit(1)
client = SteamClient()
client.login(args.user, password, sentry_hash)
for emsg, msg in client.pump():
    if emsg == EMsg.ClientUpdateMachineAuth:
        print 'got sentry hash'
        sha1 = hashlib.sha1(msg.bytes).digest()
        with open(sentry_file, 'w') as f:
            f.write(sha1)
    elif emsg == EMsg.ClientNewLoginKey:
        print 'ready!'
    elif emsg == EMsg.ClientLogOnResponse:
        if msg.eresult == EResult.AccountLogonDenied:
            token = raw_input('SteamGuard Token: ')
            client.login(args.user, password, sentry_hash, token)
