/*
#
#    Copyright 2008-2011, Lukas Lueg, lukas.lueg@gmail.com
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

#include <Python.h>
#include <structmember.h>
#include <stdint.h>
#include <openssl/hmac.h>
#include <openssl/md5.h>
#include <openssl/sha.h>
#include <openssl/aes.h>
#include <zlib.h>
#include <pcap.h>
#include "cpufeatures.h"
#include "_cpyrit_cpu.h"
//#include <sys/auxv.h>
#ifdef COMPILE_AESNI
    #include <wmmintrin.h>
#endif

static PyObject *PlatformString;
static PyTypeObject CowpattyResult_type;

/* Function pointers depend on the execution path that got compiled and that we can take (AES-NI, SSE2, x86) */
/* CPUDevice */
static void (*prepare_pmk)(const unsigned char *essid_pre, int essidlen, const unsigned char *password, int passwdlen, struct pmk_ctr *ctr) = NULL;
static int (*finalize_pmk)(struct pmk_ctr *ctr) = NULL;
/* EAPOLCracker */
static unsigned char* (*fourwise_sha1hmac_prepare)(unsigned char* msg, int msg_len) = NULL;
static void (*fourwise_sha1hmac)(unsigned char* message, int message_length, unsigned char* keys, int key_length, unsigned char* hmacs) = NULL;
static unsigned char* (*fourwise_md5hmac_prepare)(unsigned char* msg, int msg_len) = NULL;
static void (*fourwise_md5hmac)(unsigned char* message, int message_length, unsigned char* keys, int key_length, unsigned char* hmacs) = NULL;
/* CCMPCracker */
static void (*fourwise_pke2tk)(unsigned char *pke1, unsigned char *pke2, unsigned char *pmkbuffer, Py_ssize_t keycount, unsigned char *tkbuffer) = NULL;
static Py_ssize_t (*ccmp_encrypt)(const unsigned char *A0, const unsigned char *S0, const unsigned char *tkbuffer, Py_ssize_t keycount) = NULL;


#ifdef COMPILE_SSE2
    uint32_t md5_constants[64][4];
    extern int detect_sse2(void);
    extern int sse2_sha1_update(uint32_t ctx[4*5+4*6], uint32_t data[4*16], uint32_t wrkbuf[4*80]) __attribute__ ((regparm(3)));
    extern int sse2_sha1_finalize(uint32_t ctx[4*5+4*6], uint32_t digests[4*5]) __attribute__ ((regparm(2)));
    extern int sse2_md5_update(uint32_t ctx[4*5], uint32_t data[4*16], uint32_t constants[4*64]) __attribute__ ((regparm(3)));
#endif


/*
    ###########################################################################

    CPUDevice

    ###########################################################################
*/

#ifdef COMPILE_SSE2
    static int
    finalize_pmk_sse2(struct pmk_ctr *ctr)
    {
        int i, j, k;
        uint32_t ctx_ipad[4*5]      __attribute__ ((aligned (16)));
        uint32_t ctx_opad[4*5]      __attribute__ ((aligned (16)));
        uint32_t sha1_ctx[4*5+4*6]  __attribute__ ((aligned (16)));
        uint32_t e1_buffer[4*16]    __attribute__ ((aligned (16)));
        uint32_t e2_buffer[4*16]    __attribute__ ((aligned (16)));
        uint32_t wrkbuf[4*80]       __attribute__ ((aligned (16)));

        memset(e1_buffer, 0, sizeof(e1_buffer));
        memset(e2_buffer, 0, sizeof(e2_buffer));

        for (i = 0; i < 4; i++)
        {
            sha1_ctx[4*5 + 0*4 + i] = 0x5A827999; /* const_stage0 */
            sha1_ctx[4*5 + 1*4 + i] = 0x6ED9EBA1; /* const_stage1 */
            sha1_ctx[4*5 + 2*4 + i] = 0x8F1BBCDC; /* const_stage2 */
            sha1_ctx[4*5 + 3*4 + i] = 0xCA62C1D6; /* const_stage3 */
            sha1_ctx[4*5 + 4*4 + i] = 0xFF00FF00; /* const_ff00   */
            sha1_ctx[4*5 + 5*4 + i] = 0x00FF00FF; /* const_00ff   */
        }

        // Interleave four ipads, opads and first-round-PMKs to local buffers
        for (i = 0; i < 4; i++)
        {
            ctx_ipad[i+ 0] = ctr[i].ctx_ipad.h0;
            ctx_ipad[i+ 4] = ctr[i].ctx_ipad.h1;
            ctx_ipad[i+ 8] = ctr[i].ctx_ipad.h2;
            ctx_ipad[i+12] = ctr[i].ctx_ipad.h3;
            ctx_ipad[i+16] = ctr[i].ctx_ipad.h4;

            ctx_opad[i+ 0] = ctr[i].ctx_opad.h0;
            ctx_opad[i+ 4] = ctr[i].ctx_opad.h1;
            ctx_opad[i+ 8] = ctr[i].ctx_opad.h2;
            ctx_opad[i+12] = ctr[i].ctx_opad.h3;
            ctx_opad[i+16] = ctr[i].ctx_opad.h4;

            e1_buffer[20+i] = e2_buffer[20+i] = 0x80; // Terminator bit
            e1_buffer[60+i] = e2_buffer[60+i] = 0xA0020000; // size = (64+20)*8
            for (j = 0; j < 5; j++)
            {
                e1_buffer[j*4 + i] = ctr[i].e1[j];
                e2_buffer[j*4 + i] = ctr[i].e2[j];
            }
        }

        // Process through SSE2 and de-interleave back to ctr
        for (i = 0; i < 4096-1; i++)
        {
            memcpy(sha1_ctx, ctx_ipad, 4 * 5 * sizeof(uint32_t));
            sse2_sha1_update(sha1_ctx, e1_buffer, wrkbuf);
            sse2_sha1_finalize(sha1_ctx, e1_buffer);

            memcpy(sha1_ctx, ctx_opad, 4 * 5 * sizeof(uint32_t));
            sse2_sha1_update(sha1_ctx, e1_buffer, wrkbuf);
            sse2_sha1_finalize(sha1_ctx, e1_buffer);

            memcpy(sha1_ctx, ctx_ipad, 4 * 5 * sizeof(uint32_t));
            sse2_sha1_update(sha1_ctx, e2_buffer, wrkbuf);
            sse2_sha1_finalize(sha1_ctx, e2_buffer);

            memcpy(sha1_ctx, ctx_opad, 4 * 5 * sizeof(uint32_t));
            sse2_sha1_update(sha1_ctx, e2_buffer, wrkbuf);
            sse2_sha1_finalize(sha1_ctx, e2_buffer);

            for (j = 0; j < 4; j++)
            {
                for (k = 0; k < 5; k++)
                {
                    ctr[j].e1[k] ^= e1_buffer[k*4 + j];
                    ctr[j].e2[k] ^= e2_buffer[k*4 + j];
                }
            }
        }

        return 4;
    }
#endif // COMPILE_SSE2

static void
prepare_pmk_openssl(const unsigned char *essid_pre, int essidlen, const unsigned char *password, int passwdlen, struct pmk_ctr *ctr)
{
    int i;
    unsigned char pad[64], essid[32+4];

    essidlen = essidlen > 32 ? 32 : essidlen;
    passwdlen = passwdlen > 64 ? 64 : passwdlen;

    memcpy(essid, essid_pre, essidlen);
    memset(essid + essidlen, 0, sizeof(essid) - essidlen);

    memcpy(pad, password, passwdlen);
    memset(pad + passwdlen, 0, sizeof(pad) - passwdlen);
    for( i = 0; i < 16; i++ )
	    ((unsigned int*)pad)[i] ^= 0x36363636;
    SHA1_Init(&ctr->ctx_ipad);
    SHA1_Update(&ctr->ctx_ipad, pad, 64);
    for( i = 0; i < 16; i++ )
	    ((unsigned int*)pad)[i] ^= 0x6A6A6A6A;
    SHA1_Init(&ctr->ctx_opad);
    SHA1_Update(&ctr->ctx_opad, pad, 64);

    essid[essidlen + 4 - 1] = '\1';
    HMAC(EVP_sha1(), password, passwdlen, essid, essidlen + 4, (unsigned char*)ctr->e1, NULL);

    essid[essidlen + 4 - 1] = '\2';
    HMAC(EVP_sha1(), password, passwdlen, essid, essidlen + 4, (unsigned char*)ctr->e2, NULL);
}

static int
finalize_pmk_openssl(struct pmk_ctr *ctr)
{
    int i, j;
    SHA_CTX ctx;
    unsigned int e1_buffer[5], e2_buffer[5];

    memcpy(e1_buffer, ctr->e1, 20);
    memcpy(e2_buffer, ctr->e2, 20);
    for(i = 0; i < 4096-1; i++)
    {
        memcpy(&ctx, &ctr->ctx_ipad, sizeof(ctx));
        SHA1_Update(&ctx, (unsigned char*)e1_buffer, 20);
        SHA1_Final((unsigned char*)e1_buffer, &ctx);

        memcpy(&ctx, &ctr->ctx_opad, sizeof(ctx));
        SHA1_Update(&ctx, (unsigned char*)e1_buffer, 20);
        SHA1_Final((unsigned char*)e1_buffer, &ctx);

        for (j = 0; j < 5; j++)
            ctr->e1[j] ^= e1_buffer[j];

        memcpy(&ctx, &ctr->ctx_ipad, sizeof(ctx));
        SHA1_Update(&ctx, (unsigned char*)e2_buffer, 20);
        SHA1_Final((unsigned char*)e2_buffer, &ctx);

        memcpy(&ctx, &ctr->ctx_opad, sizeof(ctx));
        SHA1_Update(&ctx, (unsigned char*)e2_buffer, 20);
        SHA1_Final((unsigned char*)e2_buffer, &ctx);

        for (j = 0; j < 3; j++)
            ctr->e2[j] ^= e2_buffer[j];
    }

    return 1;
}

PyDoc_STRVAR(CPUDevice_solve__doc__,
    "solve(essid, passwords) -> tuple\n\n"
    "Calculate PMKs from ESSID and iterable of strings.");

