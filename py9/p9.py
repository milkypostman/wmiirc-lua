import socket
import sys
import os
import logging
import struct
import heapq
import cStringIO
log = logging.getLogger('py9')

VERSION = '9P2000'
MSIZE = 8192 # magic number defined in Plan9 for [TR]version and [TR]read
MAX_MSG = 100
NOFID = 0xFFFF

class Data(object):
    value = None
    def __init__(self, size=0, value=None):
        self.size = size
        self.value = value
        pass

    def pack(self):
        """ convert to a p9 byte sequence """
        pass

    def unpack(self, sock):
        """ get data from a socket """
        l = int(self.size)
        if l > 0:
            self.value = sock.recv(l)
        pass

    def __int__(self):
        return self.value

class Int(Data):
    _formats = {1:'B', 2:'H', 4:'I', 8:'L'}
    def __init__(self, size=0, value=None):
        super(Int, self).__init__(size, value)
        self.struct = struct.Struct(self._formats[size])

    def pack(self):
        return self.struct.pack(self.value)

    def unpack(self, sock):
        self.value = self.struct.unpack(sock.recv(self.size))[0]

class String(Data):
    struct = struct.Struct('H')

    def pack(self):
        return self.struct.pack(len(self.value)) + self.value

    def unpack(self, sock):
        length = self.struct.unpack(sock.recv(2))[0]
        self.value = sock.recv(length)

class Array(Data):
    def __init__(self, size, cls=None, *args):
        super(Array, self).__init__(size, [])
        self.cls = cls
        self.clsargs = args

    def __setattr__(self, name, values):
        if name == 'value' and (type(values) == list):
            self.__dict__['value'] = []
            for v in values:
                item = self.cls()
                item.value = v
                self.__dict__['value'].append(item)

        else:
            object.__setattr__(self, name, values)


    def pack(self):
        size = int(self.size)
        if size != len(self.value):
            raise Exception("Not enough items recieved for array")

        buffer = []
        for value in self.value:
            buffer.append(value.pack())

        return ''.join(buffer)

    def unpack(self, sock):
        self.value = []

        for i in range(int(self.size)):
            d = self.cls(*self.clsargs)
            d.unpack(sock)
            self.value.append(d)

class Struct(object):
    def __init__(self, count=0):
        self._fields = {}
        self._fieldset = []

    def _field(self, name, type):
        self._fields[name] = type
        self._fieldset.append( type )
        return type

    def __setattr__(self, name, value):
        fields = self.__dict__.get('_fields', False)
        if fields and name in fields:
            fields[name].value = value
        else:
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name in self.__dict__['_fields']:
            try:
                return self.__dict__['_fields'][name].value
            except AttributeError:
                return self.__dict__['_fields'][name]

        print self
        return object.__getattr__(self, name)

    def pack(self):
        buffer = []
        for field in self._fieldset:
            buffer.append(field.pack())

        return ''.join(buffer)

    def unpack(self, sock):
        for field in self._fieldset:
            field.unpack(sock)

class Qid(Struct):
    def __init__(self, count=0):
        super(Qid, self).__init__()
        self._field('type', Int(1))
        self._field('version', Int(4))
        self._field('path', Int(8))

class Stat(Struct):
    def __init__(self):
        super(Stat, self).__init__()
        self._field('size', Int(2))
        self._field('type', Int(2))
        self._field('dev', Int(4))

        self._field('qid', Qid())

        self._field('mode', Int(4))
        self._field('atime', Int(4))
        self._field('mtime', Int(4))

        self._field('length', Int(8))

        self._field('name', String())
        self._field('uid', String())
        self._field('gid', String())
        self._field('muid', String())



class Message(Struct):
    types = {}

    def __init__(self):
        super(Message, self).__init__()
        self._field('tag', Int(2))

    def pack(self):
        data = super(Message, self).pack()
        size = Int(4)
        size.value = 4 + 1 + len(data)
        return ''.join([size.pack(), self.type.pack(), data])

def unpack(sock):
    """ use the socket to unpack data """
    size = Int(4)
    size.unpack(sock)

    mtype = Int(1)
    mtype.unpack(sock)

    print mtype.value

    msg = Message.types[mtype.value]()
    msg.unpack(sock)

    return msg

