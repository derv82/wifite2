/*
#
#    Copyright 2008-2011 Lukas Lueg, lukas.lueg@gmail.com
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
#
#    If you modify this Program, or any covered work, by linking or
#    combining it with any library or libraries implementing the
#    Khronos Group OpenCL Standard v1.0 or later (or modified
#    versions of those libraries), containing parts covered by the
#    terms of the licenses of their respective copyright owners,
#    the licensors of this Program grant you additional permission
#    to convey the resulting work.
*/

#include <Python.h>
#include <structmember.h>
#ifdef __APPLE__
    #include <cl.h>
#else
    #include <CL/cl.h>
#endif /* __APPLE__ */
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <zlib.h>
#include "_cpyrit_opencl.h"

// Created by setup.py
#include "_cpyrit_oclkernel.cl.h"

static PyTypeObject OpenCLPlatform_type;
static PyTypeObject OpenCLDevice_type;

typedef struct
{
    PyObject_HEAD
    PyObject* platform_name;
    PyObject* platform_vendor;
    PyObject* numDevices;
} OpenCLPlatform;

typedef struct
{
    PyObject_HEAD
    cl_device_id device;
    PyObject* dev_name;
    PyObject* dev_type;
    PyObject* dev_maxworksize;
    cl_context dev_ctx;
    cl_program dev_prog;
    cl_kernel dev_kernel;
    cl_command_queue dev_queue;
    size_t dev_workgroupsize;
} OpenCLDevice;

cl_platform_id *platforms;
cl_uint num_platforms;

unsigned char *oclkernel_program;

