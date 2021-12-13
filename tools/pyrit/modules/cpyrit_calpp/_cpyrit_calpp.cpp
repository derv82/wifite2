/*
#
#    Copyright 2008, 2009, 2010, 2011 Artur Kornacki, hazeman11@gmail.com, Lukas Lueg, lukas.lueg@gmail.com
#
#    This file is part of Pyrit.
#
#    Pyrit is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Pyrit is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pyrit.  If not, see <http://www.gnu.org/licenses/>.
#
#    Additional permission under GNU GPL version 3 section 7
#
#    If you modify this Program, or any covered work, by linking or
#    combining it with the OpenSSL project's "OpenSSL" library (or a
#    modified version of that library), containing parts covered by
#    the terms of OpenSSL/SSLeay license, the licensors of this
#    Program grant you additional permission to convey the resulting
#    work. Corresponding Source for a non-source form of such a
#    combination shall include the source code for the parts of the
#    OpenSSL library used as well as that of the covered work.
*/

//#define __DEBUG_PYRIT_PREPROCESS_PERFORMANCE

#include <Python.h>
#include <structmember.h>
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <cal/cal.hpp>
#include <iostream>
#include <boost/array.hpp>
#include <boost/cstdint.hpp>

#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
  #include <boost/date_time/posix_time/posix_time.hpp>
  #include <boost/format.hpp>
#endif

#include "_cpyrit_calpp.h"

#define _offsetof( type, field ) ( ((uint8_t*)(&((type*)&calDevCount)->field)) - (uint8_t*)&calDevCount )

#define BUFFER_SIZE 2

std::string calpp_create_pmk_kernel( cal::Device& device );

struct WorkItem
{
    boost::array<cal::Image2D,5> g_in;
    boost::array<cal::Image2D,2> g_out;

    cal::Event                   event;

    gpu_inbuffer                 *in;
    gpu_outbuffer                *out;

    int                          size;

#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
    boost::posix_time::ptime     start_time;
#endif

    WorkItem() : g_in(), g_out(), event(), in(NULL), out(NULL), size(0)
    {
    }

    WorkItem&
    operator=( const WorkItem& v )
    {
        in     = v.in;
        out    = v.out;
        g_in   = v.g_in;
        g_out  = v.g_out;
        event  = v.event;
        size   = v.size;
#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
        start_time = v.start_time;
#endif

        return *this;
    }
};

class ThreadUnlocker
{
protected:
    PyThreadState *_save;

public:
    ThreadUnlocker() { Py_UNBLOCK_THREADS }
    ~ThreadUnlocker() { Py_BLOCK_THREADS }
};

extern "C" typedef struct
{
    PyObject_HEAD
    int               dev_idx;
    PyObject*         dev_name;

    cal::Context      dev_context;
    cal::Program      dev_prog;
    cal::Kernel       dev_kernel;
    cal::CommandQueue dev_queue;
    int               dev_maxheight;

    boost::array<WorkItem,BUFFER_SIZE> buffer;
    int                                work_count;

#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
    boost::uint64_t                    exec_time;
    boost::uint64_t                    item_count;
    boost::posix_time::ptime           last_time;
#endif
} CALDevice;

static int calDevCount;
static cal::Context calContext;

