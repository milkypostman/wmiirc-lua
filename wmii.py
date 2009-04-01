import py9
import logging
log = logging.getLogger('WMII')

class Singleton(object):
     """ A Pythonic Singleton """
     def __new__(cls, *args, **kwargs):
         if '_inst' not in vars(cls):
             cls._inst = object.__new__(cls, *args, **kwargs)
         return cls._inst


class Wmii(Singleton):
    client = None
    def __init__(self):
        if self.client is None:
            log.debug('creating new instance of client')
            self.client = py9.Client('unix!/tmp/ns.dcurtis.:0/wmii')

    def getctl(self, name):
        for line in self.client.readln_iter('/ctl'):
            if line.startswith(name):
                return line.split()[1:]

    def setctl(self, name, value):
        self.client.write('/ctl',' '.join((name,value)))

    def normcolors(self):
        return self.getctl('normcolors')

    def setFg():
        pass



