#include <Python.h>

static PyObject * pyxp_test(PyObject *self, PyObject *args)
{
    return Py_BuildValue("s", "test");
}

static PyMethodDef PYXPMethods[] = {
    {"test", pyxp_test, METH_VARARGS, "Test this module"},
    {NULL, NULL, 0, NULL},
};

PyMODINIT_FUNC
initpyxp(void)
{
    (void) Py_InitModule("pyxp", PYXPMethods);
}
