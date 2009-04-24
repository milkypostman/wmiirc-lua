#include <Python.h>
#include "structmember.h"

#include <ixp.h>

typedef struct {
    PyObject_HEAD
    PyObject *address;
    IxpClient *cli;
} Wmii;

static int Wmii_init(Wmii *self, PyObject *args, PyObject *kwds);
static void Wmii_dealloc(Wmii *self);
static PyObject *Wmii_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static PyMemberDef Wmii_members[] = {
    { "address", T_OBJECT_EX, offsetof(Wmii, address), 0, "client address" },
    {NULL}
};

static PyTypeObject WmiiType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pyxp.Wmii",               /*tp_name*/
    sizeof(Wmii),         /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Wmii_dealloc,  /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "WMII objects",            /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    0,                         /* tp_methods */
    Wmii_members,              /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Wmii_init,       /* tp_init */
    0,                         /* tp_alloc */
    Wmii_new,                  /* tp_new */
};

PyMODINIT_FUNC
initpyxp(void)
{
    PyObject *m;

    if (PyType_Ready(&WmiiType) < 0)
        return;

    m =  Py_InitModule3("pyxp", NULL, "Python libixp module");

    if (m==NULL)
        return;

    Py_INCREF(&WmiiType);
    PyModule_AddObject(m, "Wmii", (PyObject *)&WmiiType);
}

static PyObject *
Wmii_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Wmii *self;

    self = (Wmii *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->cli = NULL;
        self->address = NULL;
    }
    else
    {
        printf("Error creating object!\n");
    }
    printf("self->cli: %d\n", self->cli);

    return (PyObject *)self;
}

static int
Wmii_init(Wmii *self, PyObject *args, PyObject *kwds)
{
    PyObject *address, *tmp;
    const char *adr;

    if (!PyArg_ParseTuple(args, "S", &address))
        return -1;

    if(address) {
        tmp = self->address;
        Py_INCREF(address);
        self->address = address;

        adr = PyString_AsString(address);

        if (self->cli) {
            ixp_unmount(self->cli);
        }

        printf("** Wmii([%s]) **\n", adr);
        self->cli = ixp_mount(adr);
        printf("self->cli: %d\n", self->cli);

        Py_XDECREF(tmp);
    }

    return 0;
}

static void
Wmii_dealloc(Wmii *self)
{
    if (self->cli)
    {
        ixp_unmount(self->cli);
    }
    Py_XDECREF(self->address);
    self->ob_type->tp_free((PyObject*)self);
}
