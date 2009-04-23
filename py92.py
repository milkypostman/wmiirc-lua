import struct

def _string_property(name, idx):
    def _get(self):
        return self._data[idx+1]

    def _set(self, data):
        self._data[idx] = len(data)
        self._data[idx+1] = data
        self._fmt[idx+1] = "%ds" % len(data)

    return property(fget=_get, fset=_set)


def _property(name, idx):
    def _get(self):
        return self._data[idx]

    def _set(self, data):
        self._data[idx] = data

    return property(fget=_get, fset=_set)


class _MetaMessage:
    def __new__(mcs, cls, bases, attrs):
        slots = attrs.get('__slots__', [])
        fields = []
        for base in bases:
            fields.extend(getattr(base, 'fields', []))

        fields.extend(attrs.get('fields', []))

        idx = 0
        data = []
        fmt = []
        # we only need to add slots for things that we defined as fields
        for field in attrs.get('fields', []):
            name = field[0]
            fmt = field[1]
            if name in attrs:
                # FIXME: Don't raise exception!
                raise Exception("%s is already defined as an attribute" % name)

            if fmt == 'string':
                attrs[name] = _string_property(name, len(data))
                fmt.extend(('H', '0s'))
                data.extend((0, ''))
            else:
                attrs[name] = _string_property(name, len(data))
                fmt.append(fmt)
                data.append(0)

        attrs['fields'] = tuple(fields)
        attrs['_data_template'] = data
        attrs['_fmt_template'] = fmt

        return type.__new__(mcs, cls, bases, attrs)

class Message:
    __metaclass__ = _MetaMessage
    __slots__ = ['_data', '_fmt']

    def __init__(self):
        self._data = self._data_template[:]
        self._fmt = self._fmt_template[:]