static char*
getCLresultMsg(cl_int error)
{
    switch (error)
    {
        // HC SVNT DRACONES
        case CL_SUCCESS: return "CL_SUCCESS";
        case CL_DEVICE_NOT_FOUND: return "CL_DEVICE_NOT_FOUND";
        case CL_DEVICE_NOT_AVAILABLE: return "CL_DEVICE_NOT_AVAILABLE";
        case CL_COMPILER_NOT_AVAILABLE: return "CL_COMPILER_NOT_AVAILABLE";
        case CL_MEM_OBJECT_ALLOCATION_FAILURE: return "CL_MEM_OBJECT_ALLOCATION_FAILURE";
        case CL_OUT_OF_RESOURCES: return "CL_OUT_OF_RESOURCES";
        case CL_OUT_OF_HOST_MEMORY: return "CL_OUT_OF_HOST_MEMORY";
        case CL_PROFILING_INFO_NOT_AVAILABLE: return "CL_PROFILING_INFO_NOT_AVAILABLE";
        case CL_MEM_COPY_OVERLAP: return "CL_MEM_COPY_OVERLAP";
        case CL_IMAGE_FORMAT_MISMATCH: return "CL_IMAGE_FORMAT_MISMATCH";
        case CL_IMAGE_FORMAT_NOT_SUPPORTED: return "CL_IMAGE_FORMAT_NOT_SUPPORTED";
        case CL_BUILD_PROGRAM_FAILURE: return "CL_BUILD_PROGRAM_FAILURE";
        case CL_MAP_FAILURE: return "CL_MAP_FAILURE";
        case CL_INVALID_VALUE: return "CL_INVALID_VALUE";
        case CL_INVALID_DEVICE_TYPE: return "CL_INVALID_DEVICE_TYPE";
        case CL_INVALID_PLATFORM: return "CL_INVALID_PLATFORM";
        case CL_INVALID_DEVICE: return "CL_INVALID_DEVICE";
        case CL_INVALID_CONTEXT: return "CL_INVALID_CONTEXT";
        case CL_INVALID_QUEUE_PROPERTIES: return "CL_INVALID_QUEUE_PROPERTIES";
        case CL_INVALID_COMMAND_QUEUE: return "CL_INVALID_COMMAND_QUEUE";
        case CL_INVALID_HOST_PTR: return "CL_INVALID_HOST_PTR";
        case CL_INVALID_MEM_OBJECT: return "CL_INVALID_MEM_OBJECT";
        case CL_INVALID_IMAGE_FORMAT_DESCRIPTOR: return "CL_INVALID_IMAGE_FORMAT_DESCRIPTOR";
        case CL_INVALID_IMAGE_SIZE: return "CL_INVALID_IMAGE_SIZE";
        case CL_INVALID_SAMPLER: return "CL_INVALID_SAMPLER";
        case CL_INVALID_BINARY: return "CL_INVALID_BINARY";
        case CL_INVALID_BUILD_OPTIONS: return "CL_INVALID_BUILD_OPTIONS";
        case CL_INVALID_PROGRAM: return "CL_INVALID_PROGRAM";
        case CL_INVALID_PROGRAM_EXECUTABLE: return "CL_INVALID_PROGRAM_EXECUTABLE";
        case CL_INVALID_KERNEL_NAME: return "CL_INVALID_KERNEL_NAME";
        case CL_INVALID_KERNEL_DEFINITION: return "CL_INVALID_KERNEL_DEFINITION";
        case CL_INVALID_KERNEL: return "CL_INVALID_KERNEL";
        case CL_INVALID_ARG_INDEX: return "CL_INVALID_ARG_INDEX";
        case CL_INVALID_ARG_VALUE: return "CL_INVALID_ARG_VALUE";
        case CL_INVALID_ARG_SIZE: return "CL_INVALID_ARG_SIZE";
        case CL_INVALID_KERNEL_ARGS: return "CL_INVALID_KERNEL_ARGS";
        case CL_INVALID_WORK_DIMENSION: return "CL_INVALID_WORK_DIMENSION";
        case CL_INVALID_WORK_GROUP_SIZE: return "CL_INVALID_WORK_GROUP_SIZE";
        case CL_INVALID_WORK_ITEM_SIZE: return "CL_INVALID_WORK_ITEM_SIZE";
        case CL_INVALID_GLOBAL_OFFSET: return "CL_INVALID_GLOBAL_OFFSET";
        case CL_INVALID_EVENT_WAIT_LIST: return "CL_INVALID_EVENT_WAIT_LIST";
        case CL_INVALID_EVENT: return "CL_INVALID_EVENT";
        case CL_INVALID_OPERATION: return "CL_INVALID_OPERATION";
        case CL_INVALID_GL_OBJECT: return "CL_INVALID_GL_OBJECT";
        case CL_INVALID_BUFFER_SIZE: return "CL_INVALID_BUFFER_SIZE";
        case CL_INVALID_MIP_LEVEL: return "CL_INVALID_MIP_LEVEL";
        default : return "Unknown CLresult";
    }
}

static int
oclplatf_init(OpenCLPlatform *self, PyObject *args, PyObject *kwds)
{
    int platform_idx;
    cl_uint num_devices;
    cl_int err;
    char name[64];
    size_t name_size;
    
    if (!PyArg_ParseTuple(args, "i:platform_index", &platform_idx))
        return -1;
    
    if (platform_idx < 0 || platform_idx > num_platforms - 1)
    {
        PyErr_Format(PyExc_ValueError, "Platform-index out of range");
        return -1;
    }
    
    self->platform_name = NULL;
    self->platform_vendor = NULL;
    self->numDevices = NULL;
    
    err = clGetDeviceIDs(platforms[platform_idx], CL_DEVICE_TYPE_ALL, 0, NULL, &num_devices);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to enumerate devices on this platform (%s)", getCLresultMsg(err));
        return -1;
    }
    
    self->numDevices = PyInt_FromLong((long)num_devices);
    if (!self->numDevices)
    {
        PyErr_NoMemory();
        return -1;
    }
    
    err = clGetPlatformInfo(platforms[platform_idx], CL_PLATFORM_NAME, sizeof(name), &name, &name_size);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get Platform-Name (%s)", getCLresultMsg(err));
        return -1;
    }
    self->platform_name = PyString_FromStringAndSize(name, name_size-1);
    if (!self->platform_name)
    {
        PyErr_NoMemory();
        return -1;
    }
    
    err = clGetPlatformInfo(platforms[platform_idx], CL_PLATFORM_VENDOR, sizeof(name), &name, &name_size);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get Platform-Vendor (%s)", getCLresultMsg(err));
        return -1;
    }
    self->platform_vendor = PyString_FromStringAndSize(name, name_size-1);
    if (!self->platform_vendor)
    {
        PyErr_NoMemory();
        return -1;
    }
    
    return 0;
}

