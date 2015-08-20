import sys
import re

from jinja2 import Template

def translate_value(value):
    if isinstance(value, basestring):
        value = value.replace('::', '.')
        if value == 'ulong.MaxValue':
            value = 2 ** 64 - 1

    return value

class ClassParser:
    regex = re.compile(r'^(?P<const>const\s*)?'
                       r'(?P<steamid>steamidmarshal\s*)?'
                       r'(?P<gameid>gameidmarshal\s*)?'
                       r'(?P<bool>boolmarshal\s*)?'
                       r'(?P<proto>proto[^\s]*\s*)?'
                       r'(?P<protomask>protomask[^\s]*\s*)?'
                       r'(?P<type>[\w<>\.]+)\s*'
                       r'(?P<name>\w+)'
                       r'(\s*=\s*(?P<value>.+?))?;?$')

    def __init__(self, name, lines):
        self.name = name
        self.vars = []
        for line in lines:
            match = self.regex.match(line)
            if match:
                self.vars.append(match.groupdict())
            else:
                print 'unsupported var in {0}: {1}'.format(name, line)

    def dump(self):
        constants = []
        const_dict = {}
        keys = []

        for var in self.vars:
            if var.get('const'):
                name, value = var.get('name'), var.get('value')
                if name and value:
                    value = translate_value(value)
                    constants.append((name, value))
                    const_dict[name] = value
            else:
                name, typ = var.get('name'), var.get('type')
                typ = EnumParser.types.get(typ, typ)
                value = var.get('value')
                if value and '::' in value:
                    owner, attr = value.split('::', 1)
                    if owner == self.name:
                        value = const_dict.get(attr)

                value = translate_value(value or 0)
                keys.append((name, typ, value))

        return {
            'type': 'class',
            'name': self.name,
            'constants': constants,
            'properties': keys,
        }

class EnumParser:
    regex = re.compile(r'^([^= ]+)\s*=\s*((0x|-)?[\dA-F]+);?$')
    types = {}

    def __init__(self, name, typ, lines):
        self.name = name
        if not typ:
            typ = 'int'

        self.typ = typ
        EnumParser.types[name] = typ

        self.constants = []
        for line in lines:
            match = self.regex.match(line)
            if not match:
                print 'failed to parse:', line
                continue
            name, value = match.groups()[:2]
            value = translate_value(value)
            self.constants.append((name, value))

    def dump(self):
        return {
            'type': 'enum',
            'name': self.name,
            'constants': self.constants,
        }

class Parser:
    def __init__(self, data, regex):
        self.lines = data.split('\n')
        self.pos = 0

        self.regex = {}
        for k, r in regex.items():
            self.regex[k] = re.compile(r)

    def iter(self, match):
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            line = line.strip()
            self.pos += 1

            if not line:
                continue

            if match:
                for name, r in self.regex.items():
                    match = r.match(line)
                    if match:
                        yield name, match
                        break
                else:
                    raise Exception('could not match line: ' + line)
            else:
                yield line

    def __iter__(self):
        return self.iter(match=True)

    def seek(self, r):
        lines = []
        r = re.compile(r)
        for line in self.iter(match=False):
            if r.match(line):
                return lines
            else:
                lines.append(line)

def parse(name):
    print 'Parsing file:', name
    with open(name) as f:
        data = f.read()

    parser = Parser(data, {
        'import': r'^#import "(.+)"$',
        'enum': r'^enum (?P<name>\w+)(<(?P<type>[^>]+)>)?',
        'class': r'^class ([^<]+)(<.+>)?$',
    })

    out = []
    for key, match in parser:
        if key == 'import':
            out.extend(parse(match.group(1)))
        elif key == 'enum':
            parser.seek(r'\{')
            lines = parser.seek(r'^\};?$')
            name, typ = match.group('name'), match.group('type')
            out.append(EnumParser(name, typ, lines))
        elif key == 'class':
            parser.seek(r'\{')
            lines = parser.seek(r'^\};?$')
            out.append(ClassParser(match.group(1), lines))

    return out

if __name__ == '__main__':
    import os
    filename = sys.argv[1]
    cwd = os.getcwd()

    os.chdir(os.path.dirname(filename))
    filename = os.path.basename(filename)
    out = parse(filename)
    os.chdir(cwd)

    with open('python.template') as f:
        t = Template(f.read())
        data = t.render(types=[x.dump() for x in out])
        out = filename.replace('.steamd', '') + '.py'
        with open(out, 'w') as o:
            o.write(data)
