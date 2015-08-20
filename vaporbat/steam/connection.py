from buffer import Buffer
from crypto import encrypt, decrypt

import socket
import struct

class Connection:
    MAGIC = 'VT01'

    def __init__(self, host, port):
        self.key = None
        self.old = ''
        self.socket = socket.socket()
        self.socket.settimeout(5)
        self.socket.connect((host, port))
        self.socket.settimeout(30)
        self.length = 0

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
                if len(packet):
                    yield Buffer(packet)

    def parse(self, data):
        if self.old:
            data = self.old + data
            self.old = ''
        else:
            self.length, = struct.unpack('<I', data[:4])
            data = data[8:]

        if len(data) < self.length:
            self.old = data
            yield ''
        else:
            packet, data = data[:self.length], data[self.length:]
            if self.key:
                packet = decrypt(packet, self.key)
            if len(data):
                self.old = data
            yield packet