static void
oclplatf_dealloc(OpenCLPlatform *self)
{
    Py_XDECREF(self->numDevices);
    Py_XDECREF(self->platform_name);
    Py_XDECREF(self->platform_vendor);
    self->ob_type->tp_free((PyObject*)self);
}

static int
ocldevice_init(OpenCLDevice *self, PyObject *args, PyObject *kwds)
{
    int platform_idx, dev_idx;
    cl_uint num_entries;
    cl_device_id *devices;
    cl_device_type device_type;
    char dev_name[128];
    size_t name_size, i;
    size_t *max_work_sizes;
    cl_int err;

    if (!PyArg_ParseTuple(args, "ii:OpenCLDevice", &platform_idx, &dev_idx))
        return -1;

    if (platform_idx < 0 || platform_idx > num_platforms - 1)
    {
        PyErr_Format(PyExc_ValueError, "Platform-index out of range");
        return -1;
    }
    
    err = clGetDeviceIDs(platforms[platform_idx], CL_DEVICE_TYPE_ALL, 0, NULL, &num_entries);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to enumerate devices on this platform (%s)", getCLresultMsg(err));
        return -1;
    }
    if (dev_idx < 0 || dev_idx > num_entries-1)
    {
        PyErr_Format(PyExc_ValueError, "Device-index out of range");
        return -1;
    }

    devices = PyMem_New(cl_device_id, num_entries);
    if (!devices)
    {
        PyErr_NoMemory();
        return -1;
    }
    err = clGetDeviceIDs(platforms[platform_idx], CL_DEVICE_TYPE_ALL, num_entries, devices, NULL);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get Device-IDs (%s)", getCLresultMsg(err));
        PyMem_Free(devices);
        return -1;
    }
    self->device = devices[dev_idx];
    PyMem_Free(devices);
    
    self->dev_name = self->dev_type = self->dev_maxworksize = NULL;
    self->dev_ctx = NULL;
    self->dev_prog = NULL;
    self->dev_kernel = NULL;
    self->dev_queue = NULL;

    err = clGetDeviceInfo(self->device, CL_DEVICE_NAME, sizeof(dev_name), &dev_name, &name_size);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get device-name (%s)", getCLresultMsg(err));
        return -1;
    }
    self->dev_name = PyString_FromStringAndSize(dev_name, name_size-1);
    if (!self->dev_name)
    {
        PyErr_NoMemory();
        return -1;
    }
    
    err = clGetDeviceInfo(self->device, CL_DEVICE_TYPE, sizeof(device_type), &device_type, NULL);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get device-type (%s)", getCLresultMsg(err));
        return -1;
    }
    if (device_type & CL_DEVICE_TYPE_CPU)
    {
        self->dev_type = PyString_FromString("CPU");
    } else if (device_type & CL_DEVICE_TYPE_GPU)
    {
        self->dev_type = PyString_FromString("GPU");
    } else if (device_type & CL_DEVICE_TYPE_ACCELERATOR)
    {
        self->dev_type = PyString_FromString("ACCELERATOR");
    } else
    {
        self->dev_type = PyString_FromString("UNKNOWN");
    }
    if (!self->dev_type)
    {
        PyErr_NoMemory();
        return -1;
    }
    
    err = clGetDeviceInfo(self->device, CL_DEVICE_MAX_WORK_GROUP_SIZE, sizeof(self->dev_workgroupsize), &self->dev_workgroupsize, NULL);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get max. workgroup-size (%s)", getCLresultMsg(err));
        return -1;
    }

    err = clGetDeviceInfo(self->device, CL_DEVICE_MAX_WORK_ITEM_DIMENSIONS, sizeof(num_entries), &num_entries, NULL);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to determine work-dimensions (%s)", getCLresultMsg(err));
        return -1;
    }

    max_work_sizes = PyMem_New(size_t, num_entries);
    if (!max_work_sizes)
    {
        PyErr_NoMemory();
        return -1;
    }
    err = clGetDeviceInfo(self->device, CL_DEVICE_MAX_WORK_ITEM_SIZES, sizeof(size_t) * num_entries, max_work_sizes, NULL);
    if (err != CL_SUCCESS)
    {
        PyMem_Free(max_work_sizes);
        PyErr_Format(PyExc_SystemError, "Failed to determine max. dimension sizes. (%s)", getCLresultMsg(err));
        return -1;
    }
    self->dev_maxworksize = PyTuple_New(num_entries);
    if (!self->dev_maxworksize)
    {
        PyMem_Free(max_work_sizes);
        PyErr_NoMemory();
        return -1;
    }
    for (i = 0; i < num_entries; i++)
        PyTuple_SetItem(self->dev_maxworksize, i, PyInt_FromSize_t(max_work_sizes[i]));
    PyMem_Free(max_work_sizes);
    
    return 0;
}

