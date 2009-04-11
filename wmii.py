import py9
import subprocess
import os
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=50


class Wmii:
    __slots__=['_client', '_proglist', 'keybindings', 'events']

    def __init__(self):
        self.events = {
                'Key': [self.key_event]
                }
        self.keybindings = {}
        self._proglist = None
        self._client = None

    def getctl(self, name):
        for line in self.client.readln_iter('/ctl'):
            if line.startswith(name):
                return line.split()[1:]

    def setctl(self, name, value):
        self.client.write('/ctl',' '.join((name,value)))

    def normcolors(self):
        return self.getctl('normcolors')

    def setFg(self):
        pass

    def rehash(self):
        proc = subprocess.Popen("dmenu_path", stdout=subprocess.PIPE)
        self._proglist = []
        for prog in proc.stdout:
            self._proglist.append(prog.strip())

    def program_menu(self):
        if self._proglist is None:
            self.rehash()

        prog = self.menu('cmd', self._proglist)

        if prog:
            pid = subprocess.Popen(prog).pid
            log.debug("program %s started with pid %d..." % (prog, pid))


    def menu(self, prompt, entries):
        histfn = os.path.join(HOME,'history.%s' % prompt)
        cmd = ['wimenu', '-h', histfn]

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        for entry in entries:
            proc.stdin.write(entry)
            proc.stdin.write('\n')
        proc.stdin.close()

        out = proc.stdout.read().strip()

        history = []
        histfile = open(histfn,'r+')
        for h in histfile:
            history.append(h.strip())
        history.append(out)

        histfile.seek(0)
        for h in history[-HISTORYSIZE:]:
            histfile.write(h)
            histfile.write('\n')

        histfile.close()

        return out

    def key_event(self, key):
        log.debug('key event: %s' % key)

    def process_event(self, event):
        log.debug('processing event %s' % event.split())
        edata = event.split()
        event = edata[0]
        rest = edata[1:]

        for handler in self._events.get(event, []):
            handler(*rest)

    def _getclient(self):
        if self._client is None:
            log.debug('creating new instance of client')
            self._client = py9.Client('unix!/tmp/ns.dcurtis.:0/wmii')

        return self._client

    client = property(fget=_getclient)

    def mainloop(self):
        client = self.client

        for event in cli.readln_iter('/event'):
            process_event(event)
