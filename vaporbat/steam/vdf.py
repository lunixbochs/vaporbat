from buffer import Buffer

class Type:
    none = 0
    string = 1
    int32 = 2
    float32 = 3
    pointer = 4
    wide_string = 5
    color = 6
    uint64 = 7
    end = 8

def parse(buf):
    if isinstance(buf, basestring):
        buf = Buffer(buf)

    obj = {}
    typ = buf.read('B')
    name = buf.read_string()

    if typ == Type.none:
        obj[name] = parse(buf)
    elif typ == Type.string:
        obj[name] = buf.read_string()
    elif typ in (Type.int32, Type.color, Type.pointer):
        obj[name] = buf.read('<i')
    elif typ == Type.uint64:
        obj[name] = buf.read('<Q')
    elif typ == Type.float32:
        obj[name] = buf.read('<f')

    return obj
