import socket
import sys
import os
import logging
import heapq
import thread
import cStringIO
import time
import collections
import Queue
import copy
log = logging.getLogger('py9')

VERSION = '9P2000'
MSIZE = 8192 # magic number defined in Plan9 for [TR]version and [TR]read
MAX_MSG = 100
NOFID = 0xFFFF

class MessageData(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class Data(object):
    """
    P9 Raw Data
    ================

    Base class for all other P9 datatypes.  By default this class
    packs/unpacks raw data.
    """

    def __init__(self, size=0):
        """
        Initialize a new raw data type of length 'size'.

        Note: size may be a class instance that returns a value for int(size).
        """
        self.size = lambda _: size
        if callable(size):
            self.size = size

    def pack(self, data, ctx=None):
        """ convert to a p9 byte sequence """
        return data

    def unpack(self, sock, ctx=None, new=False):
        """ get data from a socket """
        l = self.size(ctx)
        if l > 0:
            return sock.recv(l)

class Int(Data):
    """
    P9 Integer Data
    =======================
    Encodes and decodes integer numbers to an arbitrary length.
    """

    def __init__(self, size=0):
        super(Int, self).__init__(size)

    def pack(self, data, ctx=None):
        size = self.size(ctx)

        buffer = []
        for i in range(size):
            buffer.append(chr(data & 0xff))
            data >>= 8

        return ''.join(buffer)

    def unpack(self, sock, ctx=None, new=False):
        size = self.size(ctx)
        rawdata = sock.recv(size)
        data = 0
        for i in range(size):
            cur = ord(rawdata[i]) << (i * 8)
            data += cur

        return data

class String(Data):
    length = Int(2)
    def pack(self, data, ctx=None):
        length = self.length.pack(len(data))
        return length + data

    def unpack(self, sock, ctx=None, new=False):
        length = self.length.unpack(sock)
        return sock.recv(length)

class Array(Data, list):
    def __init__(self, size, handler=None):
        super(Array, self).__init__(size)
        self.handler = handler

    def pack(self, data=None, ctx=None):
        if data == None:
            data = self
        size = self.size(ctx)

        if size != len(data):
            raise Exception("Error in Array")

        buffer = []
        for item in data:
            buffer.append(self.handler.pack(item, buffer))

        return ''.join(buffer)


    def unpack(self, sock, ctx=None, new=False):
        size = self.size(ctx)

        if new:
            data = []
        else:
            data = self

        for i in range(size):
            data.append(self.handler.unpack(sock, data, True))

        return data


class Struct(dict):
    """
    Structure to hold multiple base elements such as String/Integer/Data
    """

    _fields = []

    def __init__(self, sock=None, *args, **kwargs):
        super(Struct, self).__init__()

        self._fdict = {}
        for name, handler in self._fields:
            self._fdict[name] = handler

        if sock is not None:
            self.unpack(sock)
        else:
            for name in kwargs:
                self[name] = kwargs[name]

    def pack(self, data=None, ctx=None):
        if data == None:
            data = self

        buffer = []
        for name,handler in self._fields:
            buffer.append(self._fdict[name].pack(data[name], self))

        return ''.join(buffer)

    def unpack(self, sock, ctx=None, new=False):
        if new:
            data = self.__class__()
        else:
            data = self

        print self.__class__, id(self), id(data)

        for name, handler in self._fields:
            data[name] = handler.unpack(sock, self, True)

        return data

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

class Qid(Struct):
    _fields = [
        ('type', Int(1)),
        ('version', Int(4)),
        ('path', Int(8)),
        ]

class Stat(Struct):
    _fields = [
        ('size', Int(2)),
        ('type', Int(2)),
        ('dev', Int(4)),
        ('qid', Qid()),
        ('mode', Int(4)),
        ('atime', Int(4)),
        ('mtime', Int(4)),
        ('length', Int(8)),
        ('name', String()),
        ('uid', String()),
        ('gid', String()),
        ('muid', String()),
        ]

class Message(Struct):
    types = {}
    _fields = [
            ('tag', Int(2)),
            ]


    _sizehandler = Int(4)

    def __new__(cls, sock=None, *args, **kwargs):
        """ use the socket to unpack data """
        if cls == Message and (sock is not None) and isinstance(sock, socket.socket):
            size = Int(4).unpack(sock)

            mtype = Int(1).unpack(sock)

            msg = super(Message, cls).__new__(cls.types[mtype])

            return msg

        return super(Message, cls).__new__(cls)

    def pack(self, data=None, ctx=None):
        if data == None:
            data = self

        d = super(Message, self).pack(data, ctx)

        sizedata = self._sizehandler.pack( 4 + 1 + len(d) )
        #print [sizedata, self._typedata, d]
        return ''.join([sizedata, self._typedata, d])

def msg(num):
    """ simple decorator that counts our messages """
    global MAX_MSG
    if num > MAX_MSG:
        MAX_MSG = num+1

    def _msg(cls):
        cls._typedata = Int(1).pack(num)
        Message.types[num] = cls
        return cls

    return _msg


@msg(100)
class Tversion(Message):
    _fields = Message._fields + [
            ('msize', Int(4)),
            ('version', String()),
            ]

@msg(101)
class Rversion(Message):
    _fields = Message._fields + [
        ('msize', Int(4)),
        ('version', String()),
        ]

@msg(102)
class Tauth(Message):
    _fields = Message._fields + [
        ('afid', Int(4)),
        ('uname', String()),
        ('aname', String()),
        ]

@msg(103)
class Rauth(Message):
    _fields = Message._fields + [
        ('aqid', Qid()),
        ]

@msg(104)
class Tattach(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('afid', Int(4)),
        ('uname', String()),
        ('aname', String()),
        ]

@msg(105)
class Rattach(Message):
    _fields = Message._fields + [
        ('qid', Qid()),
        ]

    #@msg(106)
#class Terror(Message):
#    def __init__(self):
#        raise Exception("Terror is an invalid message")

@msg(107)
class Rerror(Message):
    _fields = Message._fields + [
        ('ename', String()),
        ]

@msg(108)
class Tflush(Message):
    _fields = Message._fields + [
        ('oldtag', Int(2)),
        ]

@msg(109)
class Rflush(Message):
    pass

@msg(110)
class Twalk(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('newfid', Int(4)),
        ('nwname', Int(2)),
        ('wname', Array(lambda ctx: ctx.nwname, String())),
        ]

@msg(111)
class Rwalk(Message):
    _fields = Message._fields + [
        ('nwqid', Int(2)),
        ('wqid', Array(lambda ctx: ctx.nwqid, Qid())),
        ]

@msg(112)
class Topen(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('mode', Int(1)),
        ]

@msg(113)
class Ropen(Message):
    _fields = Message._fields + [
        ('qid', Qid()),
        ('iounit', Int(4)),
        ]

@msg(114)
class Tcreate(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('name', String()),
        ('perm', Int(4)),
        ('mode', Int(1)),
        ]

@msg(115)
class Rcreate(Message):
    _fields = Message._fields + [
        ('qid', Qid()),
        ('iounit', Int(4)),
        ]

@msg(116)
class Tread(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('offset', Int(8)),
        ('count', Int(4)),
        ]

@msg(117)
class Rread(Message):
    _fields = Message._fields + [
        ('count', Int(4)),
        ('data', Data(lambda ctx: ctx.count)),
        ]

@msg(118)
class Twrite(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('offset', Int(8)),
        ('count', Int(4)),
        ('data', Data(lambda ctx: ctx.count)),
        ]

@msg(119)
class Rwrite(Message):
    _fields = Message._fields + [
        ('count', Int(4)),
        ]

@msg(120)
class Tclunk(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ]

@msg(121)
class Rclunk(Message):
    pass

@msg(122)
class Tremove(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ]

@msg(123)
class Rremove(Message):
    pass

@msg(124)
class Tstat(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ]

@msg(125)
class Rstat(Message):
    _fields = Message._fields + [
        ('stat', Stat()),
        ]

@msg(124)
class Twstat(Message):
    _fields = Message._fields + [
        ('fid', Int(4)),
        ('stat', Stat()),
        ]

@msg(125)
class Rwstat(Message):
    pass

class StringSocket:
    """
    Wrapper around the cStringIO.StringIO class providing
    some added functionality and socket functions.

    Adds the following functions:
        send : write data do the buffer
        recv : read data from the buffer
        eof : see if we have reached the end of the buffer
    """

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

    def eof(self):
        result = False
        if self.buffer.read(1) == '':
            result = True
        else:
            self.buffer.seek(-1, 1)
        return result

    def __getattr__(self, name):
        length = self.buffer.tell()
        if length > self.length:
            self.length = length
        return getattr(self.buffer, name)

    def __repr__(self):
        return self.buffer.getvalue()

class Client():
    recvqueues = collections.defaultdict(collections.deque)

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

        #self.recvthread = thread.start_new_thread(self._recv, tuple())

        version = self._version()

        log.debug("connected to server (version %s)" % version)

        if version != VERSION:
            raise Exception("9P Version Mismatch")

        self.rootfid = 0

        self._attach(self.rootfid)

        log.debug("succesfully attached")

    def _recv(self, tag):
        q = self.recvqueues[tag]
        if len(q) > 0:
            return q.pop()

        while True:
            msg = Message(self.sock)
            t = msg.tag
            if t == tag:
                return msg
            self.recvqueues[t].appendleft(msg)

    def _obtainfid(self):
        return heapq.heappop(self._fidheap)

    def _releasefid(self, fid):
        heapq.heappush(self._fidheap, fid)

    def _obtaintag(self):
        return heapq.heappop(self._tagheap)

    def _releasetag(self, tag):
        heapq.heappush(self._tagheap, tag)

    def _pullmessage(self, tag):
        """
        Get a message from the socket with tag == tid.
        """


    def _message(self, msg):
        tag = self._obtaintag()

        msg.tag = tag

        logging.debug("sending %s" % msg.__class__)

        self.sock.send(msg.pack())

        try:
            resp = self._recv(tag)
            #while resp is None:
            #    try:
            #        resp = queue.get_nowait()
            #    except Queue.Empty:
            #        time.sleep(.1)
            #print 'flushing'
            #print 'done flushing'
            #resp = queue.get()
        except KeyboardInterrupt:
            self._flush(tag)
            self._releasetag(tag)
            resp = self._recv(tag)
            raise KeyboardInterrupt

        self._releasetag(tag)
        logging.debug("recieving %s" % msg.__class__)

        if type(resp) == Rerror  and type(msg) != Tflush:
            raise IOError(str(type(msg)) + " : " + resp.ename)

        return resp

    def _flush(self, oldtag):
        print "_flush", oldtag
        msg = Tflush(oldtag = oldtag)
        self._message(msg)

    def _version(self):
        t = Tversion( msize = MSIZE, version = VERSION)

        r = self._message(t)
        self.msize = r.msize

        return r.version

    def _attach(self, fid = None):
        if fid == None:
            fid = self._obtainfid()

        t = Tattach(
                fid = fid,
                afid = NOFID,
                uname = os.getenv('USER'),
                aname = os.getenv('USER'),
                )

        r = self._message(t)

        return t.fid

    def ls(self, path):
        """ list a directory """
        buffer = self.read(path)

        # do an ls
        files = []
        while not buffer.eof():
            stat = Stat()
            stat.unpack(buffer)
            files.append( stat.name )

        return files

    def _walk(self, path):
        path = filter(None, path.split('/'))
        t = Twalk(
                fid=self.rootfid, 
                newfid=self._obtainfid(),
                nwname = len(path),
                wname = path,
            )

        r = self._message(t)

        return t.newfid

    def _open(self, fid, mode = 0):
        t = Topen(
                fid = fid,
                mode = mode,
                )

        r = self._message(t)

        return r.qid

    def _clunk(self, fid):
        t = Tclunk(fid = fid)

        self._message(t)

        self._releasefid(fid)

    def readln_iter(self, path):
        fid = self._walk(path)
        qid = self._open(fid)

        buffer = ''

        t = Tread()
        t.fid = fid
        t.count = self.msize
        readoffset = 0
        try:
            while(True):
                t.offset = readoffset

                try:
                    r = self._message(t)
                except IOError:
                    break

                if r.count < 1:
                    yield buffer
                    break

                buffer += r.data
                readoffset += len(buffer)

                offset=0
                while(True):
                    l = buffer.find('\n', offset)

                    if l < 0:
                        buffer = buffer[offset:]
                        break

                    yield buffer[offset:l]
                    offset = l+1
        finally:
            self._clunk(fid)

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
        qid = self._open(fid, 1)

        left = len(data)

        t = Twrite()
        t.tag = 0
        t.fid = fid
        t.offset = 0
        t.count = left
        t.data = data

        while left > 0:
            t.count = left & 0xff
            t.data = data[t.offset:t.count]

            resp = self._message(t)

            sent = resp.count
            t.offset += sent
            left -= sent

        self._clunk(fid)