static PyObject *
CPUDevice_solve(PyObject *self, PyObject *args)
{
    unsigned char *essid, *passwd;
    PyObject *passwd_seq, *passwd_obj, *essid_obj, *result;
    int i, arraysize, essidlen, passwdlen;
    struct pmk_ctr *pmk_buffer, *t;

    if (!PyArg_ParseTuple(args, "OO", &essid_obj, &passwd_seq)) return NULL;
    passwd_seq = PyObject_GetIter(passwd_seq);
    if (!passwd_seq) return NULL;

    essid = (unsigned char*)PyString_AsString(essid_obj);
    essidlen = PyString_Size(essid_obj);
    if (essid == NULL || essidlen < 1 || essidlen > 32)
    {
        Py_DECREF(passwd_seq);
        PyErr_SetString(PyExc_ValueError, "ESSID must be a string between 1 and 32 bytes.");
        return NULL;
    }

    arraysize = 0;
    pmk_buffer = NULL;
    while ((passwd_obj=PyIter_Next(passwd_seq)))
    {
        if (arraysize % 100 == 0)
        {
            // Step-size must be aligned to four entries so finalize_pmk_sse2 has air to breath
            t = PyMem_Realloc(pmk_buffer, sizeof(struct pmk_ctr) * (arraysize+100));
            if (!t)
            {
                Py_DECREF(passwd_obj);
                Py_DECREF(passwd_seq);
                PyMem_Free(pmk_buffer);
                PyErr_NoMemory();
                return NULL;
            }
            pmk_buffer = t;
        }
        passwd = (unsigned char*)PyString_AsString(passwd_obj);
        passwdlen = PyString_Size(passwd_obj);
        if (passwd == NULL || passwdlen < 8 || passwdlen > 63)
        {
            Py_DECREF(passwd_obj);
            Py_DECREF(passwd_seq);
            PyMem_Free(pmk_buffer);
            PyErr_SetString(PyExc_ValueError, "All passwords must be strings between 8 and 63 characters");
            return NULL;
        }
        prepare_pmk(essid, essidlen, passwd, passwdlen, &pmk_buffer[arraysize]);
        Py_DECREF(passwd_obj);
        arraysize++;
    }
    Py_DECREF(passwd_seq);

    if (arraysize > 0)
    {
        Py_BEGIN_ALLOW_THREADS;
        i = 0;
        do
            i += finalize_pmk(&pmk_buffer[i]);
        while (i < arraysize);
        Py_END_ALLOW_THREADS;

        result = PyTuple_New(arraysize);
        for (i = 0; i < arraysize; i++)
            PyTuple_SetItem(result, i, PyString_FromStringAndSize((char*)pmk_buffer[i].e1, 32));
    } else {
        result = PyTuple_New(0);
    }

    PyMem_Free(pmk_buffer);

    return result;
}

/*
    ###########################################################################

    EAPOLCracker

    ###########################################################################
*/

static int
Cracker_unpack(PyObject* result_seq, unsigned char **pmkbuffer_ptr)
{
    unsigned char *pmkbuffer, *t;
    int buffersize, itemcount;
    PyObject *result_iter, *result_obj, *pmk_obj;

    pmkbuffer = pmkbuffer_ptr[0] = NULL;
    buffersize = itemcount = 0;

    result_iter = PyObject_GetIter(result_seq);
    if (!result_iter)
    {
        PyErr_SetString(PyExc_ValueError, "Parameter must be a iterable of (password, PMK)-sequences.");
        return -1;
    }

    while ((result_obj = PyIter_Next(result_iter)))
    {
        if (buffersize <= itemcount)
        {
            /* Step-size must be aligned to four entries (SSE2-path) */
            buffersize += 50000;
            t = PyMem_Realloc(pmkbuffer, buffersize*32);
            if (!t)
            {
                PyErr_NoMemory();
                Py_DECREF(result_obj);
                goto out;
            }
            pmkbuffer = t;
        }

        pmk_obj = PySequence_GetItem(result_obj, 1);
        if (!pmk_obj)
        {
            PyErr_SetString(PyExc_ValueError, "Expected Pairwise Master Key as second item in a sequence-object.");
            Py_DECREF(result_obj);
            PyMem_Free(pmkbuffer);
            goto out;
        }
        t = (unsigned char*)PyString_AsString(pmk_obj);
        if (t == NULL || PyString_Size(pmk_obj) != 32)
        {
            PyErr_SetString(PyExc_ValueError, "All PMKs must be strings of 32 characters");
            Py_DECREF(result_obj);
            Py_DECREF(pmk_obj);
            PyMem_Free(pmkbuffer);
            goto out;
        }
        memcpy(pmkbuffer + itemcount*32, t, 32);
        itemcount += 1;
        Py_DECREF(pmk_obj);
        Py_DECREF(result_obj);
    }

    pmkbuffer_ptr[0] = pmkbuffer;

    out:
    Py_DECREF(result_iter);

    return itemcount * 32;
}

#ifdef COMPILE_SSE2
    static unsigned char*
    fourwise_sha1hmac_prepare_sse2(unsigned char* msg, int msg_len)
    {
        int buffer_len, i, j, k;
        unsigned char *retval, *buffer, *prepared_msg;

        /* Align length to 56 bytes for for message, 1 for terminator, 8 for size */
        buffer_len = msg_len + (64 - ((msg_len + 1 + 8) % 64)) + 1 + 8;
        buffer = PyMem_Malloc(buffer_len);
        if (!buffer)
            return NULL;

        /* Terminate msg, total length = 64 bytes for IPAD + sizeof(msg) in bits */
        memset(buffer, 0, buffer_len);
        memcpy(buffer, msg, msg_len);
        buffer[msg_len] = 0x80;
        PUT_BE((64 + msg_len) * 8, buffer, buffer_len - 4);

        retval = PyMem_Malloc(buffer_len * 4 + 16);
        if (!retval)
        {
            PyMem_Free(buffer);
            return NULL;
        }

        /* Interleave buffer four times for SSE2-processing */
        prepared_msg = retval + 16 - ((long)retval % 16);
        for (i = 0; i < buffer_len / 64; i++)
            for (j = 0; j < 16; j++)
                for (k = 0; k < 4; k++)
                    ((uint32_t*)prepared_msg)[(i * 64) + (j * 4) + k] = ((uint32_t*)buffer)[(i * 16) + j];

        PyMem_Free(buffer);

        return retval;
    }

    static inline void
    fourwise_sha1_init(fourwise_sha1_ctx* ctx)
    {
        int i;

        for (i = 0; i < 4; i++)
        {
            ctx->h0[i] = 0x67452301;      /* magic start value */
            ctx->h1[i] = 0xEFCDAB89;      /* magic start value */
            ctx->h2[i] = 0x98BADCFE;      /* magic start value */
            ctx->h3[i] = 0x10325476;      /* magic start value */
            ctx->h4[i] = 0xC3D2E1F0;      /* magic start value */
            ctx->cst[0][i] = 0x5A827999;  /* const_stage0 */
            ctx->cst[1][i] = 0x6ED9EBA1;  /* const_stage1 */
            ctx->cst[2][i] = 0x8F1BBCDC;  /* const_stage2 */
            ctx->cst[3][i] = 0xCA62C1D6;  /* const_stage3 */
            ctx->cst[4][i] = 0xFF00FF00;  /* const_ff00   */
            ctx->cst[5][i] = 0x00FF00FF;  /* const_00ff   */
        }
    }

    static void
    fourwise_sha1hmac_sse2(unsigned char* prepared_msg, int message_length, unsigned char* keys, int key_length, unsigned char* hmacs)
    {
        int i, j;
        uint32_t buffer[16];
        uint32_t wrkbuf[4*80]        __attribute__ ((aligned (16)));
        uint32_t blockbuffer[16][4]  __attribute__ ((aligned (16)));
        uint32_t digests[4][5];
        fourwise_sha1_ctx ctx;

        key_length = key_length <= 64 ? key_length : 64;
        prepared_msg = prepared_msg + 16 - ((long)prepared_msg % 16);
        message_length = message_length + (64 - ((message_length + 1 + 8) % 64)) + 1 + 8;

        /* Step 1: Inner hash = IPAD ^ K // message */
        fourwise_sha1_init(&ctx);

        /* Process IPAD ^ K */
        for (i = 0; i < 4; i++)
        {
            memcpy(&buffer, &keys[key_length * i], key_length);
            memset(&((unsigned char*)buffer)[key_length], 0, sizeof(buffer) - key_length);
            for (j = 0; j < 16; j++)
                blockbuffer[j][i] = buffer[j] ^ 0x36363636;
        }
        sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)blockbuffer, wrkbuf);

        for (i = 0; i < message_length / 64; i++)
            sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)(prepared_msg + 64 * 4 * i), wrkbuf);

        /* First hash done */
        sse2_sha1_finalize((uint32_t*)&ctx, (uint32_t*)&blockbuffer);
        for (i = 0; i < 4; i++)
            for (j = 0; j < 5; j++)
                digests[i][j] = blockbuffer[j][i];

        /* Step 2: Outer hash = OPAD ^ K // inner hash */
        fourwise_sha1_init(&ctx);
        for (i = 0; i < 4; i++)
        {
            memcpy(&buffer, &keys[key_length * i], key_length);
            memset(&((unsigned char*)buffer)[key_length], 0, sizeof(buffer) - key_length);
            for (j = 0; j < 16; j++)
                blockbuffer[j][i] = buffer[j] ^ 0x5C5C5C5C;
        }
        sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)blockbuffer, wrkbuf);

        memset(blockbuffer, 0, sizeof(blockbuffer));
        for (i = 0; i < 4; i++)
        {
            for (j = 0; j < 5; j++)
                blockbuffer[j][i] = digests[i][j];
            blockbuffer[ 5][i] = 0x80;       /* Terminator bit */
            blockbuffer[15][i] = 0xA0020000; /* size = (64 + 20) * 8 */
        }

        sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)blockbuffer, wrkbuf);

        /* Second hash == HMAC */
        sse2_sha1_finalize((uint32_t*)&ctx, (uint32_t*)&blockbuffer);
        for (i = 0; i < 4; i++)
            for (j = 0; j < 5; j++)
                ((uint32_t*)hmacs)[i * 5 + j] = blockbuffer[j][i];
    }

    static unsigned char*
    fourwise_md5hmac_prepare_sse2(unsigned char* msg, int msg_len)
    {
        int buffer_len, i, j, k;
        unsigned char *retval, *buffer, *prepared_msg;

        /* Align length to 56 bytes for for message, 1 for terminator, 8 for size */
        buffer_len = msg_len + (64 - ((msg_len + 1 + 8) % 64)) + 1 + 8;
        buffer = PyMem_Malloc(buffer_len);
        if (!buffer)
            return NULL;

        /* Terminate msg, total length = 64 bytes for IPAD + sizeof(msg) in bits */
        memset(buffer, 0, buffer_len);
        memcpy(buffer, msg, msg_len);
        buffer[msg_len] = 0x80;
        ((uint32_t*)buffer)[buffer_len / 4 - 2] = (64 + msg_len) * 8;

        retval = PyMem_Malloc(buffer_len * 4 + 16);
        if (!retval)
        {
            PyMem_Free(buffer);
            return NULL;
        }

        /* Interleave buffer four times for SSE2-processing */
        prepared_msg = retval + 16 - ((long)retval % 16);
        for (i = 0; i < buffer_len / 64; i++)
            for (j = 0; j < 16; j++)
                for (k = 0; k < 4; k++)
                    ((uint32_t*)prepared_msg)[(i * 64) + (j * 4) + k] = ((uint32_t*)buffer)[(i * 16) + j];

        PyMem_Free(buffer);

        return retval;
    }

    static inline void
    fourwise_md5_init(fourwise_md5_ctx* ctx)
    {
        int i;

        for (i = 0; i < 4; i++)
        {
            ctx->a[i] = 0x67452301; ctx->b[i] = 0xEFCDAB89;
            ctx->c[i] = 0x98BADCFE; ctx->d[i] = 0x10325476;
        }
    }

    static void
    fourwise_md5hmac_sse2(unsigned char* prepared_msg, int message_length, unsigned char* keys, int key_length, unsigned char* hmacs)
    {
        int i, j;
        uint32_t buffer[16];
        uint32_t blockbuffer[16][4]  __attribute__ ((aligned (16)));
        uint32_t digests[4][4];
        fourwise_md5_ctx ctx;

        key_length = key_length <= 64 ? key_length : 64;
        prepared_msg = prepared_msg + 16 - ((long)prepared_msg % 16);
        message_length = message_length + (64 - ((message_length + 1 + 8) % 64)) + 1 + 8;

        /* Step 1: Inner hash = IPAD ^ K // message */
        fourwise_md5_init(&ctx);

        /* Process IPAD ^ K */
        for (i = 0; i < 4; i++)
        {
            memcpy(&buffer, &keys[key_length * i], key_length);
            memset(&((unsigned char*)buffer)[key_length], 0, sizeof(buffer) - key_length);
            for (j = 0; j < 16; j++)
                blockbuffer[j][i] = buffer[j] ^ 0x36363636;
        }
        sse2_md5_update((uint32_t*)&ctx, (uint32_t*)blockbuffer, (uint32_t*)&md5_constants);

        for (i = 0; i < message_length / 64; i++)
            sse2_md5_update((uint32_t*)&ctx, (uint32_t*)(prepared_msg + 64 * 4 * i), (uint32_t*)&md5_constants);

        /* First hash done */
        for (i = 0; i < 4; i++)
        {
            digests[i][0] = ctx.a[i];
            digests[i][1] = ctx.b[i];
            digests[i][2] = ctx.c[i];
            digests[i][3] = ctx.d[i];
        }

        /* Step 2: Outer hash = OPAD ^ K // inner hash */
        fourwise_md5_init(&ctx);
        for (i = 0; i < 4; i++)
        {
            memcpy(&buffer, &keys[key_length * i], key_length);
            memset(&((unsigned char*)buffer)[key_length], 0, sizeof(buffer) - key_length);
            for (j = 0; j < 16; j++)
                blockbuffer[j][i] = buffer[j] ^ 0x5C5C5C5C;
        }
        sse2_md5_update((uint32_t*)&ctx, (uint32_t*)blockbuffer, (uint32_t*)&md5_constants);

        memset(blockbuffer, 0, sizeof(blockbuffer));
        for (i = 0; i < 4; i++)
        {
            for (j = 0; j < 4; j++)
                blockbuffer[j][i] = digests[i][j];
            blockbuffer[ 4][i] = 0x80;        /* Terminator bit */
            blockbuffer[14][i] = (64+16) * 8; /* Size in bits */
        }
        sse2_md5_update((uint32_t*)&ctx, (uint32_t*)blockbuffer, (uint32_t*)&md5_constants);

        /* Second hash == HMAC */
        for (i = 0; i < 4; i++)
        {
            ((uint32_t*)hmacs)[i * 4 + 0] = ctx.a[i];
            ((uint32_t*)hmacs)[i * 4 + 1] = ctx.b[i];
            ((uint32_t*)hmacs)[i * 4 + 2] = ctx.c[i];
            ((uint32_t*)hmacs)[i * 4 + 3] = ctx.d[i];
        }
    }