static int
ocldevice_compile(OpenCLDevice *self)
{
    char log[1024];
    cl_int err, status;

    if (!self->dev_ctx)
    {
        self->dev_ctx = clCreateContext(NULL, 1, &(self->device), NULL, NULL, &err);
        if (err != CL_SUCCESS)
        {
            PyErr_Format(PyExc_SystemError, "Failed to create device-context (%s)", getCLresultMsg(err));
            return -1;
        }
    }
    
    if (!self->dev_queue)
    {
        self->dev_queue = clCreateCommandQueue(self->dev_ctx, self->device, 0, &err);
        if (err != CL_SUCCESS)
        {
            PyErr_Format(PyExc_SystemError, "Failed to create command-queue (%s)", getCLresultMsg(err));
            return -1;
        }
    }
    
    if (!self->dev_prog)
    {
        self->dev_prog = clCreateProgramWithSource(self->dev_ctx, 1, (void*)&oclkernel_program, &oclkernel_size, &err);
        if (err != CL_SUCCESS)
        {
            PyErr_Format(PyExc_SystemError, "Failed to load kernel-source (%s)", getCLresultMsg(err));
            return -1;
        }
    }
    
    if (!self->dev_kernel)
    {
        err = clBuildProgram(self->dev_prog, 0, NULL, NULL, NULL, NULL);
        if (err != CL_SUCCESS)
        {
            clGetProgramBuildInfo(self->dev_prog, self->device, CL_PROGRAM_BUILD_LOG, sizeof(log), log, NULL);
            PyErr_Format(PyExc_SystemError, "Failed to build kernel (%s):\n%s", getCLresultMsg(err), log);
            return -1;
        }

        err = clGetProgramBuildInfo(self->dev_prog, self->device, CL_PROGRAM_BUILD_STATUS, sizeof(status), &status, NULL);
        if (err != CL_SUCCESS || status != CL_BUILD_SUCCESS)
        {
            clGetProgramBuildInfo(self->dev_prog, self->device, CL_PROGRAM_BUILD_LOG, sizeof(log), log, NULL);
            PyErr_Format(PyExc_SystemError, "Failed to compile kernel (%s):\n%s", getCLresultMsg(err), log);
            return -1;
        }
           
        self->dev_kernel = clCreateKernel(self->dev_prog, "opencl_pmk_kernel", &err);
        if (err != CL_SUCCESS)
        {
            PyErr_Format(PyExc_SystemError, "Failed to create kernel (%s)", getCLresultMsg(err));
            return -1;
        }
    }

    return 0;

}

