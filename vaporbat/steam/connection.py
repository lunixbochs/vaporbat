from buffer import Buffer
from crypto import encrypt, decrypt

import socket
import struct

class Connection:
    MAGIC = 'VT01'

    def __init__(self, host, port):
        self.key = None
        self.buf = ''
        self.socket = socket.socket()
        self.socket.settimeout(5)
        self.socket.connect((host, port))
        self.socket.settimeout(30)
        self.length = None

    def send(self, data):
        if self.key:
            data = encrypt(data, self.key)
        length = struct.pack('<I', len(data))
        self.socket.send(length + self.MAGIC + data)

    def recv(self):
        data = self.socket.recv(4096)
        if data == '':
            # TODO: something like Connection.Disconnected?
            raise socket.error('disconnected from remote host')
        return self.parse(data)

    def pump(self):
        while True:
            for packet in self.recv():
                yield Buffer(packet)

    def parse(self, data):
        self.buf += data
        if self.length is None:
            if len(self.buf) < 8:
                return
            self.length, = struct.unpack('<I', self.buf[:4])
            if self.buf[4:8] != self.MAGIC:
                raise socket.error('invalid magic')
            self.buf = self.buf[8:]

        if len(self.buf) < self.length:
            return

        packet, self.buf = self.buf[:self.length], self.buf[self.length:]
        self.length = None
        if self.key:
            packet = decrypt(packet, self.key)
        yield packet