#endif // COMPILE_SSE2

static unsigned char*
fourwise_hmac_prepare_openssl(unsigned char* msg, int msg_len)
{
    unsigned char* prep_msg;

    prep_msg = PyMem_Malloc(msg_len);
    if (!prep_msg)
        return NULL;

    memcpy(prep_msg, msg, msg_len);

    return prep_msg;
}

static void
fourwise_sha1hmac_openssl(unsigned char* message, int message_length, unsigned char* keys, int key_length, unsigned char* hmacs)
{
    int i;

    for (i = 0; i < 4; i++)
        HMAC(EVP_sha1(), &keys[i * key_length], key_length, message, message_length, &hmacs[i * 20], NULL);
}

static void
fourwise_md5hmac_openssl(unsigned char* message, int message_length, unsigned char* keys, int key_length, unsigned char* hmacs)
{
    int i;

    for (i = 0; i < 4; i++)
        HMAC(EVP_md5(), &keys[i * key_length], key_length, message, message_length, &hmacs[i * 16], NULL);
}

static int
EAPOLCracker_init(EAPOLCracker *self, PyObject *args, PyObject *kwds)
{
    char *keyscheme;
    unsigned char *pke, *keymic, *eapolframe;
    int pke_len, keymic_size, eapolframe_size;

    self->eapolframe = self->pke = NULL;
    if (!PyArg_ParseTuple(args, "ss#s#s#", &keyscheme, &pke, &pke_len, &keymic, &keymic_size, &eapolframe, &eapolframe_size))
        return -1;

    if (pke_len != 100)
    {
        PyErr_SetString(PyExc_ValueError, "PKE must be a string of exactly 100 bytes.");
        return -1;
    }
    self->pke = fourwise_sha1hmac_prepare(pke, 100);
    if (!self->pke)
    {
        PyErr_NoMemory();
        return -1;
    }

    if (keymic_size != 16)
    {
        PyErr_SetString(PyExc_ValueError, "KeyMIC must a string of 16 bytes.");
        return -1;
    }
    memcpy(self->keymic, keymic, 16);

    self->eapolframe_size = eapolframe_size;

    if (strcmp(keyscheme, "HMAC_MD5_RC4") == 0)
    {
        self->eapolframe = fourwise_md5hmac_prepare(eapolframe, eapolframe_size);
        self->keyscheme = HMAC_MD5_RC4;
    } else if (strcmp(keyscheme, "HMAC_SHA1_AES") == 0) {
        self->eapolframe = fourwise_sha1hmac_prepare(eapolframe, eapolframe_size);
        self->keyscheme = HMAC_SHA1_AES;
    } else {
        PyErr_SetString(PyExc_ValueError, "Invalid key-scheme.");
        return -1;
    }

    if (!self->eapolframe)
    {
        PyErr_NoMemory();
        return -1;
    }

    return 0;
}

static void
EAPOLCracker_dealloc(EAPOLCracker *self)
{
    if (self->pke)
        PyMem_Free(self->pke);
    if (self->eapolframe)
        PyMem_Free(self->eapolframe);
    self->ob_type->tp_free((PyObject*)self);
}

PyDoc_STRVAR(EAPOLCracker_solve__doc__,
    "solve(object) -> solution or None\n\n"
    "Try to find the password that corresponds to this instance's EAPOL-session.\n");

static PyObject*
EAPOLCracker_solve(EAPOLCracker *self, PyObject *args)
{
    PyObject *result_seq, *pmkbuffer_obj, *solution_obj;
    unsigned char *pmkbuffer, *t, kck[4][16], md5mics[4][16], sha1mics[4][20];
    Py_ssize_t buffersize;
    int i, j, solution_idx;
    PyBufferProcs *pb;

    pmkbuffer = NULL;

    if (!PyArg_ParseTuple(args, "O", &result_seq))
        return NULL;

    /* Try to get the PMKs through the object's buffer-protocol (faster) */
    if (PyObject_HasAttrString(result_seq, "getpmkbuffer"))
    {
        pmkbuffer_obj = PyObject_CallMethod(result_seq, "getpmkbuffer", NULL);
        if (pmkbuffer_obj)
        {
            if (!PyBuffer_Check(pmkbuffer_obj))
            {
                PyErr_SetString(PyExc_ValueError, "The object's .getpmkbuffer() must provide a buffer-object.");
                Py_DECREF(pmkbuffer_obj);
                return NULL;
            } else {
                pb = pmkbuffer_obj->ob_type->tp_as_buffer;
                buffersize = (*pb->bf_getreadbuffer)(pmkbuffer_obj, 0, (void**)&t);
                if (buffersize % 32 != 0)
                {
                    PyErr_SetString(PyExc_ValueError, "Object's buffer's length is not a multiple of 32.");
                    Py_DECREF(pmkbuffer_obj);
                    return NULL;
                }
                /* Align size to 4*32 for SSE2 */
                pmkbuffer = PyMem_Malloc(buffersize + 128 - (buffersize % 128));
                if (!pmkbuffer)
                {
                    PyErr_NoMemory();
                    Py_DECREF(pmkbuffer_obj);
                    return NULL;
                }
                memcpy(pmkbuffer, t, buffersize);
                Py_DECREF(pmkbuffer_obj);
            }
        } else {
            /* Pass the error from getpmkbuffer() */
            return NULL;
        }
    } else {
        /* Basic sequence-like objects must be unpacked */
        buffersize = Cracker_unpack(result_seq, &pmkbuffer);
        if (!pmkbuffer)
            return NULL;
    }

    solution_idx = -1;
    Py_BEGIN_ALLOW_THREADS;
    for (i = 0; i < buffersize / 32 && solution_idx == -1; i += 4)
    {
        fourwise_sha1hmac(self->pke, 100, &pmkbuffer[i*32], 32, (unsigned char*)&sha1mics);
        for (j = 0; j < 4; j++)
            memcpy(kck[j], sha1mics[j], 16);
        if (self->keyscheme == HMAC_MD5_RC4)
        {
            fourwise_md5hmac(self->eapolframe, self->eapolframe_size, (unsigned char*)&kck, 16, (unsigned char*)&md5mics);
            for (j = 0; j < 4 && i + j < buffersize / 32; j++)
                if (memcmp(&md5mics[j], self->keymic, 16) == 0)
                {
                    solution_idx = i + j;
                    break;
                }
        } else
        {
            fourwise_sha1hmac(self->eapolframe, self->eapolframe_size, (unsigned char*)&kck, 16, (unsigned char*)&sha1mics);
            for (j = 0; j < 4 && i + j < buffersize / 32; j++)
                if (memcmp(&sha1mics[j], self->keymic, 16) == 0)
                {
                    solution_idx = i + j;
                    break;
                }
        }
    }
    Py_END_ALLOW_THREADS;

    PyMem_Free(pmkbuffer);

    if (solution_idx == -1)
    {
        solution_obj = Py_None;
        Py_INCREF(solution_obj);
    } else {
        solution_obj = PySequence_GetItem(result_seq, solution_idx);
    }

    return solution_obj;
}

