from distutils.core import setup, Extension

pyxpmodule = Extension('pyxp', sources=['pyxp.c'])

setup(name = 'PYXP',
        version = '0.1',
        description = 'Python extension for libixp',
        ext_modules = [pyxpmodule])