static int
caldev_init( CALDevice *self, PyObject *args, PyObject *kwds )
{
    int dev_idx;

    self->dev_idx  = 0;
    self->dev_name = NULL;
    new(&self->dev_context) cal::Context();
    new(&self->dev_prog) cal::Program();
    new(&self->dev_kernel) cal::Kernel();
    new(&self->dev_queue) cal::CommandQueue();
    new(&self->buffer) boost::array<WorkItem,BUFFER_SIZE>();
    self->work_count = 0;
#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
    self->exec_time = 0;
    self->item_count = 0;
    new(&self->last_time) boost::posix_time::ptime();
#endif

    if (!PyArg_ParseTuple(args, "i:CALDevice", &dev_idx))
        return -1;

    if (dev_idx < 0 || dev_idx > calDevCount-1)
    {
        PyErr_SetString(PyExc_SystemError, "Invalid device number");
        return -1;
    }

    try {
        cal::Device device;
        std::string source;

        device = calContext.getInfo<CAL_CONTEXT_DEVICES>()[dev_idx];

        self->dev_context = cal::Context(device);

        source = calpp_create_pmk_kernel(device);

        //std::cout << source;

        self->dev_idx  = dev_idx;
        self->dev_name = PyString_FromString(device.getInfo<CAL_DEVICE_NAME>().c_str());

        try {
            self->dev_prog = cal::Program(self->dev_context, source.c_str(), source.length() );
            self->dev_prog.build(device);
            //self->dev_prog.disassemble(std::cout);
        } catch( cal::Error& e ) {
            PyErr_SetString(PyExc_SystemError, "CAL++ kernel compilation error");
            return -1;
        }

        self->dev_kernel = cal::Kernel(self->dev_prog, "main");
        self->dev_kernel.setArgBind(0, "i0");
        self->dev_kernel.setArgBind(1, "i1");
        self->dev_kernel.setArgBind(2, "i2");
        self->dev_kernel.setArgBind(3, "i3");
        self->dev_kernel.setArgBind(4, "i4");
        self->dev_kernel.setArgBind(5, "o0");
        self->dev_kernel.setArgBind(6, "o1");

        self->dev_queue = cal::CommandQueue(self->dev_context,device);
        self->dev_maxheight = device.getInfo<CAL_DEVICE_MAXRESOURCE2DHEIGHT>();
    } catch( cal::Error& e ) {
        PyErr_SetString(PyExc_SystemError, e.what());
        return -1;
    }

    return 0;
}