/*
 ###########################################################################

 CCMPCracker

 ###########################################################################
 */

static int
CCMPCracker_init(CCMPCracker *self, PyObject *args, PyObject *kwds)
{
    unsigned char *pkeptr, *msgblock, *sourcemac, *pn, pke[100];
    Py_ssize_t pkelen, msglen, sourcemaclen, pnlen;

    self->pke1 = self->pke2 = NULL;
    pkelen = msglen = sourcemaclen = pnlen = 0;
    if (!PyArg_ParseTuple(args, "s#s#s#s#", &pkeptr, &pkelen, &msgblock, &msglen,
                          &sourcemac, &sourcemaclen, &pn, &pnlen))
        return -1;

    if (pkelen != 100)
    {
        PyErr_SetString(PyExc_ValueError, "PKE must be a string of exactly 100 bytes.");
        return -1;
    }
    memcpy(pke, pkeptr, 100);

    /* Key Computation Block to compute Temporal Key */
    pke[99] = 1;
    self->pke1 = fourwise_sha1hmac_prepare(pke, 100);
    if (!self->pke1)
    {
        PyErr_NoMemory();
        return -1;
    }

    pke[99] = 2;
    self->pke2 = fourwise_sha1hmac_prepare(pke, 100);
    if (!self->pke2)
    {
        PyErr_NoMemory();
        return -1;
    }

    /* First 6 bytes in an CCMP-encrypted message */
    if (msglen < 6)
    {
        PyErr_SetString(PyExc_ValueError, "Message must a string of at least six bytes.");
        return -1;
    }
    memcpy(self->S0, msgblock, 6);

    /* We are looking for S0 that decrypts C0 to a LLC+SNAP-header (AAAA03000000).
     As C0 ^ S0 = P0, therefor C0 ^ P0 = S0. We xor the ciphertext with the plaintext
     to get the key (S0) we are looking for.
    */
    self->S0[0] ^= 0xAA; self->S0[1] ^= 0xAA; self->S0[2] ^= 0x03;

    if (sourcemaclen != 6)
    {
        PyErr_SetString(PyExc_ValueError, "Source-MAC must be a string of six bytes.");
        return -1;
    }
    memcpy(self->A0.nonce.a2, sourcemac, 6);

    if (pnlen != 6)
    {
        PyErr_SetString(PyExc_ValueError, "Counter must be a string of 6 bytes.");
        return -1;
    }
    memcpy(self->A0.nonce.pn, pn, 6);

    self->A0.flags = 1;           /* flags = L' = 2 - 1 = 1 */
    self->A0.nonce.priority = 0;  /* priority is always zero */
    self->A0.counter = 1 << 8;    /* counter for first block */

    return 0;
}

static void
CCMPCracker_dealloc(CCMPCracker *self)
{
    if (self->pke1)
        PyMem_Free(self->pke1);
    if (self->pke2)
        PyMem_Free(self->pke2);
    self->ob_type->tp_free((PyObject*)self);
}

#ifdef COMPILE_SSE2
    /* A note regarding the following function:

       The Temporal Key is derived from the Pairwise Key Expansion Block (PKE)
       using PRF-384. As HMAC-SHA1 produces 20 bytes of output per call and
       the Temporal Key is 32 bytes into the PRF-stream, the first eight bytes
       of the TK are produced by the second while the last eight bytes are produced
       by the third round of PRF-384.
       A naive solution requires two complete calls to HMAC-SHA1, which in turn
       requires five rounds of SHA1 each.

       As the key to HMAC-SHA1 (the PMK) is the same for both rounds and the message
       (the PKE) only differs in the second block (where the counter is), we can
       optimize computing the TK by re-using the SHA1-state from the OPAD and the
       SHA1-state from the IPAD+(first block of PKE).
       Thereby we only need 5+2 rounds of SHA1 instead of 5+5.
    */
    static void
    fourwise_pke2tk_sse2(unsigned char *pke1, unsigned char *pke2, unsigned char *pmkbuffer, Py_ssize_t keycount, unsigned char *tkbuffer)
    {
        Py_ssize_t i;
        int j, k;
        uint32_t wrkbuf[4*80]        __attribute__ ((aligned (16)));
        uint32_t ipad[16][4]         __attribute__ ((aligned (16)));
        uint32_t opad[16][4]         __attribute__ ((aligned (16)));
        uint32_t digest[16][4]       __attribute__ ((aligned (16)));
        fourwise_sha1_ctx ctx, ipad_ctx, opad_ctx;

        /* The PKE-data is aligned to 16 bytes inside the allocated buffer so re-align the pointer now. */
        pke1 = pke1 + 16 - ((long)pke1 % 16);
        pke2 = pke2 + 16 - ((long)pke2 % 16);

        /* Initialize static values for inner hash block */
        for (j = 0; j < 4; j++)
        {
            digest[ 5][j] = 0x80;       /* Terminator bit */
            digest[15][j] = 0xA0020000; /* size = (64 + 20) * 8 */
            for (k = 6; k < 15; k++)
                digest[k][j] = 0;
        }
        memset((unsigned char*)ipad, 0x36, sizeof(ipad));
        memset((unsigned char*)opad, 0x5C, sizeof(opad));

        for (i = 0; i < keycount; i += 4)
        {
            /* Second round of PRF-384 to compute first half of TK */

            /* HMAC-SHA1 step 1: Inner hash = SHA1((IPAD ^ PMK) // PKE) */
            fourwise_sha1_init(&ctx);

            /* Mix-in key (PMK) */
            for (j = 0; j < 4; j++)
                for (k = 0; k < 8; k++)
                    ipad[k][j] = ((uint32_t*)pmkbuffer)[(i + j) * 8 + k] ^ 0x36363636;
            sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)ipad, wrkbuf);

            /* Mix-in first block of PKE */
            sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)(pke1), wrkbuf);

            /* Copy state before mixing in second block */
            memcpy((unsigned char*)&ipad_ctx, (unsigned char*)&ctx, sizeof(ipad_ctx));
            sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)(pke1 + 64*4), wrkbuf);

            /* First hash done */
            sse2_sha1_finalize((uint32_t*)&ctx, (uint32_t*)&digest);

            /* Step 2: Outer hash = SHA1((OPAD ^ PMK) // inner hash) */
            fourwise_sha1_init(&ctx);
            for (j = 0; j < 4; j++)
                for (k = 0; k < 8; k++)
                    opad[k][j] = ((uint32_t*)pmkbuffer)[(i + j) * 8 + k] ^ 0x5C5C5C5C;
            sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)opad, wrkbuf);

            /* Copy this state before mixing in the inner hash */
            memcpy((unsigned char*)&opad_ctx, (unsigned char*)&ctx, sizeof(opad_ctx));
            sse2_sha1_update((uint32_t*)&ctx, (uint32_t*)&digest, wrkbuf);

            /* Second round of PRF-384 done -> First 8 bytes of TK */
            sse2_sha1_finalize((uint32_t*)&ctx, (uint32_t*)&digest);
            for (j = 0; j < 4; j++)
                for (k = 0; k < 2; k++)
                    ((uint32_t*)tkbuffer)[(i + j) * 4 + k + 0] = digest[k + 3][j];

            /* Quick third round of PRF-384 */
            sse2_sha1_update((uint32_t*)&ipad_ctx, (uint32_t*)(pke2 + 64*4), wrkbuf);
            sse2_sha1_finalize((uint32_t*)&ipad_ctx, (uint32_t*)&digest);
            sse2_sha1_update((uint32_t*)&opad_ctx, (uint32_t*)&digest, wrkbuf);

            /* Third round of PRF-384 done -> Last 8 bytes of TK */
            sse2_sha1_finalize((uint32_t*)&opad_ctx, (uint32_t*)&digest);
            for (j = 0; j < 4; j++)
                for (k = 0; k < 2; k++)
                    ((uint32_t*)tkbuffer)[(i + j) * 4 + k + 2] = digest[k + 0][j];
        }
    }
#endif /* COMPILE_SSE2 */

static void
fourwise_pke2tk_openssl(unsigned char *pke1, unsigned char *pke2, unsigned char *pmkbuffer, Py_ssize_t keycount, unsigned char *tkbuffer)
{
    Py_ssize_t i;
    int j;
    unsigned char pad[64], hash[20];
    SHA_CTX ctx, ipad_ctx, opad_ctx;

    /* See the comments above and inside fourwise_pke2tk_sse2() */

    for (i = 0; i < keycount; i++)
    {
        /* Second round of PRF-384 to compute first half of TK */
        SHA1_Init(&ctx);

        memset(pad, 0x36, sizeof(pad));
        for (j = 0; j < 32; j++)
            pad[j] ^= pmkbuffer[i * 32 + j];
        SHA1_Update(&ctx, pad, sizeof(pad));

        SHA1_Update(&ctx, pke1, 64);

        memcpy((unsigned char*)&ipad_ctx, (unsigned char*)&ctx, sizeof(ipad_ctx));
        SHA1_Update(&ctx, pke1 + 64, 100 - 64);

        SHA1_Final(hash, &ctx);

        SHA1_Init(&ctx);
        memset(pad, 0x5C, sizeof(pad));
        for (j = 0; j < 32; j++)
            pad[j] ^= pmkbuffer[i * 32 + j];
        SHA1_Update(&ctx, pad, sizeof(pad));

        memcpy((unsigned char*)&opad_ctx, (unsigned char*)&ctx, sizeof(opad_ctx));
        SHA1_Update(&ctx, hash, 20);

        /* Second round of PRF-384 done -> First 8 bytes of TK */
        SHA1_Final(hash, &ctx);
        memcpy(&tkbuffer[16 * i + 0], hash + 12, 8);

        /* Quick third round of PRF-384 */
        SHA1_Update(&ipad_ctx, pke2 + 64, 100 - 64);
        SHA1_Final(hash, &ipad_ctx);
        SHA1_Update(&opad_ctx, hash, 20);

        /* Third round of PRF-384 done -> Last 8 bytes of TK */
        SHA1_Final(hash, &opad_ctx);
        memcpy(&tkbuffer[16 * i + 8], hash + 0, 8);
    }
}

