import pyxp
import subprocess
import os
#import logging
#logging.basicConfig(level=logging.DEBUG)
#log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=50

#log.debug('creating new instance of client')
client = pyxp.Wmii('unix!/tmp/ns.dcurtis.:0/wmii')

tags = []

def getctl(name):
    global client
    for line in client.read('/ctl'):
        if line.startswith(name):
            return line.split()[1:]

def setctl(name, value):
    global client
    client.write('/ctl',' '.join((name,value)))

def normcolors():
    return getctl('normcolors')

def setFg():
    pass

proglist = None
def rehash():
    global proglist

    proc = subprocess.Popen("dmenu_path", stdout=subprocess.PIPE)
    proglist = []
    for prog in proc.stdout:
        proglist.append(prog.strip())

def program_menu():
    global proglist
    if proglist is None:
        rehash()

    prog = menu('cmd', proglist)

    if prog:
        pid = subprocess.Popen(prog).pid
        #log.debug("program %s started with pid %d..." % (prog, pid))

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

keybindings = {
        'Mod1-p':lambda _: program_menu(),
        'Mod1-j':lambda _: client.write('/tag/sel/ctl', 'select down'),
        'Mod1-k':lambda _: client.write('/tag/sel/ctl', 'select up'),
        'Mod1-h':lambda _: client.write('/tag/sel/ctl', 'select left'),
        'Mod1-l':lambda _: client.write('/tag/sel/ctl', 'select right'),
        'Mod1-comma':lambda _: view_offset(-1),
        'Mod1-period':lambda _: view_offset(1),
        }

def updatekeys():
    global keybindings
    global client
    client.write('/keys', '\n'.join(keybindings.keys()))


def view_offset(ofs):
    global client
    global tags

    idx = tags.index(getctl('view')[0])
    idx = (idx+ofs) % len(tags)
    setctl('view', tags[idx])

def key_event(key):
    #log.debug('key event: %s' % key)
    func = keybindings.get(key, None)
    if hasattr(func, '__call__'):
        func(key)

events = {
        'Key': [key_event]
        }
def process_event(event):
    #log.debug('processing event %s' % event.split())
    edata = event.split()
    event = edata[0]
    rest = edata[1:]

    for handler in events.get(event, []):
        handler(*rest)

def inittags():
    global tags

    for tag in filter(lambda n: n != 'sel', client.ls('/tag')):
        tags.append(tag)


def mainloop():
    global client

    inittags()

    updatekeys()

    while True:
        # load plugins
        # set the timeout to the shortest plugin event
        timeout = None
        break

        # process plugin timers


if __name__ == '__main__':
    mainloop()
