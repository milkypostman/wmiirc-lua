#
# Copyright (C) 2009 Donald Ephraim Curtis <dcurtis@cs.uiowa.edu>
# Copyright (C) 2007 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# vim:syntax=python:sw=4:ts=4:expandtab

import os
import logging
import socket
import thread
import sys
import cmd
from error import *

version = "9P2000"
nofid = 0xffffffffL
notag = 0xffff

DIR = 020000000000L
QDIR = 0x80
OREAD, OWRITE, ORDWR, OEXEC = range(4)
OTRUNC, ORCLOSE = 0x10, 0x40

PORT = 564

def lock(func):
    def wrapper(self, *args, **kwargs):
        self.lock.acquire()
        ret = None
        try:
            ret = func(self, self.counter, *args, **kwargs)
        except Exception, e:
            logging.exception(e)
            try:
                _close(self.counter)
            except:
                pass
        self.counter += 1
        self.lock.release()
        return ret
    return wrapper

class Client(object):
    ROOT = 23
    verbose = 1
    def __init__(self, path):
        #sock_path = os.environ.get('WMII_ADDRESS', '').split('!')
        sock_path = path.split('!')
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
            logging.exception(e)
            sys.exit(-1)

        self.sock = cmd.Marshal9P(sock)

        maxbuf, vers = self._version(16 * 1024, version)
        if vers != version:
            raise Error('version mismatch: %r' % vers)

        self._attach(self.ROOT, nofid, '', '')
        self.connected = True
        self.counter = 42
        self.lock = thread.allocate_lock()

    def _rpc(self, type, *args):
        tag = 1
        if type == cmd.Tversion:
            tag = notag
        if self.verbose:
            print cmd.repr(type), repr(args)
        self.sock.send(type, tag, *args)
        rtype, rtag, vals = self.sock.recv()
        if self.verbose:
            print cmd.repr(rtype), repr(vals)
        if rtag != tag:
            raise Error("invalid tag received")
        if rtype == cmd.Rerror:
            raise P9Error(vals)
        if rtype != type + 1:
            raise Error("incorrect reply from server: %r" % [rtype, rtag, vals])
        return vals

    def _version(self, msize, version):
        return self._rpc(cmd.Tversion, msize, version)

    def _attach(self, fid, afid, uname, aname):
        return self._rpc(cmd.Tattach, fid, afid, uname, aname)

    def _stat(self, fid):
        return self._rpc(cmd.Tstat, fid)

    def _wstat(self, fid, stats):
        return self._rpc(cmd.Twstat, fid, stats)

    def _walk(self, fd, path):
        pstr = path
        root = self.ROOT
        path = filter(None, path.split('/'))
        try:
            w = self._rpc(cmd.Twalk, (root, fd, path))
        except P9Error, e:
            raise P9Exception('_walk: %s: %s' % (pstr, e.args[0]))

        if len(w) < len(path):
            raise P9Exception('_walk: %s: not found' % pstr)
        return w

    def _open(self, fd, mode = 0):
        try:
            t =  self._rpc(cmd.Topen, fd, mode)
            if not t:
                raise P9Exception('_open: failed to open')
        except P9Error, e:
            raise P9Exception('_open: %s' % e.args[0])
        return t

    def _close(self, fd):
        try:
            self._rpc(cmd.Tclunk, fd)
        except P9Error, e:
            raise P9Exception('_close: %s' % e.args[0])

    def _read(self, fd, length):
        try:
            pos = 0L
            buf =  self._rpc(cmd.Tread, fd, pos, length)
            while len(buf) > 0:
                pos += len(buf)
                yield buf
                buf = self._rpc(cmd.Tread, fd, pos, length)
        except P9Error, e:
            raise P9Exception('_read: %s' % e.args[0])

    def _write(self, fd, buf):
        try:
            towrite = len(buf)
            pos = 0
            while pos < towrite:
                pos += self._rpc(cmd.Twrite, fd, pos, buf[pos:pos + 1024])
        except P9Error, e:
            raise P9Exception('_write: %s' % e.args[0])

    def _create(self, fd, name, mode = 1, perm = 0644):
        try:
            return self._rpc(cmd.Tcreate, fd, name, perm, mode)
        except P9Error, e:
            self._close()
            raise P9Exception('_create: %s' % e.args[0])

    def _remove(self, fd):
        try:
            return self._rpc(cmd.Tremove, fd)
        except P9Error, e:
            raise P9Exception('_remove: %s' % e.args[0])

    @lock
    def write(self, fd, file, value):
        if type(value) not in (type([]), type(()), type(set())):
            value = [value]
        try:
            # TODO: walk on non existent files fail. needed?
            self._walk(fd, file)
        except:
            pass
        self._open(fd, mode = OWRITE|OTRUNC)
        self._write(fd, '\n'.join(value) + '\n')
        self._close(fd)

    @lock
    def read(self, fd, file):
        ret = ''
        self._walk(fd, file)
        self._open(fd)
        for buf in self._read(fd, 4096):
            ret += buf
        ret = ret.split('\n')
        self._close(fd)
        return ret

    @lock
    def create(self, fd, file, value = None):
        if type(value) not in (type([]), type(()), type(set())):
            value = [value]
        plist = file.split('/')
        path, name = '/'.join(plist[:-1]), plist[-1]
        self._walk(fd, path)
        self._create(fd, name)
        self._write(fd, '\n'.join(value))
        self._close(fd)

    @lock
    def remove(self, fd, path):
        self._walk(fd, path)
        self._open(fd)
        self._remove(fd)

    @lock
    def ls(self, fd, path):
        ret = []
        self._walk(fd, path)
        self._open(fd)
        for buf in self._read(fd, 4096):
            p9 = self.sock
            p9.setBuf(buf)
            for sz, t, d, q, m, at, mt, l, name, u, g, mod in p9._decStat(0):
                if m & DIR:
                    name += '/'
                ret.append(name)
        self._close(fd)
        return ret

    @lock
    def process(self, fd, file, func, *args, **kwargs):
        self._walk(fd, file)
        self._open(fd)
        obuf = ''
        cont = True
        for buf in self._read(fd, 4096):
            buf = obuf + buf
            lnl = buf.rfind('\n')
            for line in buf[0:lnl].split('\n'):
                if not func(line.strip(), *args, **kwargs):
                    cont = False
                    break
            if not cont:
                break
            obuf = buf[lnl + 1:]
        self._close(fd)

class Server(object):
    """
    A server interface to the protocol.
    Subclass this to provide service
    """
    verbose = 0

    def __init__(self, fd):
        self.msg = Marshal9P(fd)

    def _err(self, tag, msg):
        print 'Error', msg        # XXX
        if self.verbose:
            print cmd.repr(cmd.Rerror), repr(msg)
        self.msg.send(cmd.Rerror, tag, msg)

    def rpc(self):
        """
        Process a single RPC message.
        Return -1 on error.
        """
        type, tag, vals = self.msg.recv()

        name = "_srv" + cmd.repr(type)
        if self.verbose:
            print cmd.repr(type), repr(vals)
        if hasattr(self, name):
            func = getattr(self, name)
            try:
                rvals = func(type, tag, vals)
            except ServError, e:
                self._err(tag, e.args[0])
                return 1                    # nonfatal
            if self.verbose:
                print cmd.repr(type+1), repr(rvals)
            self.msg.send(type + 1, tag, *rvals)
        else:
            return self._err(tag, "Unhandled message: %s" % cmd.repr(type))
        return 1

    def serve(self):
        while self.rpc():
            pass