static Py_ssize_t
ccmp_encrypt_openssl(const unsigned char *A0, const unsigned char *S0, const unsigned char *tkbuffer, Py_ssize_t keycount)
{
    Py_ssize_t i;
    AES_KEY aes_ctx;
    unsigned char crib[16];

    for (i = 0; i < keycount; i++)
    {
        /* Use TK to encrypt A0 into S0 */
        AES_set_encrypt_key(&tkbuffer[i * 16], 128, &aes_ctx);
        AES_encrypt(A0, crib, &aes_ctx);
        if (memcmp(crib, S0, 6) == 0)
            return i;
    }

    return -1;
}

PyDoc_STRVAR(CCMPCracker_solve__doc__,
             "solve(object) -> solution or None\n\n"
             "Try to find the password that corresponds to this instance's CCMP-encrypted message.\n");

static PyObject*
CCMPCracker_solve(CCMPCracker *self, PyObject *args)
{
    PyObject *result_seq, *pmkbuffer_obj, *solution_obj;
    unsigned char *pmkbuffer, *t, *tkbuffer;
    Py_ssize_t buffersize, keycount, solution_idx;
    PyBufferProcs *pb;

    buffersize = keycount = 0;

    if (!PyArg_ParseTuple(args, "O", &result_seq))
        return NULL;

    /* Try to get the PMKs through the object's buffer-protocol (faster) */
    if (PyObject_HasAttrString(result_seq, "getpmkbuffer"))
    {
        pmkbuffer_obj = PyObject_CallMethod(result_seq, "getpmkbuffer", NULL);
        if (pmkbuffer_obj)
        {
            if (!PyBuffer_Check(pmkbuffer_obj))
            {
                PyErr_SetString(PyExc_ValueError, "The object's .getpmkbuffer() must provide a buffer-object.");
                Py_DECREF(pmkbuffer_obj);
                return NULL;
            } else {
                pb = pmkbuffer_obj->ob_type->tp_as_buffer;
                buffersize = (*pb->bf_getreadbuffer)(pmkbuffer_obj, 0, (void**)&t);
                if (buffersize % 32 != 0)
                {
                    PyErr_SetString(PyExc_ValueError, "Object's buffer's length is not a multiple of 32.");
                    Py_DECREF(pmkbuffer_obj);
                    return NULL;
                }
                /* Align size to 4*32 for SSE2 */
                pmkbuffer = PyMem_Malloc(buffersize + 128 - (buffersize % 128));
                if (!pmkbuffer)
                {
                    PyErr_NoMemory();
                    Py_DECREF(pmkbuffer_obj);
                    return NULL;
                }
                memcpy(pmkbuffer, t, buffersize);
                Py_DECREF(pmkbuffer_obj);
            }
        } else {
            /* Pass the error from getpmkbuffer() */
            return NULL;
        }
    } else {
        /* Basic sequence-like objects must be unpacked */
        buffersize = Cracker_unpack(result_seq, &pmkbuffer);
        if (!pmkbuffer)
            return NULL;
    }
    keycount = buffersize / 32;

    tkbuffer = PyMem_Malloc((keycount + 3) * 16);
    if (!tkbuffer)
    {
        PyMem_Free(pmkbuffer);
        PyErr_NoMemory();
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS;
    /* Compute TKs from PMKs and PKE */
    fourwise_pke2tk(self->pke1, self->pke2, pmkbuffer, keycount, tkbuffer);
    /* Try to find the TK that encrypts A0 to S0 */
    solution_idx = ccmp_encrypt((unsigned char*)&self->A0, (unsigned char*)&self->S0, tkbuffer, keycount);
    Py_END_ALLOW_THREADS;

    PyMem_Free(pmkbuffer);
    PyMem_Free(tkbuffer);

    if (solution_idx == -1)
    {
        solution_obj = Py_None;
        Py_INCREF(solution_obj);
    } else {
        solution_obj = PySequence_GetItem(result_seq, solution_idx);
    }

    return solution_obj;
}

/*
    ###########################################################################

    CowpattyResult

    ###########################################################################
*/

static void
CowpattyResult_dealloc(CowpattyResult* self)
{
    if (self->buffer)
        PyMem_Free(self->buffer);
    self->ob_type->tp_free((PyObject*)self);
}

static Py_ssize_t
CowpattyResult_bf_getreadbuffer(CowpattyResult* self, Py_ssize_t segment, void **ptrptr)
{
    if (segment != 0)
    {
        PyErr_SetString(PyExc_SystemError, "Invalid segment to CowpattyResult-buffer.");
        return -1;
    }
    ptrptr[0] = self->buffer;
    return self->itemcount * 32;
}

static Py_ssize_t
CowpattyResult_bf_getsegcount(CowpattyResult* self, Py_ssize_t *lenp)
{
    if (lenp)
        lenp[0] = self->itemcount * 32;
    return 1;
}

static Py_ssize_t
CowpattyResult_sq_length(CowpattyResult* self)
{
    return self->itemcount;
}

static PyObject*
CowpattyResult_sq_item(CowpattyResult* self, Py_ssize_t idx)
{
    PyObject *result;
    int entrylen, i, consumed;

    if (idx < 0 || idx > self->itemcount - 1)
    {
        PyErr_SetString(PyExc_IndexError, "Index out of bounds for CowpattyResult.");
        return NULL;
    }

    consumed = 0;
    for (i = 0; i < idx; i++)
        consumed += (int)self->buffer[self->itemcount * 32 + consumed];

    result = PyTuple_New(2);
    if (!result)
    {
        PyErr_NoMemory();
        return NULL;
    }

    entrylen = (int)self->buffer[self->itemcount * 32 + consumed];
    PyTuple_SetItem(result, 0, PyString_FromStringAndSize((char*)&self->buffer[self->itemcount * 32 + consumed + 1], entrylen - 1));
    PyTuple_SetItem(result, 1, PyString_FromStringAndSize((char*)&self->buffer[idx * 32], 32));

    return result;
}

static PyObject*
CowpattyResult_iter(CowpattyResult* self)
{
    Py_INCREF(self);
    return (PyObject*)self;
}

static PyObject*
CowpattyResult_iternext(CowpattyResult *self)
{
    PyObject *result;
    int entrylen;

    if (self->current_idx >= self->itemcount)
        return NULL;

    result = PyTuple_New(2);
    if (!result)
    {
        PyErr_NoMemory();
        return NULL;
    }

    entrylen = (int)self->current_ptr[0];
    PyTuple_SetItem(result, 0, PyString_FromStringAndSize((char*)self->current_ptr + 1, entrylen - 1));
    PyTuple_SetItem(result, 1, PyString_FromStringAndSize((char*)self->buffer + self->current_idx * 32, 32));

    self->current_ptr += entrylen;
    self->current_idx += 1;

    return result;
}

PyDoc_STRVAR(CowpattyResult_getpmkbuffer__doc__,
    "getpmkbuffer() -> buffer-object\n\n"
    "Return a buffer-object to directly access the PMKs held by this object.");

static PyObject*
CowpattyResult_getpmkbuffer(PyObject *self, PyObject *args)
{
    return PyBuffer_FromObject(self, 0, Py_END_OF_BUFFER);
}

/*
    ###########################################################################

    CowpattyFile

    ###########################################################################
*/

PyDoc_STRVAR(CowpattyFile_gencowpentries__doc__,
    "gencowpentries(iterable) -> string\n\n"
    "Generate a data-string in cowpatty-like format from a iterable of (password-PMK)-tuples.");

static PyObject *
CowpattyFile_gencowpentries(PyObject *self, PyObject *args)
{
    PyObject *result_seq, *result_obj, *passwd_obj, *pmk_obj, *result;
    char *passwd, *pmk;
    unsigned char *cowpbuffer, *t;
    unsigned int passwd_length, buffer_offset, buffersize;

    if (!PyArg_ParseTuple(args, "O", &result_seq))
        return NULL;

    result_seq = PyObject_GetIter(result_seq);
    if (!result_seq)
    {
        PyErr_NoMemory();
        return NULL;
    }

    cowpbuffer = NULL;
    passwd_obj = pmk_obj = NULL;
    buffer_offset = buffersize = 0;
    while ((result_obj = PyIter_Next(result_seq)))
    {
        if (buffersize - buffer_offset < 1+63+32)
        {
            buffersize += 1024*10;
            t = PyMem_Realloc(cowpbuffer, buffersize);
            if (!t)
            {
                PyErr_NoMemory();
                goto errout;
            }
            cowpbuffer = t;
        }
        passwd_obj = PySequence_GetItem(result_obj, 0);
        if (!passwd_obj)
        {
            PyErr_NoMemory();
            goto errout;
        }
        passwd = PyString_AsString(passwd_obj);
        passwd_length = PyString_Size(passwd_obj);
        if (passwd == NULL || passwd_length < 8 || passwd_length > 63)
        {
            PyErr_SetString(PyExc_ValueError, "All passwords must be strings between 8 and 63 characters");
            Py_DECREF(passwd_obj);
            goto errout;
        }
        pmk_obj = PySequence_GetItem(result_obj, 1);
        if (!pmk_obj)
        {
            PyErr_NoMemory();
            Py_DECREF(passwd_obj);
            goto errout;
        }
        pmk = PyString_AsString(pmk_obj);
        if (pmk == NULL || PyString_Size(pmk_obj) != 32)
        {
            PyErr_SetString(PyExc_ValueError, "All PMKs must be strings of 32 characters");
            Py_DECREF(passwd_obj);
            Py_DECREF(pmk_obj);
            goto errout;
        }

        cowpbuffer[buffer_offset + 0] = passwd_length + 32 + 1;
        memcpy(&cowpbuffer[buffer_offset + 1], passwd, passwd_length);
        memcpy(&cowpbuffer[buffer_offset + 1 + passwd_length], pmk, 32);

        Py_DECREF(passwd_obj);
        Py_DECREF(pmk_obj);
        Py_DECREF(result_obj);

        buffer_offset += passwd_length + 32 + 1;
    }
    Py_DECREF(result_seq);

    result = PyString_FromStringAndSize((char*)cowpbuffer, buffer_offset);

    PyMem_Free(cowpbuffer);

    return result;

    errout:
    Py_DECREF(result_obj);
    Py_DECREF(result_seq);
    PyMem_Free(cowpbuffer);
    return NULL;
}

PyDoc_STRVAR(CowpattyFile_unpackcowpentries__doc__,
    "unpackcowpentries(string) -> (CowpattyResult, string)\n\n"
    "Unpack a data-string in cowpatty-like format and return a tuple with results and unfinished tail.");

static PyObject *
CowpattyFile_unpackcowpentries(PyObject *self, PyObject *args)
{
    CowpattyResult *iter;
    PyObject *result;
    int i, stringsize, consumed, entrylen, itemcount;
    char *string;

    if (!PyArg_ParseTuple(args, "s#", &string, &stringsize))
        return NULL;

    if (stringsize < 1+8+32 || string[0] > stringsize)
    {
        PyErr_SetString(PyExc_ValueError, "Input-string is too short.");
        return NULL;
    }

    itemcount = consumed = 0;
    do
    {
        entrylen = (int)string[consumed];
        if (entrylen < 1+8+32 || entrylen > 1+63+32)
        {
            PyErr_Format(PyExc_ValueError, "Entry of invalid size: %i", entrylen);
            return NULL;
        }
        if (consumed + entrylen > stringsize)
            break;
        consumed += entrylen;
        itemcount += 1;
    } while (consumed < stringsize);

    iter = (CowpattyResult*)PyObject_New(CowpattyResult, &CowpattyResult_type);
    if (!iter)
    {
        PyErr_NoMemory();
        return NULL;
    }
    iter->buffersize = consumed;
    iter->current_idx = 0;
    iter->itemcount = itemcount;

    iter->buffer = PyMem_Malloc(consumed);
    if (!iter->buffer)
    {
        Py_DECREF(iter);
        PyErr_NoMemory();
        return NULL;
    }
    iter->current_ptr = iter->buffer + (itemcount * 32);

    consumed = 0;
    for (i = 0; i < itemcount; i++)
    {
        entrylen = (int)string[consumed];
        memcpy(&iter->buffer[32 * i], &string[consumed + entrylen - 32], 32);
        iter->buffer[32 * itemcount + consumed - (32 * i)] = entrylen - 32;
        memcpy(&iter->buffer[32 * itemcount + consumed - (32 * i) + 1], &string[consumed + 1], entrylen - (32 + 1));
        consumed += entrylen;
    }

    result = PyTuple_New(2);
    if (!result)
    {
        PyErr_NoMemory();
        Py_DECREF(iter);
        return NULL;
    }
    PyTuple_SetItem(result, 0, (PyObject*)iter);
    PyTuple_SetItem(result, 1, PyString_FromStringAndSize(string + consumed, stringsize - consumed));

    return result;
}

/*
    ###########################################################################

    PcapDevice

    ###########################################################################
*/

static int
PcapDevice_init(PcapDevice *self, PyObject *args, PyObject *kwds)
{
    self->device_name = Py_None;
    Py_INCREF(Py_None);

    self->type = Py_None;
    Py_INCREF(Py_None);

    self->datalink_name = Py_None;
    Py_INCREF(Py_None);

    self->p = NULL;
    self->status = self->datalink = 0;

    return 0;
}

static void
PcapDevice_dealloc(PcapDevice *self)
{
    Py_XDECREF(self->device_name);
    Py_XDECREF(self->type);
    Py_XDECREF(self->datalink_name);
    if (self->p && self->status == 1)
        pcap_close(self->p);
    self->ob_type->tp_free((PyObject*)self);
}

PyDoc_STRVAR(PcapDevice_close__doc__,
    "close() -> None\n\n"
    "Close the instance");
static PyObject*
PcapDevice_close(PcapDevice *self, PyObject *args)
{
    if (self->status == 1)
        pcap_close(self->p);
    self->status = -1;

    Py_INCREF(Py_None);
    return Py_None;
}

static int
PcapDevice_setup(PcapDevice *self, const char* type, const char* dev)
{
    const char *dlink_name;

    self->datalink = pcap_datalink(self->p);

    dlink_name = pcap_datalink_val_to_name(self->datalink);
    if (dlink_name)
    {
        Py_DECREF(self->datalink_name);
        self->datalink_name = PyString_FromString(dlink_name);
        if (!self->datalink_name)
        {
            PyErr_NoMemory();
            return 0;
        }
    }

    Py_DECREF(self->type);
    self->type = PyString_FromString(type);
    if (!self->type)
    {
        PyErr_NoMemory();
        return 0;
    }

    Py_DECREF(self->device_name);
    self->device_name = PyString_FromString(dev);
    if (!self->device_name)
    {
        PyErr_NoMemory();
        return 0;
    }

    self->status = 1;

    return 1;
}

PyDoc_STRVAR(PcapDevice_open_live__doc__,
    "open_live(device_name) -> None\n\n"
    "Open a device for live-capture");
static PyObject*
PcapDevice_open_live(PcapDevice *self, PyObject *args)
{
    char errbuf[PCAP_ERRBUF_SIZE], *device_name;

    if (!PyArg_ParseTuple(args, "s", &device_name))
        return NULL;

    if (self->status != 0)
    {
        PyErr_SetString(PyExc_RuntimeError, "Already opened.");
        return NULL;
    }

    self->p = pcap_open_live(device_name, 65535, 1, 200, errbuf);
    if (!self->p)
    {
        PyErr_Format(PyExc_IOError, "Failed to open device '%s' (libpcap: %s)", device_name, errbuf);
        return NULL;
    }

    if (!PcapDevice_setup(self, "live", device_name))
        return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(PcapDevice_open_offline__doc__,
    "open_offline(fname) ->None\n\n"
    "Open a file for reading");
static PyObject*
PcapDevice_open_offline(PcapDevice *self, PyObject *args)
{
    char errbuf[PCAP_ERRBUF_SIZE], *fname;

    if (!PyArg_ParseTuple(args, "s", &fname))
        return NULL;

    if (self->status != 0)
    {
        PyErr_SetString(PyExc_RuntimeError, "Already opened.");
        return NULL;
    }

    self->p = pcap_open_offline(fname, errbuf);
    if (!self->p)
    {
        PyErr_Format(PyExc_IOError, "Failed to open file '%s' (libpcap: %s)", fname, errbuf);
        return NULL;
    }

    if (!PcapDevice_setup(self, "offline", fname))
        return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(PcapDevice_read__doc__,
    "read() -> tuple\n\n"
    "Read the next packet");
static PyObject*
PcapDevice_read(PcapDevice *self, PyObject *args)
{
    PyObject *result, *ts, *pckt_content;
    int ret;
    struct pcap_pkthdr *h;
    const u_char *bytes;

    if (self->status != 1)
    {
        PyErr_SetString(PyExc_RuntimeError, "Instance not ready for reading.");
        return NULL;
    }

    for (;;)
    {
        Py_BEGIN_ALLOW_THREADS;
        ret = pcap_next_ex(self->p, &h, &bytes);
        Py_END_ALLOW_THREADS;
        switch (ret)
        {
            case 0: // Timeout from live-capture
                PyErr_CheckSignals();
                if (PyErr_Occurred())
                    return NULL;
                continue;
            case 1: // OK
                pckt_content = PyString_FromStringAndSize((char*)bytes, h->caplen);
                if (!pckt_content)
                    return PyErr_NoMemory();

                ts = PyTuple_New(2);
                if (!ts)
                {
                    Py_DECREF(pckt_content);
                    return PyErr_NoMemory();
                }
                PyTuple_SetItem(ts, 0, PyLong_FromLong(h->ts.tv_sec));
                PyTuple_SetItem(ts, 1, PyLong_FromLong(h->ts.tv_usec));

                result = PyTuple_New(2);
                if (!result)
                {
                    Py_DECREF(pckt_content);
                    Py_DECREF(ts);
                    return PyErr_NoMemory();
                }
                PyTuple_SetItem(result, 0, ts);
                PyTuple_SetItem(result, 1, pckt_content);

                return result;

            case -2: // End of file
                Py_INCREF(Py_None);
                return Py_None;
            case -1: // Error
                PyErr_Format(PyExc_IOError, "libpcap-error while reading: %s", pcap_geterr(self->p));
                return NULL;
            default:
                PyErr_SetString(PyExc_IOError, "Unknown return-value from pcap_next_ex()");
                return NULL;
        }
    }

}

PyDoc_STRVAR(PcapDevice_send__doc__,
    "send(object) -> None\n\n"
    "Send an object's string-representation as a raw packet via a live device.");
static PyObject*
PcapDevice_send(PcapDevice *self, PyObject *args)
{
    char *pckt_buffer;
    Py_ssize_t pckt_size;
    PyObject *pckt, *pckt_string;

    if (self->status != 1)
    {
        PyErr_SetString(PyExc_RuntimeError, "Instance not ready for writing.");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "O", &pckt))
        return NULL;

    pckt_string = PyObject_Str(pckt);
    if (!pckt_string)
    {
        PyErr_SetString(PyExc_ValueError, "Failed to get string-representation from object.");
        return NULL;
    }

    if (PyString_AsStringAndSize(pckt_string, &pckt_buffer, &pckt_size))
    {
        Py_DECREF(pckt_string);
        return NULL;
    }

    if (pcap_sendpacket(self->p, (unsigned char*)pckt_buffer, pckt_size))
    {
        PyErr_Format(PyExc_IOError, "Failed to send packet (libpcap: %s).", pcap_geterr(self->p));
        Py_DECREF(pckt_string);
        return NULL;
    }

    Py_DECREF(pckt_string);

    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(PcapDevice_set_filter__doc__,
    "set_filter(filter_string) -> None\n\n"
    "Set a BPF-filter");
static PyObject*
PcapDevice_set_filter(PcapDevice *self, PyObject *args)
{
    struct bpf_program fp;
    char *filter_string;

    if (!PyArg_ParseTuple(args, "s", &filter_string))
        return NULL;

    if (self->status != 1)
    {
        PyErr_SetString(PyExc_RuntimeError, "Instance not opened yet");
        return NULL;
    }

    if (pcap_compile(self->p, &fp, filter_string, 0, 0))
    {
        PyErr_Format(PyExc_ValueError, "Failed to compile BPF-filter (libpcap: %s).", pcap_geterr(self->p));
        return NULL;
    }

    if (pcap_setfilter(self->p, &fp))
    {
        PyErr_Format(PyExc_RuntimeError, "Failed to set BPF-filter (libpcap: %s)", pcap_geterr(self->p));
        pcap_freecode(&fp);
        return NULL;
    }
    pcap_freecode(&fp);

    Py_INCREF(Py_None);
    return Py_None;
}


/*
    ###########################################################################

    Module functions

    ###########################################################################
*/

PyDoc_STRVAR(cpyrit_getPlatform__doc__,
    "getPlatform() -> string\n\n"
    "Determine CPU-type");

static PyObject *
cpyrit_getPlatform(PyObject *self, PyObject *args)
{
    Py_INCREF(PlatformString);
    return PlatformString;
}

PyDoc_STRVAR(cpyrit_grouper__doc__,
    "grouper(string, groupsize) -> tuple\n\n"
    "Group a large string into a tuple of strings of equal size each");

static PyObject *
cpyrit_grouper(PyObject *self, PyObject *args)
{
    PyObject *result;
    int i, stringsize, groupsize;
    char *string;

    if (!PyArg_ParseTuple(args, "s#i", &string, &stringsize, &groupsize))
        return NULL;

    if (stringsize % groupsize != 0)
    {
        PyErr_SetString(PyExc_ValueError, "Invalid size of input string.");
        return NULL;
    }

    result = PyTuple_New(stringsize / groupsize);
    if (!result)
    {
        PyErr_NoMemory();
        return NULL;
    }
    for (i = 0; i < stringsize / groupsize; i++)
        PyTuple_SetItem(result, i, PyString_FromStringAndSize(&string[i * groupsize], groupsize));

    return result;
}

PyDoc_STRVAR(cpyrit_pyr2halfpack__doc__,
    "pyr2halfpack(results) -> tuple\n\n"
    "Pack a sequence of (password, pmk)-tuples to a password- and a pmk-string");

static PyObject *
cpyrit_pyr2halfpack(PyObject *self, PyObject *args)
{
    PyObject *result, *seq, *iter, *entry, *item;
    int buffercount, itemcount, pwsize;
    unsigned char *pwbuffer, *pmkbuffer, *pwptr, *t;

    pwbuffer = pwptr = pmkbuffer = NULL;
    buffercount = itemcount = 0;
    result = NULL;

    if (!PyArg_ParseTuple(args, "O", &seq))
        return NULL;

    iter = PyObject_GetIter(seq);
    if (!iter)
    {
        PyErr_SetString(PyExc_ValueError, "Parameter must be a iterable of (password, PMK)-sequences.");
        return NULL;
    }

    while ((entry = PyIter_Next(iter)))
    {
        if (buffercount <= itemcount)
        {
            buffercount += 100000;
            t = PyMem_Realloc(pwbuffer, buffercount*(64+1));
            if (!t)
            {
                PyErr_NoMemory();
                Py_DECREF(entry);
                goto out;
            }
            pwptr = t + (int)(pwptr - pwbuffer);
            pwbuffer = t;
            t = PyMem_Realloc(pmkbuffer, buffercount*32);
            if (!t)
            {
                PyErr_NoMemory();
                Py_DECREF(entry);
                goto out;
            }
            pmkbuffer = t;
        }

        item = PySequence_GetItem(entry, 0);
        if (!item)
        {
            PyErr_SetString(PyExc_ValueError, "Expected password as first item in a sequence-object.");
            Py_DECREF(entry);
            goto out;
        }
        t = (unsigned char*)PyString_AsString(item);
        pwsize = PyString_Size(item);
        if (t == NULL || pwsize < 8 || pwsize > 64)
        {
            PyErr_SetString(PyExc_ValueError, "Passwords must be strings of 8-64 characters.");
            Py_DECREF(entry);
            Py_DECREF(item);
            goto out;
        }
        memcpy(pwptr, t, pwsize);
        pwptr[pwsize] = '\n';
        pwptr += pwsize + 1;
        Py_DECREF(item);

        item = PySequence_GetItem(entry, 1);
        if (!item)
        {
            PyErr_SetString(PyExc_ValueError, "Expected PMK as second item in a sequence-object.");
            Py_DECREF(entry);
            goto out;
        }
        t = (unsigned char*)PyString_AsString(item);
        if (t == NULL || PyString_Size(item) != 32)
        {
            PyErr_SetString(PyExc_ValueError, "PMKs must be strings of 32 characters.");
            Py_DECREF(entry);
            Py_DECREF(item);
            goto out;
        }
        memcpy(pmkbuffer + itemcount*32, t, 32);
        Py_DECREF(item);

        itemcount += 1;
        Py_DECREF(entry);
    }

    result = PyTuple_New(2);
    if (!result)
    {
        PyErr_NoMemory();
        goto out;
    }

    if (itemcount > 0)
        pwptr -= 1;
    item = PyString_FromStringAndSize((char*)pwbuffer, (int)(pwptr - pwbuffer));
    if (!item)
    {
        PyErr_NoMemory();
        Py_DECREF(result);
        goto out;
    }
    PyTuple_SetItem(result, 0, item);

    item = PyString_FromStringAndSize((char*)pmkbuffer, itemcount*32);
    if (!item)
    {
        PyErr_NoMemory();
        Py_DECREF(result);
        goto out;
    }
    PyTuple_SetItem(result, 1, item);

    out:
    Py_DECREF(iter);
    if (pmkbuffer)
        PyMem_Free(pmkbuffer);
    if (pwbuffer)
        PyMem_Free(pwbuffer);

    return result;
}

/*
    ###########################################################################

    Class definitions

    ###########################################################################
*/


static PyMethodDef CPUDevice_methods[] =
{
    {"solve", (PyCFunction)CPUDevice_solve, METH_VARARGS, CPUDevice_solve__doc__},
    {NULL, NULL}
};

static PyTypeObject CPUDevice_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cpu.CPUDevice",    /*tp_name*/
    sizeof(CPUDevice),          /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    0,                          /*tp_dealloc*/
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
    CPUDevice_methods,          /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    0,                          /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMethodDef EAPOLCracker_methods[] =
{
    {"solve", (PyCFunction)EAPOLCracker_solve, METH_VARARGS, EAPOLCracker_solve__doc__},
    {NULL, NULL}
};

static PyTypeObject EAPOLCracker_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cpu.EAPOLCracker",  /*tp_name*/
    sizeof(EAPOLCracker),       /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    (destructor)EAPOLCracker_dealloc,   /*tp_dealloc*/
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
    EAPOLCracker_methods,       /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)EAPOLCracker_init,/*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMethodDef CCMPCracker_methods[] =
{
    {"solve", (PyCFunction)CCMPCracker_solve, METH_VARARGS, CCMPCracker_solve__doc__},
    {NULL, NULL}
};

static PyTypeObject CCMPCracker_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cpu.CCMPCracker",  /*tp_name*/
    sizeof(CCMPCracker),        /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    (destructor)CCMPCracker_dealloc, /*tp_dealloc*/
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
    CCMPCracker_methods,        /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)CCMPCracker_init, /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMethodDef CowpattyResult_methods[] =
{
    {"getpmkbuffer", CowpattyResult_getpmkbuffer, METH_NOARGS, CowpattyResult_getpmkbuffer__doc__},
    {NULL, NULL}
};

static PyBufferProcs CowpattyResults_buffer_procs = {
    (readbufferproc)CowpattyResult_bf_getreadbuffer, /* bf_getreadbuffer */
    0,                                               /* bf_getwritebuffer */
    (segcountproc)CowpattyResult_bf_getsegcount,     /* bf_getsegcount */
    0                                                /* bf_getcharbuffer */
};

static PySequenceMethods CowpattyResult_seq_methods = {
    (lenfunc)CowpattyResult_sq_length,    /* sq_length */
    0,                                    /* sq_concat */
    0,                                    /* sq_repeat */
    (ssizeargfunc)CowpattyResult_sq_item, /* sq_item */
    0,                                    /* sq_ass_item */
    0,                                    /* sq_contains */
    0,                                    /* sq_inplace_concat */
    0                                     /* sq_inplace_repeat */
};

static PyTypeObject CowpattyResult_type = {
    PyObject_HEAD_INIT(NULL)
    0,                            /*ob_size*/
    "_cpyrit_cpu.CowpattyResult", /*tp_name*/
    sizeof(CowpattyResult),       /*tp_basicsize*/
    0,                            /*tp_itemsize*/
    (destructor)CowpattyResult_dealloc, /*tp_dealloc*/
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
    (getiterfunc)CowpattyResult_iter,      /*tp_iter*/
    (iternextfunc)CowpattyResult_iternext, /*tp_iternext*/
    CowpattyResult_methods,     /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    0,                          /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMethodDef CowpattyFile_methods[] =
{
    {"genCowpEntries", CowpattyFile_gencowpentries, METH_VARARGS, CowpattyFile_gencowpentries__doc__},
    {"unpackCowpEntries", CowpattyFile_unpackcowpentries, METH_VARARGS, CowpattyFile_unpackcowpentries__doc__},
    {NULL, NULL}
};

static PyTypeObject CowpattyFile_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cpu.CowpattyFile", /*tp_name*/
    sizeof(CowpattyFile),       /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    0,                          /*tp_dealloc*/
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
    CowpattyFile_methods,       /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    0,                          /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

static PyMemberDef PcapDevice_members[] =
{
    {"deviceName", T_OBJECT, offsetof(PcapDevice, device_name), READONLY},
    {"type", T_OBJECT, offsetof(PcapDevice, type), READONLY},
    {"datalink", T_INT, offsetof(PcapDevice, datalink), READONLY},
    {"datalink_name", T_OBJECT, offsetof(PcapDevice, datalink_name), READONLY},
    {NULL}
};

static PyMethodDef PcapDevice_methods[] =
{
    {"open_live", (PyCFunction)PcapDevice_open_live, METH_VARARGS, PcapDevice_open_live__doc__},
    {"open_offline", (PyCFunction)PcapDevice_open_offline, METH_VARARGS, PcapDevice_open_offline__doc__},
    {"close", (PyCFunction)PcapDevice_close, METH_NOARGS, PcapDevice_close__doc__},
    {"read", (PyCFunction)PcapDevice_read, METH_NOARGS, PcapDevice_read__doc__},
    {"send", (PyCFunction)PcapDevice_send, METH_VARARGS, PcapDevice_send__doc__},
    {"set_filter", (PyCFunction)PcapDevice_set_filter, METH_VARARGS, PcapDevice_set_filter__doc__},
    {NULL, NULL}
};

static PyTypeObject PcapDevice_type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /*ob_size*/
    "_cpyrit_cpu.PcapDevice",   /*tp_name*/
    sizeof(PcapDevice),         /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    (destructor)PcapDevice_dealloc, /*tp_dealloc*/
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
    PcapDevice_methods,         /*tp_methods*/
    PcapDevice_members,         /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)PcapDevice_init,  /*tp_init*/
    0,                          /*tp_alloc*/
    0,                          /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};


