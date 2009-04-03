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

"""
Specialized data structures for the P9 server.
The choice to write this from scratch was a learning excersize
and also because I wanted my classes to have structure that was
similar to the actual messages.

One improvement might be to make each message a simple data structure
with attributes (empty class) and then have a single Parser class that
takes that data structure and parses it.  Essentially this is what we 
have now but the packer is not decoupled from the structure itself.

This just seems to make more sense to only have to worry about a single
message instance that can pack and unpack itself, rather than
an instance of a data structure that you then pass to a specific packer
for that structure.

*** all message structures are immutable ***


"""

class Data(object):
    """
    P9 Raw Data
    ================

    Base class for all other P9 datatypes.  By default this class
    packs/unpacks raw data.
    """

    __slots__ = ['size']

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
    """
    P9 String Data
    ================
    Encodes the string length as a two byte string and appends the
    actual string
    """

    length = Int(2)
    def pack(self, data, ctx=None):
        length = self.length.pack(len(data))
        return length + data

    def unpack(self, sock, ctx=None, new=False):
        length = self.length.unpack(sock)
        return sock.recv(length)

class Array(Data):
    __slots__ = ['handler']
    """
    P9 Array Data
    =================
    Simple array wrapper for lists / tuples
    """
    def __init__(self, size, handler=None):
        super(Array, self).__init__(size)
        self.handler = handler

    def pack(self, data=None, ctx=None):
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
            data = self._data = []

        for i in range(size):
            data.append(self.handler.unpack(sock, data, True))

        return data

def _property(name):
    """ generates property methods for each of our fields """
    def get(self):
        return self._data[name]

    def set(self, data):
        self._data[name] = data

    return property(fget=get, fset=set)


class _MetaStruct(type):
    """
    Struct Meta-Class
    ====================
    This meta-class takes the field list and makes appropriate
    attributes for each field.  These attributes are generated
    by the _property method and are an alternative to overwriting
    the __getattr__ and __setattr__ methods.
    """

    def __new__(cls, name, bases, attrs):
        slots = attrs.get('__slots__', [])
        fields = ()
        for base in bases:
            fields += tuple(getattr(base, 'fields', ()))

        fields += tuple(attrs.get('fields', ()))

        # we only need to add slots for things that we defined as fields
        for field in attrs.get('fields', ()):
            name = field[0]
            if name in slots:
                raise ClassException("%s is already defined as an attribute" % name)
            slots.append(name)

        attrs['fields'] = fields
        attrs['__slots__'] = slots

        return type.__new__(cls, name, bases, attrs)

class Struct(object):
    """
    P9 Structure
    ----------------
    Structure to hold multiple base elements such as String/Integer/Data.
    Each structure can have multiple fields which are attributes for 
    any instance of the structure.
    """

    __slots__ = ['_fdict']

    fields = []

    __metaclass__ = _MetaStruct

    def __init__(self, sock=None, *args, **kwargs):
        super(Struct, self).__init__()
        self._fdict = {}


        for name, handler in self.fields:
            self._fdict[name] = handler

        if sock is not None:
            self.unpack(sock)
        else:
            for name in kwargs:
                setattr(self, name, kwargs[name])

    def pack(self, data=None, ctx=None):
        if data == None:
            data = self

        buffer = []
        for name,handler in self.fields:
            p = self._fdict[name].pack(getattr(data,name), self)
            buffer.append(p)

        return ''.join(buffer)

    def unpack(self, sock, ctx=None, new=False):
        if new:
            data = self.__class__()
        else:
            data = self

        for name, handler in self.fields:
            setattr(data, name, handler.unpack(sock, self, True))

        return data

class Qid(Struct):
    """
    P9 QID Structure
    -------
    Structure used when walking trees and a few other small things
    """
    fields = (
        ('type', Int(1)),
        ('version', Int(4)),
        ('path', Int(8)),
        )

class Stat(Struct):
    """
    P9 Stat Class
    ------------
    Used for getting attributes of P9 files and directories.
    """
    fields = (
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
        )

class _MetaMessage(_MetaStruct):
    """
    Struct Meta-Class
    ====================
    This meta-class takes the field list and makes appropriate
    attributes for each field.  These attributes are generated
    by the _property method and are an alternative to overwriting
    the __getattr__ and __setattr__ methods.
    """

    def __init__(cls, name, bases, dict):
        # Let _MetaStruct create our attributes
        super(_MetaMessage, cls).__init__(name, bases, dict)


        if hasattr(cls, 'type'):
            # record this class in the Message class
            cls.types[cls.type] = cls

            # prepack the type data
            cls._typedata = cls._typehandler.pack(cls.type)


