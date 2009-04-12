import py9
import subprocess
import os
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=50

log.debug('creating new instance of client')
client = py9.Client('unix!/tmp/ns.dcurtis.:0/wmii')

def getctl(name):
    global client
    for line in client.readln_iter('/ctl'):
        if line.startswith(name):
            return line.split()[1:]

def setctl(name, value):
    global client
    client.write('/ctl',' '.join((name,value)))

def normcolors():
    return getctl('normcolors')

def setFg():
    pass

_proglist = None
def rehash():
    global proglist

    proc = subprocess.Popen("dmenu_path", stdout=subprocess.PIPE)
    _proglist = []
    for prog in proc.stdout:
        _proglist.append(prog.strip())

def program_menu():
    global _proglist
    if _proglist is None:
        rehash()

    prog = menu('cmd', _proglist)

    if prog:
        pid = subprocess.Popen(prog).pid
        log.debug("program %s started with pid %d..." % (prog, pid))


def menu(prompt, entries):
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

keybindings = {}
def key_event(key):
    log.debug('key event: %s' % key)

events = {
        'Key': [key_event]
        }
def process_event(event):
    log.debug('processing event %s' % event.split())
    edata = event.split()
    event = edata[0]
    rest = edata[1:]

    for handler in _events.get(event, []):
        handler(*rest)

def mainloop():
    global client

    for event in client.readln_iter('/event'):
        process_event(event)
