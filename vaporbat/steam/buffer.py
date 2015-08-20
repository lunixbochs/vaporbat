import struct

class Buffer:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def truncate(self):
        return Buffer(self.read_rest())

    def read(self, fmt):
        length = struct.calcsize(fmt)
        out = struct.unpack(fmt, self.read_len(length))
        if len(out) == 1:
            return out[0]
        else:
            return out

    def read_rest(self):
        return self.data[self.pos:]

    def read_len(self, length):
        data = self.data[self.pos:self.pos+length]
        self.pos += length
        return data

    def read_string(self):
        left, _ = self.data[self.pos:].split('\0')
        self.pos += len(left) + 1
        return left

    def __str__(self):
        return self.data