static void
ocldevice_dealloc(OpenCLDevice *self)
{
    if (self->dev_queue)
        clReleaseCommandQueue(self->dev_queue);
    if (self->dev_kernel)
        clReleaseKernel(self->dev_kernel);
    if (self->dev_prog)
        clReleaseProgram(self->dev_prog);
    if (self->dev_ctx)
        clReleaseContext(self->dev_ctx);
    Py_XDECREF(self->dev_name);
    Py_XDECREF(self->dev_type);
    Py_XDECREF(self->dev_maxworksize);
    self->ob_type->tp_free((PyObject*)self);
}

static cl_int
calc_pmklist(OpenCLDevice *self, gpu_inbuffer *inbuffer, gpu_outbuffer* outbuffer, int size)
{
    cl_mem g_inbuffer, g_outbuffer;
    cl_int errcode, status;
    cl_event clEvents[3];
    size_t gWorksize[1];
    int i;
    
    g_inbuffer = g_outbuffer = NULL;
    clEvents[0] = clEvents[1] = clEvents[2] = 0;
    gWorksize[0] = (size / self->dev_workgroupsize + (size % self->dev_workgroupsize == 0 ? 0 : 1)) * self->dev_workgroupsize;
    
    g_inbuffer = clCreateBuffer(self->dev_ctx, CL_MEM_READ_ONLY, gWorksize[0]*sizeof(gpu_inbuffer), NULL, &errcode);
    if (errcode != CL_SUCCESS)
        goto out;
    errcode = clEnqueueWriteBuffer(self->dev_queue, g_inbuffer, CL_FALSE, 0, size*sizeof(gpu_inbuffer), inbuffer, 0, NULL, &clEvents[0]);
    if (errcode != CL_SUCCESS)
        goto out;
    
    g_outbuffer = clCreateBuffer(self->dev_ctx, CL_MEM_WRITE_ONLY, gWorksize[0]*sizeof(gpu_outbuffer), NULL, &errcode);
    if (errcode != CL_SUCCESS)
        goto out;
    
    errcode = clSetKernelArg(self->dev_kernel, 0, sizeof(cl_mem), &g_inbuffer);
    if (errcode != CL_SUCCESS)
        goto out;
    errcode = clSetKernelArg(self->dev_kernel, 1, sizeof(cl_mem), &g_outbuffer);
    if (errcode != CL_SUCCESS)
        goto out;
    errcode = clEnqueueNDRangeKernel(self->dev_queue, self->dev_kernel, 1, NULL, gWorksize, NULL, 1, &clEvents[0], &clEvents[1]);
    if (errcode != CL_SUCCESS)
        goto out;

    errcode = clEnqueueReadBuffer(self->dev_queue, g_outbuffer, CL_FALSE, 0, size*sizeof(gpu_outbuffer), outbuffer, 2, &clEvents[0], &clEvents[2]);
    if (errcode != CL_SUCCESS)
        goto out;
    
    errcode = clFinish(self->dev_queue);
    if (errcode != CL_SUCCESS)
        goto out;
    errcode = clWaitForEvents(3, &clEvents[0]);
    if (errcode != CL_SUCCESS)
        goto out;
    for (i = 0; i < 3; i++)
    {
        errcode = clGetEventInfo(clEvents[i], CL_EVENT_COMMAND_EXECUTION_STATUS, sizeof(status), &status, NULL);
        if (errcode != CL_SUCCESS)
            goto out;
        if (status != CL_COMPLETE)
        {
            errcode = CL_INVALID_OPERATION;
            goto out;
        }
    }

out:
    for (i = 0; i < 3; i++)
    {
        if (clEvents[i] != 0)
            clReleaseEvent(clEvents[i]);
    }

    if (g_inbuffer != NULL)
        clReleaseMemObject(g_inbuffer);
    if (g_outbuffer != NULL)
        clReleaseMemObject(g_outbuffer);
    
    return errcode;
}