static PyMethodDef CPyritCPUMethods[] =
{
    {"getPlatform", cpyrit_getPlatform, METH_NOARGS, cpyrit_getPlatform__doc__},
    {"grouper", cpyrit_grouper, METH_VARARGS, cpyrit_grouper__doc__},
    {"pyr2halfpack", cpyrit_pyr2halfpack, METH_VARARGS, cpyrit_pyr2halfpack__doc__},
    {NULL, NULL, 0, NULL}
};

static int
detect_cpu(void)
{
#ifdef COMPILE_SSE2
    unsigned int a,b,c,d;

    cpuid(1, a, b, c, d);
    return (c & HAVE_AESNI) | (d & HAVE_SSE2);
#else
    return 0;
#endif
}


static void pathconfig(void)
{
    int cpufeatures;

    cpufeatures = detect_cpu();

    #ifdef COMPILE_AESNI
    if (cpufeatures & HAVE_AESNI)
    {
        PlatformString = PyString_FromString("SSE2/AES");
        ccmp_encrypt = ccmp_encrypt_aesni;
    }
    #endif

    #ifdef COMPILE_SSE2
    if (cpufeatures & HAVE_SSE2)
    {
        if (!PlatformString)
            PlatformString = PyString_FromString("SSE2");
        prepare_pmk = prepare_pmk_openssl;
        finalize_pmk = finalize_pmk_sse2;
        fourwise_sha1hmac_prepare = fourwise_sha1hmac_prepare_sse2;
        fourwise_sha1hmac = fourwise_sha1hmac_sse2;
        fourwise_md5hmac_prepare = fourwise_md5hmac_prepare_sse2;
        fourwise_md5hmac = fourwise_md5hmac_sse2;
        fourwise_pke2tk = fourwise_pke2tk_sse2;
    }
    #endif

    #ifdef __arm__
	if (!PlatformString)
	   PlatformString = PyString_FromString("ARM");
    #endif

    #ifdef __arm64__
        if (!PlatformString)
           PlatformString = PyString_FromString("ARM_64");
    #endif

    #ifdef PPC64
        if (!PlatformString)
           PlatformString = PyString_FromString("PPC_64");
    #endif
    /*
    if (!PlatformString)
        PlatformString = PyString_FromString((char *) getauxval(AT_PLATFORM));
    */
    if (!PlatformString)
        PlatformString = PyString_FromString("Default");
    if (!prepare_pmk)
        prepare_pmk = prepare_pmk_openssl;
    if (!finalize_pmk)
        finalize_pmk = finalize_pmk_openssl;
    if (!fourwise_sha1hmac_prepare)
        fourwise_sha1hmac_prepare = fourwise_hmac_prepare_openssl;
    if (!fourwise_sha1hmac)
        fourwise_sha1hmac = fourwise_sha1hmac_openssl;
    if (!fourwise_md5hmac_prepare)
        fourwise_md5hmac_prepare = fourwise_hmac_prepare_openssl;
    if (!fourwise_md5hmac)
        fourwise_md5hmac = fourwise_md5hmac_openssl;
    if (!fourwise_pke2tk)
        fourwise_pke2tk = fourwise_pke2tk_openssl;
    if (!ccmp_encrypt)
        ccmp_encrypt = ccmp_encrypt_openssl;
}