class Message(Struct):
    """
    P9 Base Message Class
    ---------
    Base class for all messages used to add size and type
    information to the class.
    """
    __metaclass__ = _MetaMessage

    types = {}

    fields = (
            ('tag', Int(2)),
            )

    _typehandler = Int(1)
    _sizehandler = Int(4)

    def __new__(cls, sock=None, *args, **kwargs):
        """
        Base Class for all P9 Messages
        ---
        If a socket is passed into the constructure 
        the proper class type is returned
        """
        if cls == Message and (sock is not None) and isinstance(sock, socket.socket):
            size = cls._sizehandler.unpack(sock)
            mtype = cls._typehandler.unpack(sock)
            msg = super(Message, cls).__new__(cls.types[mtype])

            return msg

        return super(Message, cls).__new__(cls)

    def pack(self, data=None, ctx=None):
        """
        Pack a P9 Message.  Adds length information.
        """
        if data == None:
            data = self

        d = super(Message, self).pack(data, ctx)

        sizedata = self._sizehandler.pack( 4 + 1 + len(d) )
        print [sizedata, self._typedata, d]
        return ''.join([sizedata, self._typedata, d])


# type is a field but because it needs to be read before class
# creation, it is not treated as all the other fields.
class Tversion(Message):
    type = 100
    fields = (
            ('msize', Int(4)),
            ('version', String()),
            )

class Rversion(Message):
    type = 101
    fields = (
        ('msize', Int(4)),
        ('version', String()),
        )

class Tauth(Message):
    type = 102
    fields = (
        ('afid', Int(4)),
        ('uname', String()),
        ('aname', String()),
        )

class Rauth(Message):
    type = 103
    fields = (
        ('aqid', Qid()),
        )

class Tattach(Message):
    type = 104
    fields = (
        ('fid', Int(4)),
        ('afid', Int(4)),
        ('uname', String()),
        ('aname', String()),
        )

class Rattach(Message):
    type = 105
    fields = (
        ('qid', Qid()),
        )

#class Terror(Message):
#type = #106
#    def __init__(self):
#        raise Exception("Terror is an invalid message")

class Rerror(Message):
    type = 107
    fields = (
        ('ename', String()),
        )

class Tflush(Message):
    type = 108
    fields = (
        ('oldtag', Int(2)),
        )

class Rflush(Message):
    type = 109
    pass

class Twalk(Message):
    type = 110
    fields = (
        ('fid', Int(4)),
        ('newfid', Int(4)),
        ('nwname', Int(2)),
        ('wname', Array(lambda ctx: ctx.nwname, String())),
        )

class Rwalk(Message):
    type = 111
    fields = (
        ('nwqid', Int(2)),
        ('wqid', Array(lambda ctx: ctx.nwqid, Qid())),
        )

class Topen(Message):
    type = 112
    fields = (
        ('fid', Int(4)),
        ('mode', Int(1)),
        )

class Ropen(Message):
    type = 113
    fields = (
        ('qid', Qid()),
        ('iounit', Int(4)),
        )

class Tcreate(Message):
    type = 114
    fields = (
        ('fid', Int(4)),
        ('name', String()),
        ('perm', Int(4)),
        ('mode', Int(1)),
        )

class Rcreate(Message):
    type = 115
    fields = (
        ('qid', Qid()),
        ('iounit', Int(4)),
        )

class Tread(Message):
    type = 116
    fields = (
        ('fid', Int(4)),
        ('offset', Int(8)),
        ('count', Int(4)),
        )

class Rread(Message):
    type = 117
    fields = (
        ('count', Int(4)),
        ('data', Data(lambda ctx: ctx.count)),
        )

class Twrite(Message):
    type = 118
    fields = (
        ('fid', Int(4)),
        ('offset', Int(8)),
        ('count', Int(4)),
        ('data', Data(lambda ctx: ctx.count)),
        )

class Rwrite(Message):
    type = 119
    fields = (
        ('count', Int(4)),
        )

class Tclunk(Message):
    type = 120
    fields = (
        ('fid', Int(4)),
        )

class Rclunk(Message):
    type = 121
    pass

class Tremove(Message):
    type = 122
    fields = (
        ('fid', Int(4)),
        )

class Rremove(Message):
    type = 123
    pass

class Tstat(Message):
    type = 124
    fields = (
        ('fid', Int(4)),
        )

class Rstat(Message):
    type = 125
    fields = (
        ('stat', Stat()),
        )

class Twstat(Message):
    type = 124
    fields = (
        ('fid', Int(4)),
        ('stat', Stat()),
        )

class Rwstat(Message):
    type = 125


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
            stat = Stat(buffer)
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