static void
caldev_dealloc(CALDevice *self)
{
    for(int i=0;i<BUFFER_SIZE;i++) {
        PyMem_Free(self->buffer[i].in);
        PyMem_Free(self->buffer[i].out);
    }

    self->buffer.~array();
    self->dev_queue.~CommandQueue();
    self->dev_kernel.~Kernel();
    self->dev_prog.~Program();
    self->dev_context.~Context();

    Py_XDECREF(self->dev_name);
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
cpyrit_listDevices(PyObject* self, PyObject* args)
{
    int i;
    PyObject* result;
    std::vector<cal::Device> devices;

    devices = calContext.getInfo<CAL_CONTEXT_DEVICES>();

    result = PyTuple_New(calDevCount);
    for (i = 0; i < calDevCount; i++)
        PyTuple_SetItem(result, i, Py_BuildValue("(s)", devices[i].getInfo<CAL_DEVICE_NAME>().c_str()));

    return result;
}

static void
copy_gpu_inbuffer(CALDevice* self, const gpu_inbuffer* inbuffer, boost::array<cal::Image2D,5>& in, int size )
{
    CALuint  pitch;
    uint32_t *p[5];
    int      i;

    for(i = 0; i < 5; i++) 
        p[i] = (uint32_t*)self->dev_queue.mapMemObject(in[i],pitch);

    for(i = 0; i < size; i++)
    {
        std::memcpy(p[0], &inbuffer[i].ctx_ipad.h0, 4*4);
        std::memcpy(p[1], &inbuffer[i].ctx_ipad.h4, 4*4);
        std::memcpy(p[2], &inbuffer[i].ctx_opad.h3, 4*4);
        std::memcpy(p[3], &inbuffer[i].e1.h2, 4*4);
        std::memcpy(p[4], &inbuffer[i].e2.h1, 4*4);

        p[0] += 4; p[1] += 4;
        p[2] += 4; p[3] += 4;
        p[4] += 4;
    }

    for(i = 0; i < 5; i++) 
        self->dev_queue.unmapMemObject(in[i]);
}

static void
copy_gpu_outbuffer(CALDevice* self, gpu_outbuffer* outbuffer, boost::array<cal::Image2D,2>& out, int size)
{
    CALuint  pitch;
    uint32_t *p[2];
    int      i;

    for(i = 0; i < 2; i++) 
        p[i] = (uint32_t*)self->dev_queue.mapMemObject(out[i],pitch);

    for(i = 0; i < size; i++)
    {
        std::memcpy(&outbuffer[i].pmk1.h0, p[0], 4*4);
        std::memcpy(&outbuffer[i].pmk1.h4, p[1], 4*4);

        p[0] += 4; p[1] += 4;
    }

    for(i = 0; i < 2; i++) 
        self->dev_queue.unmapMemObject(out[i]);
}

static void 
start_kernel( CALDevice* self, int idx )
{
    int size, w, h;

    size = self->buffer[idx].size;

    h = (size + CALPP_BLOCK_WIDTH - 1) / CALPP_BLOCK_WIDTH;
    w = CALPP_BLOCK_WIDTH * ((h + self->dev_maxheight - 1) / self->dev_maxheight);
    h = (size + w - 1) / w;

    for(int i=0;i<5;i++) {
        if( !self->buffer[idx].g_in[i].isValid() || self->buffer[idx].g_in[i].getWidth()!=w || self->buffer[idx].g_in[i].getHeight()!=h ) {
            self->buffer[idx].g_in[i] = cal::Image2D(self->dev_context, w, h, CAL_FORMAT_UINT_4, 0);
        }
    }
    for(int i=0;i<2;i++) {
        if( !self->buffer[idx].g_out[i].isValid() || self->buffer[idx].g_out[i].getWidth()!=w || self->buffer[idx].g_out[i].getWidth()!=h ) {
            self->buffer[idx].g_out[i] = cal::Image2D(self->dev_context, w, h, CAL_FORMAT_UINT_4, 0);
        }
    }

    copy_gpu_inbuffer( self, self->buffer[idx].in, self->buffer[idx].g_in, size );

#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
    boost::posix_time::ptime t2 = boost::posix_time::microsec_clock::local_time();
    boost::uint64_t          tm = boost::posix_time::time_period(self->last_time,t2).length().total_microseconds();
    if( tm>1000 ) 
        std::cout << boost::format("Not fast enough data preparation for GPU: lost time %i ms\n") % (tm/1000);
    self->buffer[idx].start_time = boost::posix_time::microsec_clock::local_time();
#endif

    for(int i=0;i<5;i++) 
        self->dev_kernel.setArg(0+i, self->buffer[idx].g_in[i]);
    for(int i=0;i<2;i++) 
        self->dev_kernel.setArg(5+i, self->buffer[idx].g_out[i]);

    self->dev_queue.enqueueNDRangeKernel(self->dev_kernel, cal::NDRange(w,h), &(self->buffer[idx].event));
    self->dev_queue.flush();
    self->dev_queue.isEventDone(self->buffer[idx].event);
}

static PyObject*
cpyrit_send(CALDevice *self, PyObject *args)
{
    unsigned char essid[32+4], *passwd, pad[64], temp[32];
    int i, idx, size, essidlen, passwdlen;
    PyObject *essid_obj, *passwd_seq, *passwd_obj;
    gpu_inbuffer *c_inbuffer;
    SHA_CTX ctx_pad;

    if (!PyArg_ParseTuple(args, "OO", &essid_obj, &passwd_seq))
        return NULL;

    if( self->work_count>=BUFFER_SIZE )
        Py_RETURN_FALSE;

    size = PySequence_Size(passwd_seq);
    if( size<=0 ) 
    {
        PyErr_SetString(PyExc_SystemError, "send: not enough data");
        return NULL;
    }

    passwd_seq = PyObject_GetIter(passwd_seq);
    if (!passwd_seq)
        return NULL;

    essidlen = PyString_Size(essid_obj);
    if (essidlen < 1 || essidlen > 32)
    {
        Py_DECREF(passwd_seq);
        PyErr_SetString(PyExc_ValueError, "The ESSID must be a string between 1 and 32 characters");
        return NULL;
    }
    memcpy(essid, PyString_AsString(essid_obj), essidlen);
    memset(essid + essidlen, 0, sizeof(essid) - essidlen);

    self->buffer[self->work_count].in   = (gpu_inbuffer*) PyMem_Realloc( self->buffer[self->work_count].in, sizeof(gpu_inbuffer)*size );
    self->buffer[self->work_count].out  = (gpu_outbuffer*) PyMem_Realloc( self->buffer[self->work_count].out, sizeof(gpu_outbuffer)*size );
    self->buffer[self->work_count].size = size;

    if( !self->buffer[self->work_count].in || !self->buffer[self->work_count].out ) 
    {
        Py_DECREF(passwd_seq);
        PyErr_NoMemory();
        return NULL;
    }

    idx  = 0;
    c_inbuffer = self->buffer[self->work_count].in;
    while ((passwd_obj = PyIter_Next(passwd_seq)))
    {
        if( idx>=size ) 
        {
            Py_DECREF(passwd_obj);
            Py_DECREF(passwd_seq);
            PyErr_SetString(PyExc_ValueError, "Invalid sequence length");
            return NULL;
        }

        passwd = (unsigned char*)PyString_AsString(passwd_obj);
        passwdlen = PyString_Size(passwd_obj);
        if (passwd == NULL || passwdlen < 8 || passwdlen > 63)
        {
            Py_DECREF(passwd_obj);
            Py_DECREF(passwd_seq);
            PyErr_SetString(PyExc_ValueError, "All passwords must be strings between 8 and 63 characters");
            return NULL;
        }

        memcpy(pad, passwd, passwdlen);
        memset(pad + passwdlen, 0, sizeof(pad) - passwdlen);
        for (i = 0; i < 16; i++)
            ((unsigned int*)pad)[i] ^= 0x36363636;
        SHA1_Init(&ctx_pad);
        SHA1_Update(&ctx_pad, pad, sizeof(pad));
        CPY_DEVCTX(ctx_pad, c_inbuffer[idx].ctx_ipad);
        for (i = 0; i < 16; i++)
            ((unsigned int*)pad)[i] ^= 0x6A6A6A6A;
        SHA1_Init(&ctx_pad);
        SHA1_Update(&ctx_pad, pad, sizeof(pad));
        CPY_DEVCTX(ctx_pad, c_inbuffer[idx].ctx_opad);

        essid[essidlen + 4 - 1] = '\1';
        HMAC(EVP_sha1(), passwd, passwdlen, essid, essidlen + 4, temp, NULL);
        GET_BE(c_inbuffer[idx].e1.h0, temp, 0);
        GET_BE(c_inbuffer[idx].e1.h1, temp, 4);
        GET_BE(c_inbuffer[idx].e1.h2, temp, 8);
        GET_BE(c_inbuffer[idx].e1.h3, temp, 12);
        GET_BE(c_inbuffer[idx].e1.h4, temp, 16);

        essid[essidlen + 4 - 1] = '\2';
        HMAC(EVP_sha1(), passwd, passwdlen, essid, essidlen + 4, temp, NULL);
        GET_BE(c_inbuffer[idx].e2.h0, temp, 0);
        GET_BE(c_inbuffer[idx].e2.h1, temp, 4);
        GET_BE(c_inbuffer[idx].e2.h2, temp, 8);
        GET_BE(c_inbuffer[idx].e2.h3, temp, 12);
        GET_BE(c_inbuffer[idx].e2.h4, temp, 16);

        Py_DECREF(passwd_obj);
        idx++;
    }
    Py_DECREF(passwd_seq);

    self->work_count++;
    if( self->work_count==1 ) 
    {
        try {
            ThreadUnlocker unlock;
            start_kernel(self,0);
        } catch( cal::Error& e ) {
            PyErr_SetString(PyExc_SystemError, e.what());
            return NULL;
        }
    }

    Py_RETURN_TRUE;
}

static PyObject*
cpyrit_receive(CALDevice *self, PyObject *args)
{
    unsigned char temp[32];
    PyObject      *result;
    gpu_outbuffer *c_outbuffer;
    int           wait_for_data,event_done;

    if (!PyArg_ParseTuple(args, "i", &wait_for_data))
        return NULL;

    if( self->work_count<=0 ) 
        Py_RETURN_NONE;

    try {
        ThreadUnlocker unlock;
#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
        boost::posix_time::ptime t1 = boost::posix_time::microsec_clock::local_time();
#endif
        if( wait_for_data ) 
            self->dev_queue.waitForEvent(self->buffer[0].event);
        event_done = self->dev_queue.isEventDone(self->buffer[0].event);

        if( event_done ) 
        {
#ifdef __DEBUG_PYRIT_PREPROCESS_PERFORMANCE
            boost::posix_time::ptime t2 = boost::posix_time::microsec_clock::local_time();
            if( boost::posix_time::time_period(t1,t2).length().total_microseconds()>=200000 ) 
            {
                // cpu was waiting >=0.2s for gpu 
                // data were prepared fast enough and cpu had spare time
                self->item_count += self->buffer[0].size;
                self->exec_time  += boost::posix_time::time_period(self->buffer[0].start_time,t2).length().total_microseconds();
            } 
            else 
            {
                // cpu was waiting <0.2s for gpu 
                // or most probable case gpu was waiting for cpu
                if( self->item_count>0 ) 
                {
                    boost::int64_t  perf = (1000*self->exec_time)/self->item_count;
                    boost::int64_t  lost_time = boost::posix_time::time_period(self->buffer[0].start_time,t2).length().total_microseconds() -
                                                perf*self->buffer[0].size/1000;
                    std::cout << boost::format("Not fast enough data preparation for GPU: estimated lost time %i ms\n") % (lost_time/1000);
                } 
                else 
                    std::cout << "Not fast enough data preparation for GPU: unknown lost time\n";
            } 
            self->last_time = t2;
#endif
            copy_gpu_outbuffer( self, self->buffer[0].out, self->buffer[0].g_out, self->buffer[0].size );
            if( self->work_count>1 ) start_kernel(self,1);
        }
    } catch( cal::Error& e ) {
        PyErr_SetString(PyExc_SystemError, e.what());
        return NULL;
    }

    if( event_done ) 
    {
        c_outbuffer = self->buffer[0].out;

        result = PyTuple_New(self->buffer[0].size);
        for (int i = 0; i < self->buffer[0].size; i++)
        {
            PUT_BE(c_outbuffer[i].pmk1.h0, temp, 0); PUT_BE(c_outbuffer[i].pmk1.h1, temp, 4);
            PUT_BE(c_outbuffer[i].pmk1.h2, temp, 8); PUT_BE(c_outbuffer[i].pmk1.h3, temp, 12); 
            PUT_BE(c_outbuffer[i].pmk1.h4, temp, 16);PUT_BE(c_outbuffer[i].pmk2.h0, temp, 20); 
            PUT_BE(c_outbuffer[i].pmk2.h1, temp, 24);PUT_BE(c_outbuffer[i].pmk2.h2, temp, 28); 
            PyTuple_SetItem(result, i, PyString_FromStringAndSize((char*)temp, 32));
        }

        WorkItem tmp = self->buffer[0];
        for(int i=0;i<(BUFFER_SIZE-1);i++) 
            self->buffer[i] = self->buffer[i+1];
        self->buffer[BUFFER_SIZE-1] = tmp;
        self->work_count--;

        return result;
    }

    Py_RETURN_NONE;
}

static PyObject*
cpyrit_sizes(CALDevice *self, PyObject *args)
{
    cal::Device device;
    int         min_size,avg_size,max_size,div_size;
    int         target,simd,avg_speed,max_speed;

    device = self->dev_context.getInfo<CAL_CONTEXT_DEVICES>()[0];
    target = device.getInfo<CAL_DEVICE_TARGET>();
    simd   = device.getInfo<CAL_DEVICE_NUMBEROFSIMD>();

    if( target>=CAL_TARGET_CYPRESS )
    {
        avg_speed = 3500;
        max_speed = 5000;
    } 
    else
    {
        avg_speed = 2000;
        max_speed = 3000;
    }

    div_size = 8*64*2*simd; // 8 threads per simd * thread size * 2 elements per thread * number of simds
    min_size = 4096;
    avg_size = div_size*((1*avg_speed*simd + div_size - 1)/div_size);
    max_size = div_size*((3*max_speed*simd + div_size - 1)/div_size);

    return Py_BuildValue("iiii",min_size,avg_size,max_size,div_size);
}

static PyMemberDef CALDevice_members[] =
{
    {(char*)"deviceName", T_OBJECT, _offsetof(CALDevice, dev_name), 0},
    {NULL}
};

static PyMethodDef CALDevice_methods[] =
{
    {"send", (PyCFunction)cpyrit_send, METH_VARARGS, "Enqueue calculation of PMKs from ESSID and iterable of strings."},
    {"receive", (PyCFunction)cpyrit_receive, METH_VARARGS, "Gather result of calculation PMKs from ESSID and iterable of strings."},
    {"workSizes", (PyCFunction)cpyrit_sizes, METH_VARARGS, "Return tuple with core min,avg,max,div sizes."},
    {NULL, NULL}
};

static PyTypeObject CALDevice_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_calpp.CALDevice",  /*tp_name*/
    sizeof(CALDevice),          /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    (destructor)caldev_dealloc, /*tp_dealloc*/
    0,                          /*tp_print*/
    0,                          /*tp_getattr*/
    0,                          /*tp_setattr*/
    0,                          /*tp_compare*/
    0,                          /*tp_repr*/
    0,                          /*tp_as_number*/
    0,                          /*tp_as_sequence*/
    0,                          /*tp_as_mapping*/
    0,                          /*tp_hash*/
    0,                          /*tp_call*/
    0,                          /*tp_str*/
    0,                          /*tp_getattro*/
    0,                          /*tp_setattro*/
    0,                          /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT          /*tp_flags*/
     | Py_TPFLAGS_BASETYPE,
    0,                          /*tp_doc*/
    0,                          /*tp_traverse*/
    0,                          /*tp_clear*/
    0,                          /*tp_richcompare*/
    0,                          /*tp_weaklistoffset*/
    0,                          /*tp_iter*/
    0,                          /*tp_iternext*/
    CALDevice_methods,          /*tp_methods*/
    CALDevice_members,          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)caldev_init,      /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMethodDef CPyritCAL_methods[] = {
    {"listDevices", cpyrit_listDevices, METH_NOARGS, "Returns a tuple of tuples, each describing a CAL++ capable device."},
    {NULL, NULL, 0, NULL}
};

extern "C" PyMODINIT_FUNC init_cpyrit_calpp(void)
{
    PyObject *m;

    cal::Init();

    calContext = cal::Context(CAL_DEVICE_TYPE_GPU);
    calDevCount = calContext.getInfo<CAL_CONTEXT_DEVICES>().size();

    CALDevice_type.tp_getattro = PyObject_GenericGetAttr;
    CALDevice_type.tp_setattro = PyObject_GenericSetAttr;
    CALDevice_type.tp_alloc  = PyType_GenericAlloc;
    CALDevice_type.tp_new = PyType_GenericNew;
    CALDevice_type.tp_free = _PyObject_Del;
    if (PyType_Ready(&CALDevice_type) < 0)
        return;

    m = Py_InitModule("_cpyrit_calpp", CPyritCAL_methods);

    Py_INCREF(&CALDevice_type);
    PyModule_AddObject(m, "CALDevice", (PyObject*)&CALDevice_type);
    PyModule_AddStringConstant(m, "VERSION", VERSION);
}
