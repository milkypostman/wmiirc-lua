import time
import py9
reload(py9)

c = py9.Client('unix!/tmp/ns.dcurtis.:0/wmii')

print c.ls('/')

f = c.open('/ctl')
for l in f:
    print l

f = c.open('/event')

start = time.time()
for i in f.readln_iter(3):
    print i
stop = time.time()
print stop-start

