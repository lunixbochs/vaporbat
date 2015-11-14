from cStringIO import StringIO
import socket
import struct
import sys
import time

from vaporbat.steam.protobuf import steam_remote

client_id = 1234
PREFIX = 0xA05F4C21FFFFFFFF

def discover():
    hdr = steam_remote.CMsgRemoteClientBroadcastHeader()
    hdr.client_id = client_id
    hdr.msg_type = steam_remote.k_ERemoteClientBroadcastMsgDiscovery
    hdr = hdr.SerializeToString()

    msg = steam_remote.CMsgRemoteClientBroadcastDiscovery()
    msg.seq_num = 1
    msg = msg.SerializeToString()

    data = struct.pack('<Q', PREFIX)
    data += struct.pack('<I', len(hdr)) + hdr
    data += struct.pack('<I', len(msg)) + msg

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.bind(('0.0.0.0', 27036))

    s.settimeout(0.3)
    resp = None
    while not resp:
        print 'broadcasting discovery...', len(data), data.encode('hex')
        s.sendto(data, ('255.255.255.255', 27036))
        while True:
            try:
                resp, addr = s.recvfrom(1024)
                if resp and resp != data:
                    print 'got response', resp.encode('hex')
                    break
                resp = None
            except socket.timeout:
                break
        time.sleep(0.1)

    assert(struct.unpack('<Q', resp[:8]) == (PREFIX,))
    length, = struct.unpack('<I', resp[8:12])
    resp = resp[8+4:]
    hdrb = resp[:length]
    resp = resp[length:]
    length, = struct.unpack('<I', resp[:4])
    msgb = resp[4:4+length]

    hdr = steam_remote.CMsgRemoteClientBroadcastHeader()
    hdr.ParseFromString(hdrb)
    assert(hdr.msg_type == steam_remote.k_ERemoteClientBroadcastMsgStatus)
    msg = steam_remote.CMsgRemoteClientBroadcastStatus()
    msg.ParseFromString(msgb)
    return msg

if __name__ == '__main__':
    print discover()
