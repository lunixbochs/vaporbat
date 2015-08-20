class PackedBinary(object):
    def __init__(self, i=0):
        self.id = i

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

class GID(PackedBinary):
    @property
    def sequence(self):
        return self[0, 0xFFFFF]

    @sequence.setter
    def sequence(self, value):
        self[0, 0xFFFFF] = value

    @property
    def start_time(self):
        return self[20, 0x3FFFFFFF] + 1104537600

    @start_time.setter
    def start_time(self, value):
        self[20, 0x3FFFFFFF] = value - 1104537600

    @property
    def process(self):
        return self[50, 0xF]

    @process.setter
    def process(self, value):
        self[50, 0xF] = value

    @property
    def box(self):
        return self[54, 0x3FF]

    @box.setter
    def box(self, value):
        self[54, 0x3FF] = value