def msg(num):
    """ simple decorator that counts our messages """
    global MAX_MSG
    if num > MAX_MSG:
        MAX_MSG = num+1

    def _msg(cls):
        cls.type = Int(1, num)
        Message.types[num] = cls
        return cls

    return _msg


@msg(100)
class Tversion(Message):
    def __init__(self):
        super(Tversion, self).__init__()
        self._field('msize', Int(4))
        self._field('version', String())

@msg(101)
class Rversion(Message):
    def __init__(self):
        super(Rversion, self).__init__()
        self._field('msize', Int(4))
        self._field('version', String())

@msg(102)
class Tauth(Message):
    def __init__(self):
        super(Tauth, self).__init__()
        self._field('afid', Int(4))
        self._field('uname', String())
        self._field('aname', String())

@msg(103)
class Rauth(Message):
    def __init__(self):
        super(Rauth, self).__init__()
        self._field('aqid', Qid())

@msg(104)
class Tattach(Message):
    def __init__(self):
        super(Tattach, self).__init__()
        self._field('fid', Int(4))
        self._field('afid', Int(4))
        self._field('uname', String())
        self._field('aname', String())

@msg(105)
class Rattach(Message):
    def __init__(self):
        super(Rattach, self).__init__()
        self._field('qid', Qid())

@msg(106)
class Terror(Message):
    def __init__(self):
        raise Exception("Terror is an invalid message")

@msg(107)
class Rerror(Message):
    def __init__(self):
        super(Rerror, self).__init__()
        self._field('ename', String())

@msg(108)
class Tflush(Message):
    def __init__(self):
        super(Tflush, self).__init__()
        self._field('oldtag', Int(4))

@msg(109)
class Rflush(Message):
    pass

@msg(110)
class Twalk(Message):
    def __init__(self):
        super(Twalk, self).__init__()
        self._field('fid', Int(4))
        self._field('newfid', Int(4))
        n = self._field('nwname', Int(2))
        self._field('wname', Array(n, String))

@msg(111)
class Rwalk(Message):
    def __init__(self):
        super(Rwalk, self).__init__()
        n = self._field('nwqid', Int(2))
        self._field('wqid', Array(n, Qid))

@msg(112)
class Topen(Message):
    def __init__(self):
        super(Topen, self).__init__()
        self._field('fid', Int(4))
        self._field('mode', Int(1))

@msg(113)
class Ropen(Message):
    def __init__(self):
        super(Ropen, self).__init__()
        self._field('qid', Qid())
        self._field('iounit', Int(4))

@msg(114)
class Tcreate(Message):
    def __init__(self):
        super(Tcreate, self).__init__()
        self._field('fid', Int(4))
        self._field('name', String())
        self._field('perm', Int(4))
        self._field('mode', Int(1))

@msg(115)
class Rcreate(Message):
    def __init__(self):
        super(Rcreate, self).__init__()
        self._field('qid', Qid())
        self._field('iounit', Int(4))

@msg(116)
class Tread(Message):
    def __init__(self):
        super(Tread, self).__init__()
        self._field('fid', Int(4))
        self._field('offset', Int(8))
        self._field('count', Int(4))

@msg(117)
class Rread(Message):
    def __init__(self):
        super(Rread, self).__init__()
        c = self._field('count', Int(4))
        self._field('data', Data(c))

@msg(118)
class Twrite(Message):
    def __init__(self):
        super(Twrite, self).__init__()
        self._field('fid', Int(4))
        self._field('offset', Int(8))
        c = self._field('count', Int(4))
        self._field('data', Raw(c))

@msg(119)
class Rwrite(Message):
    def __init__(self):
        super(Rwrite, self).__init__()
        c = self._field('count', Int(4))

@msg(120)
class Tclunk(Message):
    def __init__(self):
        super(Tclunk, self).__init__()
        self._field('fid', Int(4))

@msg(121)
class Rclunk(Message):
    def __init__(self):
        super(Rclunk, self).__init__()

@msg(122)
class Tremove(Message):
    def __init__(self):
        super(Tremove, self).__init__()
        self._field('fid', Int(4))

@msg(123)
class Rremove(Message):
    def __init__(self):
        super(Rremove, self).__init__()

    #    Tstat => 124,
    #    Rstat => 125,
    #    Twstat => 126,
    #    Rwstat => 127,
    #  }.freeze

