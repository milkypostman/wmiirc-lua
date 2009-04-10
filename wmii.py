import py9
import subprocess
import os
import logging
log = logging.getLogger('wmii')

client = None
#__state__ = {}
#def __new__(cls):
#    self = super(Wmii, cls).__new__()
#    self.__dict__ = cls.__stat__
#    return self

def getctl(name):
    for line in client.readln_iter('/ctl'):
        if line.startswith(name):
            return line.split()[1:]

def setctl(name, value):
    client.write('/ctl',' '.join((name,value)))

def normcolors():
    return getctl('normcolors')

def setFg():
    pass

def menu(prompt, entries):
    cmd = ['wimenu']
    tmp = os.tempnam()
    tmpfile = open(tmp, 'wb')

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    for entry in entries:
        proc.stdin.write(entry)
        proc.stdin.write('\n')

    proc.stdin.close()

    out = proc.stdout.read().strip()

    return out


keybindings = {}

def key_event(key):
    log.debug('key event: %s' % key)

events = {}
events['Key'] = [
    key_event
]
def process_event(event):
    global events
    log.debug('processing event %s' % event.split())
    edata = event.split()
    event = edata[0]
    rest = edata[1:]

    for handler in events.get(event, []):
        handler(*rest)

def mainloop():
    global client
    if not client:
        log.debug('creating new instance of client')
        client = py9.Client('unix!/tmp/ns.dcurtis.:0/wmii')

    for event in client.readln_iter('/event'):
        process_event(event)
