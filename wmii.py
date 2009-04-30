import pyxp
import subprocess
import time
import re
import select
import os
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=5

#log.debug('creating new instance of client')
client = pyxp.Wmii('unix!/tmp/ns.dcurtis.:0/wmii')

tags = { 'main' : 1,
        'www' : 2,
        }

_tagidx = {}
_tagname = {}

_tagidxname = ()

def getctl(name):
    global client
    for line in client.read('/ctl').split('\n'):
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

    if out:
        history = []
        histfile = open(histfn,'a+')
        for h in histfile:
            history.append(h.strip())
        history.append(out)

        histfile = open(histfn,'w+')
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
        'Mod1-l':lambda _: client.write('/tag/sel/ctl', 'select right'),
        'Mod1-comma':lambda _: view_offset(-1),
        'Mod1-period':lambda _: view_offset(1),
        'Mod4-#':lambda key: set_tag_idx(int(key[key.find('-')+1:])),
        }

def updatekeys():
    global keybindings
    global client
    numre = re.compile('(.*-)#')

    keys = []
    for key in keybindings:
        match = numre.match(key)
        if match:
            pfx = match.group(1)
            keys.extend([pfx+str(i) for i in range(10)])

        keys.append(key)

    client.write('/keys', '\n'.join(keys))


def view_offset(ofs):
    global client
    global _tagidx

    view = getctl('view')[0]
    idx = _tagidxname.index( (_tagidx[view], view) )

    idx,view = _tagidxname[(idx + ofs) % len(_tagidxname)]

    setctl('view', view)


def key_event(key):
    #log.debug('key event: %s' % key)
    func = keybindings.get(key, None)
    if hasattr(func, '__call__'):
        func(key)
    else:
        numkey = re.sub('-\d*', '-#', key)
        func = keybindings.get(numkey, None)
        if hasattr(func, '__call__'):
            func(key)

def set_tag_idx(idx):
    if idx in _tagname:
        setctl('view', _tagname[idx])

def focus_tag(tag):
    print tag

def unfocus_tag(tag):
    print tag

events = {
        'Key': [key_event],
        'FocusTag': [focus_tag],
        'UnfocusTag': [unfocus_tag],
        }

def process_event(event):
    log.debug('processing event %s' % event.split())
    edata = event.split()
    event = edata[0]
    rest = edata[1:]

    for handler in events.get(event, []):
        handler(*rest)

def inittags():
    global _tagidx, _tagname, _tagidxname
    global client

    for tag, idx in tags.iteritems():
        _tagidx[tag] = idx
        _tagname[idx] = tag

    idx = 0
    for tag in filter(lambda n: n != 'sel', client.ls('/tag')):
        if tag in _tagidx:
            continue

        while idx in _tagname:
            idx += 1

        _tagidx[tag] = idx
        _tagname[idx] = tag

        idx += 1

    _tagidxname = sorted(_tagname.iteritems())


def mainloop():
    global client

    inittags()

    updatekeys()

    eventproc = subprocess.Popen(("wmiir","read","/event"), stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    while True:

        # load plugins
        # set the timeout to the shortest plugin event
        #timeout = 0
        #print type(proc.stdout)

        timeout = 5
        while True:
            s = time.time()
            rdy, _, _ = select.select([eventproc.stdout], [], [], timeout)
            if not rdy:
                break
            e = time.time()

            line = rdy[0].readline()
            process_event(line)

            timeout -= e-s


if __name__ == '__main__':
    mainloop()
