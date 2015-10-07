import socket
import struct
import sys
import time

from vaporbat.steam.protobuf import steam_remote

client_id = 1234

def discover():
    hdr = steam_remote.CMsgRemoteClientBroadcastHeader()
    hdr.client_id = client_id
    hdr.msg_type = steam_remote.k_ERemoteClientBroadcastMsgDiscovery
    hdr = hdr.SerializeToString()

    msg = steam_remote.CMsgRemoteClientBroadcastDiscovery()
    msg.seq_num = 1
    msg = msg.SerializeToString()

    data = struct.pack('<Q', 0xFFFFFFFFA05F4C21)
    data += struct.pack('<I', len(hdr)) + hdr
    data += struct.pack('<I', len(msg)) + msg

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.bind(('0.0.0.0', 27036))

    s.settimeout(0.3)
    while True:
        print 'broadcasting discovery...'
        s.sendto(data, ('255.255.255.255', 27036))
        try:
            resp, addr = s.recvfrom(1024)
            if resp:
                print 'got response', resp
                break
        except socket.timeout:
            continue

    r = steam_remote.CMsgRemoteClientBroadcastStatus()
    r.ParseFromString(resp)
    return r

if __name__ == '__main__':
    print discover()
