import pyxp

w = pyxp.Wmii("unix!/tmp/ns.dcurtis.:0/wmii")

print w.ls('/')
print w.read('/ctl')