PyObject*
cpyrit_solve(OpenCLDevice *self, PyObject *args)
{
    unsigned char essid[32+4], *passwd, pad[64], temp[32];
    int i, arraysize, essidlen, passwdlen;
    PyObject *essid_obj, *passwd_seq, *passwd_obj, *result;
    gpu_inbuffer *c_inbuffer, *t;
    gpu_outbuffer *c_outbuffer;
    SHA_CTX ctx_pad;

    if (!PyArg_ParseTuple(args, "OO", &essid_obj, &passwd_seq)) return NULL;
    passwd_seq = PyObject_GetIter(passwd_seq);
    if (!passwd_seq) return NULL;
    
    if (self->dev_kernel == NULL)
    {
        if (ocldevice_compile(self) != 0)
            return NULL;
    }
    
    essidlen = PyString_Size(essid_obj);
    if (essidlen < 1 || essidlen > 32)
    {
        Py_DECREF(passwd_seq);
        PyErr_SetString(PyExc_ValueError, "The ESSID must be a string between 1 and 32 characters");
        return NULL;
    }
    memcpy(essid, PyString_AsString(essid_obj), essidlen);
    memset(essid + essidlen, 0, sizeof(essid) - essidlen);

    arraysize = 0;
    c_inbuffer = NULL;
    c_outbuffer = NULL;
    while ((passwd_obj = PyIter_Next(passwd_seq)))
    {
        if (arraysize % 1000 == 0)
        {
            t = PyMem_Resize(c_inbuffer, gpu_inbuffer, arraysize+1000);
            if (!t)
            {
                Py_DECREF(passwd_obj);
                Py_DECREF(passwd_seq);
                PyMem_Free(c_inbuffer);
                PyErr_NoMemory();
                return NULL;
            }
            c_inbuffer = t;
        }
                
        passwd = (unsigned char*)PyString_AsString(passwd_obj);
        passwdlen = PyString_Size(passwd_obj);
        if (passwd == NULL || passwdlen < 8 || passwdlen > 63)
        {
            Py_DECREF(passwd_obj);
            Py_DECREF(passwd_seq);
            PyMem_Free(c_inbuffer);
            PyErr_SetString(PyExc_ValueError, "All items must be strings between 8 and 63 characters");
            return NULL;
        }
        
        memcpy(pad, passwd, passwdlen);
        memset(pad + passwdlen, 0, sizeof(pad) - passwdlen);
        for (i = 0; i < 16; i++)
            ((unsigned int*)pad)[i] ^= 0x36363636;
        SHA1_Init(&ctx_pad);
        SHA1_Update(&ctx_pad, pad, sizeof(pad));
        CPY_DEVCTX(ctx_pad, c_inbuffer[arraysize].ctx_ipad);
        for (i = 0; i < 16; i++)
            ((unsigned int*)pad)[i] ^= 0x6A6A6A6A;
        SHA1_Init(&ctx_pad);
        SHA1_Update(&ctx_pad, pad, sizeof(pad));
        CPY_DEVCTX(ctx_pad, c_inbuffer[arraysize].ctx_opad);
        
        essid[essidlen + 4 - 1] = '\1';
        HMAC(EVP_sha1(), passwd, passwdlen, essid, essidlen + 4, temp, NULL);
        GET_BE(c_inbuffer[arraysize].e1.h0, temp, 0);
        GET_BE(c_inbuffer[arraysize].e1.h1, temp, 4);
        GET_BE(c_inbuffer[arraysize].e1.h2, temp, 8);
        GET_BE(c_inbuffer[arraysize].e1.h3, temp, 12);
        GET_BE(c_inbuffer[arraysize].e1.h4, temp, 16);

        essid[essidlen + 4 - 1] = '\2';
        HMAC(EVP_sha1(), passwd, passwdlen, essid, essidlen + 4, temp, NULL);
        GET_BE(c_inbuffer[arraysize].e2.h0, temp, 0);
        GET_BE(c_inbuffer[arraysize].e2.h1, temp, 4);
        GET_BE(c_inbuffer[arraysize].e2.h2, temp, 8);
        GET_BE(c_inbuffer[arraysize].e2.h3, temp, 12);
        GET_BE(c_inbuffer[arraysize].e2.h4, temp, 16);

        Py_DECREF(passwd_obj);
        arraysize++;
    }
    Py_DECREF(passwd_seq);
    
    if (arraysize == 0)
    {
        PyMem_Free(c_inbuffer);
        return PyTuple_New(0);
    }

    c_outbuffer = PyMem_New(gpu_outbuffer, arraysize);
    if (c_outbuffer == NULL)
    {
        PyMem_Free(c_inbuffer);
        PyErr_NoMemory();
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS;
    i = calc_pmklist(self, c_inbuffer, c_outbuffer, arraysize);
    Py_END_ALLOW_THREADS;    
    PyMem_Free(c_inbuffer);
    
    if (i != CL_SUCCESS)
    {
        PyMem_Free(c_outbuffer);
        PyErr_Format(PyExc_SystemError, "Failed to execute kernel (%s)", getCLresultMsg(i));
        return NULL;
    }

    result = PyTuple_New(arraysize);
    for (i = 0; i < arraysize; i++)
    {
        PUT_BE(c_outbuffer[i].pmk1.h0, temp, 0); PUT_BE(c_outbuffer[i].pmk1.h1, temp, 4);
        PUT_BE(c_outbuffer[i].pmk1.h2, temp, 8); PUT_BE(c_outbuffer[i].pmk1.h3, temp, 12); 
        PUT_BE(c_outbuffer[i].pmk1.h4, temp, 16);PUT_BE(c_outbuffer[i].pmk2.h0, temp, 20); 
        PUT_BE(c_outbuffer[i].pmk2.h1, temp, 24);PUT_BE(c_outbuffer[i].pmk2.h2, temp, 28); 
        PyTuple_SetItem(result, i, PyString_FromStringAndSize((char*)temp, 32));
    }
    
    PyMem_Free(c_outbuffer);

    return result;
}

static PyMemberDef OpenCLPlatform_members[] =
{
    {"platformName", T_OBJECT, offsetof(OpenCLPlatform, platform_name), 0},
    {"platformVendor", T_OBJECT, offsetof(OpenCLPlatform, platform_vendor), 0},
    {"numDevices", T_OBJECT, offsetof(OpenCLPlatform, numDevices), 0},
    {NULL}
};

static PyTypeObject OpenCLPlatform_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cuda.OpenCLPlatform",/*tp_name*/
    sizeof(OpenCLPlatform),     /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    (destructor)oclplatf_dealloc,/*tp_dealloc*/
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
    0,
    OpenCLPlatform_members,     /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)oclplatf_init,    /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMemberDef OpenCLDevice_members[] =
{
    {"deviceName", T_OBJECT, offsetof(OpenCLDevice, dev_name), 0},
    {"deviceType", T_OBJECT, offsetof(OpenCLDevice, dev_type), 0},
    {"maxWorkSizes", T_OBJECT, offsetof(OpenCLDevice, dev_maxworksize), 0},
    {NULL}
};