/*
    ###########################################################################

    Module initialization

    ###########################################################################
*/

PyMODINIT_FUNC
init_cpyrit_cpu(void)
{
    PyObject *m;

#ifdef COMPILE_SSE2
    int i;

    for (i = 0; i < 4; i++)
    {
        md5_constants[ 0][i] = 0xD76AA478; md5_constants[ 1][i] = 0xE8C7B756;
        md5_constants[ 2][i] = 0x242070DB; md5_constants[ 3][i] = 0xC1BDCEEE;
        md5_constants[ 4][i] = 0xF57C0FAF; md5_constants[ 5][i] = 0x4787C62A;
        md5_constants[ 6][i] = 0xA8304613; md5_constants[ 7][i] = 0xFD469501;
        md5_constants[ 8][i] = 0x698098D8; md5_constants[ 9][i] = 0x8B44F7AF;
        md5_constants[10][i] = 0xFFFF5BB1; md5_constants[11][i] = 0x895CD7BE;
        md5_constants[12][i] = 0x6B901122; md5_constants[13][i] = 0xFD987193;
        md5_constants[14][i] = 0xA679438E; md5_constants[15][i] = 0x49B40821;
        md5_constants[16][i] = 0xF61E2562; md5_constants[17][i] = 0xC040B340;
        md5_constants[18][i] = 0x265E5A51; md5_constants[19][i] = 0xE9B6C7AA;
        md5_constants[20][i] = 0xD62F105D; md5_constants[21][i] = 0x02441453;
        md5_constants[22][i] = 0xD8A1E681; md5_constants[23][i] = 0xE7D3FBC8;
        md5_constants[24][i] = 0x21E1CDE6; md5_constants[25][i] = 0xC33707D6;
        md5_constants[26][i] = 0xF4D50D87; md5_constants[27][i] = 0x455A14ED;
        md5_constants[28][i] = 0xA9E3E905; md5_constants[29][i] = 0xFCEFA3F8;
        md5_constants[30][i] = 0x676F02D9; md5_constants[31][i] = 0x8D2A4C8A;
        md5_constants[32][i] = 0xFFFA3942; md5_constants[33][i] = 0x8771F681;
        md5_constants[34][i] = 0x6D9D6122; md5_constants[35][i] = 0xFDE5380C;
        md5_constants[36][i] = 0xA4BEEA44; md5_constants[37][i] = 0x4BDECFA9;
        md5_constants[38][i] = 0xF6BB4B60; md5_constants[39][i] = 0xBEBFBC70;
        md5_constants[40][i] = 0x289B7EC6; md5_constants[41][i] = 0xEAA127FA;
        md5_constants[42][i] = 0xD4EF3085; md5_constants[43][i] = 0x04881D05;
        md5_constants[44][i] = 0xD9D4D039; md5_constants[45][i] = 0xE6DB99E5;
        md5_constants[46][i] = 0x1FA27CF8; md5_constants[47][i] = 0xC4AC5665;
        md5_constants[48][i] = 0xF4292244; md5_constants[49][i] = 0x432AFF97;
        md5_constants[50][i] = 0xAB9423A7; md5_constants[51][i] = 0xFC93A039;
        md5_constants[52][i] = 0x655B59C3; md5_constants[53][i] = 0x8F0CCC92;
        md5_constants[54][i] = 0xFFEFF47D; md5_constants[55][i] = 0x85845DD1;
        md5_constants[56][i] = 0x6FA87E4F; md5_constants[57][i] = 0xFE2CE6E0;
        md5_constants[58][i] = 0xA3014314; md5_constants[59][i] = 0x4E0811A1;
        md5_constants[60][i] = 0xF7537E82; md5_constants[61][i] = 0xBD3AF235;
        md5_constants[62][i] = 0x2AD7D2BB; md5_constants[63][i] = 0xEB86D391;
    }
#endif // COMPILE_SSE2

    pathconfig();

    CPUDevice_type.tp_getattro = PyObject_GenericGetAttr;
    CPUDevice_type.tp_setattro = PyObject_GenericSetAttr;
    CPUDevice_type.tp_alloc  = PyType_GenericAlloc;
    CPUDevice_type.tp_new = PyType_GenericNew;
    CPUDevice_type.tp_free = _PyObject_Del;
    if (PyType_Ready(&CPUDevice_type) < 0)
	    return;

    EAPOLCracker_type.tp_getattro = PyObject_GenericGetAttr;
    EAPOLCracker_type.tp_setattro = PyObject_GenericSetAttr;
    EAPOLCracker_type.tp_alloc  = PyType_GenericAlloc;
    EAPOLCracker_type.tp_new = PyType_GenericNew;
    EAPOLCracker_type.tp_free = _PyObject_Del;
    if (PyType_Ready(&EAPOLCracker_type) < 0)
	    return;

    CCMPCracker_type.tp_getattro = PyObject_GenericGetAttr;
    CCMPCracker_type.tp_setattro = PyObject_GenericSetAttr;
    CCMPCracker_type.tp_alloc  = PyType_GenericAlloc;
    CCMPCracker_type.tp_new = PyType_GenericNew;
    CCMPCracker_type.tp_free = _PyObject_Del;
    if (PyType_Ready(&CCMPCracker_type) < 0)
	    return;

    CowpattyFile_type.tp_getattro = PyObject_GenericGetAttr;
    CowpattyFile_type.tp_setattro = PyObject_GenericSetAttr;
    CowpattyFile_type.tp_alloc  = PyType_GenericAlloc;
    CowpattyFile_type.tp_new = PyType_GenericNew;
    CowpattyFile_type.tp_free = _PyObject_Del;
    if (PyType_Ready(&CowpattyFile_type) < 0)
	    return;

    CowpattyResult_type.tp_getattro = PyObject_GenericGetAttr;
    CowpattyResult_type.tp_setattro = PyObject_GenericSetAttr;
    CowpattyResult_type.tp_alloc  = PyType_GenericAlloc;
    CowpattyResult_type.tp_new = PyType_GenericNew;
    CowpattyResult_type.tp_free = _PyObject_Del;
    CowpattyResult_type.tp_as_sequence = &CowpattyResult_seq_methods;
    CowpattyResult_type.tp_as_buffer = &CowpattyResults_buffer_procs;
    if (PyType_Ready(&CowpattyResult_type) < 0)
	    return;

    PcapDevice_type.tp_getattro = PyObject_GenericGetAttr;
    PcapDevice_type.tp_setattro = PyObject_GenericSetAttr;
    PcapDevice_type.tp_alloc  = PyType_GenericAlloc;
    PcapDevice_type.tp_new = PyType_GenericNew;
    PcapDevice_type.tp_free = _PyObject_Del;
    if (PyType_Ready(&PcapDevice_type) < 0)
	    return;

    m = Py_InitModule("_cpyrit_cpu", CPyritCPUMethods);

    Py_INCREF(&CPUDevice_type);
    PyModule_AddObject(m, "CPUDevice", (PyObject*)&CPUDevice_type);

    Py_INCREF(&EAPOLCracker_type);
    PyModule_AddObject(m, "EAPOLCracker", (PyObject*)&EAPOLCracker_type);

    Py_INCREF(&CCMPCracker_type);
    PyModule_AddObject(m, "CCMPCracker", (PyObject*)&CCMPCracker_type);

    Py_INCREF(&CowpattyFile_type);
    PyModule_AddObject(m, "CowpattyFile", (PyObject*)&CowpattyFile_type);

    Py_INCREF(&CowpattyResult_type);
    PyModule_AddObject(m, "CowpattyResult", (PyObject*)&CowpattyResult_type);

    Py_INCREF(&PcapDevice_type);
    PyModule_AddObject(m, "PcapDevice", (PyObject*)&PcapDevice_type);

    PyModule_AddStringConstant(m, "VERSION", VERSION);
}
