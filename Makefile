all:
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O3 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.6 -c pyxp.c -o pyxp.o
	gcc -pthread -shared pyxp.o -L/usr/lib -lpython2.6 -lixp -o pyxp.so