static PyMethodDef OpenCLDevice_methods[] =
{
    {"solve", (PyCFunction)cpyrit_solve, METH_VARARGS, "Calculate PMKs from ESSID and list of strings."},
    {NULL, NULL}
};

static PyTypeObject OpenCLDevice_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cuda.OpenCLDevice",/*tp_name*/
    sizeof(OpenCLDevice),       /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    (destructor)ocldevice_dealloc,/*tp_dealloc*/
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
    OpenCLDevice_methods,       /*tp_methods*/
    OpenCLDevice_members,       /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)ocldevice_init,   /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};


static PyMethodDef CPyritOpenCL_methods[] = {
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
init_cpyrit_opencl(void)
{
    PyObject *m;
    z_stream zst;
    cl_int err;
    
    err = clGetPlatformIDs(0, NULL, &num_platforms);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to enumerate OpenCL-platforms (%s)", getCLresultMsg(err));
        return;
    }
    
    platforms = PyMem_New(cl_platform_id, num_platforms);
    if (!platforms)
    {
        PyErr_NoMemory();
        return;
    }
    
    err = clGetPlatformIDs(num_platforms, platforms, NULL);
    if (err != CL_SUCCESS)
    {
        PyErr_Format(PyExc_SystemError, "Failed to get platform-IDs (%s)", getCLresultMsg(err));
        return;
    }
    
    oclkernel_program = PyMem_Malloc(oclkernel_size);
    if (!oclkernel_program)
    {
        PyMem_Free(platforms);
        PyErr_NoMemory();
        return;
    }
    zst.zalloc = Z_NULL;
    zst.zfree = Z_NULL;
    zst.opaque = Z_NULL;
    zst.avail_in = sizeof(oclkernel_packedprogram);
    zst.next_in = oclkernel_packedprogram;
    if (inflateInit(&zst) != Z_OK)
    {
        PyMem_Free(platforms);
        PyMem_Free(oclkernel_program);
        PyErr_SetString(PyExc_IOError, "Failed to initialize zlib.");
        return;
    }
    zst.avail_out = oclkernel_size;
    zst.next_out = oclkernel_program;   
    if (inflate(&zst, Z_FINISH) != Z_STREAM_END)
    {
        inflateEnd(&zst);
        PyMem_Free(platforms);
        PyMem_Free(oclkernel_program);    
        PyErr_SetString(PyExc_IOError, "Failed to decompress OpenCL-kernel.");
        return;
    }
    inflateEnd(&zst);
    oclkernel_size -= 1;

    OpenCLPlatform_type.tp_getattro = PyObject_GenericGetAttr;
    OpenCLPlatform_type.tp_setattro = PyObject_GenericSetAttr;
    OpenCLPlatform_type.tp_alloc  = PyType_GenericAlloc;
    OpenCLPlatform_type.tp_new = PyType_GenericNew;
    OpenCLPlatform_type.tp_free = _PyObject_Del;      
    if (PyType_Ready(&OpenCLPlatform_type) < 0)
    {
        PyMem_Free(platforms);
        PyMem_Free(oclkernel_program);
	    return;
    }

    OpenCLDevice_type.tp_getattro = PyObject_GenericGetAttr;
    OpenCLDevice_type.tp_setattro = PyObject_GenericSetAttr;
    OpenCLDevice_type.tp_alloc  = PyType_GenericAlloc;
    OpenCLDevice_type.tp_new = PyType_GenericNew;
    OpenCLDevice_type.tp_free = _PyObject_Del;      
    if (PyType_Ready(&OpenCLDevice_type) < 0)
    {
        PyMem_Free(platforms);
        PyMem_Free(oclkernel_program);
	    return;
    }


    m = Py_InitModule("_cpyrit_opencl", CPyritOpenCL_methods);

    Py_INCREF(&OpenCLPlatform_type);
    PyModule_AddObject(m, "OpenCLPlatform", (PyObject *)&OpenCLPlatform_type);    

    Py_INCREF(&OpenCLDevice_type);
    PyModule_AddObject(m, "OpenCLDevice", (PyObject *)&OpenCLDevice_type);

    PyModule_AddIntConstant(m, "numPlatforms", (long)num_platforms);

    PyModule_AddStringConstant(m, "VERSION", VERSION);
}