#size[4] Tstat tag[2] fid[4]                                        
#size[4] Rstat tag[2] stat[n]                                       
#
#size[4] Twstat tag[2] fid[4] stat[n]                               
#size[4] Rwstat tag[2]
class StringSocket:
    def __init__(self):
        self.buffer = cStringIO.StringIO()
        self.length = 0

    def recv(self, size):
        return self.buffer.read(size)

    def send(self, data):
        self.buffer.write(data)
        length = self.buffer.tell()
        if length > self.length:
            self.length = length

    def eof():
        result = False
        if self.buffer.read() == '':
            result = True
        self.buffer.seek(-1, 1)
        return result

    def __len__(self):
        return self.length

    def __getattr__(self, name):
        length = self.buffer.tell()
        if length > self.length:
            self.length = length
        return getattr(self.buffer, name)

    def __repr__(self):
        return self.buffer.getvalue()

class Client():
    def __init__(self, addr):
        self._tagheap = range(1, 0xff)
        heapq.heapify(self._tagheap)
        self._fidheap = range(0xff, 0xffff)
        heapq.heapify(self._fidheap)

        sock_path = addr.split('!')
        try:
            if sock_path[0] == 'unix':
                sock = socket.socket(socket.AF_UNIX)
                sock.connect(sock_path[1])
            elif sock_path[0] == 'tcp':
                sock = socket.socket(socket.AF_INET)
                sock.connect((sock_path[1], int(sock_path[2])))
            else:
                return
        except socket.error, e:
            log.exception(e)
            sys.exit(-1)

        self.sock = sock

        version = self._version()
        print version

        if version != VERSION:
            raise Exception("9P Version Mismatch")

        self.rootfid = 0

        self._attach(self.rootfid)


    def _obtainfid(self):
        return heapq.heappop(self._fidheap)

    def _releasefid(self, fid):
        heapq.heappush(self._fidheap, fid)

    def _obtaintag(self):
        return heapq.heappop(self._tagheap)

    def _releasetag(self, tag):
        heapq.heappush(self._tagheap, tag)

    def _message(self, msg):
        tag = self._obtaintag()

        msg.tag = tag
        self.sock.send(msg.pack())
        resp = unpack(self.sock)

        if type(resp) == Rerror:
            raise IOError(str(type(msg)) + " : " + resp.ename)

        self._releasetag(tag)
        return resp

    def _version(self):
        t = Tversion()

        t.msize = MSIZE
        t.version = VERSION

        r = self._message(t)
        self.msize = r.msize

        return r.version

    def _attach(self, fid = None):
        t = Tattach()
        if fid == None:
            fid = self._obtainfid()
        t.fid = fid
        t.afid = NOFID
        t.uname = os.getenv('USER')
        t.aname = os.getenv('USER')

        r = self._message(t)

        return t.fid

    def ls(self, path):
        """ list a directory """
        buffer = self.read(path)
        eof = len(buffer)

        # do an ls
        files = []
        while buffer.tell() < eof:
            stat = Stat()
            stat.unpack(buffer)
            files.append( stat.name )

        return files

    def _walk(self, path):
        t = Twalk()
        t.tag = self._obtaintag()

        t.fid = self.rootfid
        t.newfid = self._obtainfid()
        path = filter(None, path.split('/'))
        t.nwname = len(path)
        t.wname = path

        r = self._message(t)

        return t.newfid

    def _open(self, fid, mode = 0):
        t = Topen()
        t.fid = fid
        t.mode = mode

        r = self._message(t)

        return r.qid

    def _clunk(self, fid):
        t = Tclunk()
        t.fid = fid

        self._message(t)

        self._releasefid(fid)

    def read(self, path):
        fid = self._walk(path)
        qid = self._open(fid)

        offset = 0
        buffer = StringSocket()
        t = Tread()
        t.fid = fid
        t.count = self.msize
        while(True):
            t.offset = offset

            r = self._message(t)

            if r.count < 1:
                break

            buffer.write(r.data)
            offset += r.count

        buffer.reset()

        self._clunk(fid)

        return buffer

    def write(self, path, data):
        fid = self._walk(path)
        qid = self._open(fid, 2)

        left = len(data)

        t = Tread()
        t.fid = fid
        t.offset = 0
        while left > 0:
            t.count = left & 0xff
            t.data = data[t.offset:t.count]

            resp = self._message(t)

            sent = resp.count
            t.offset += sent
            left -= sent

        self._clunk(fid)





