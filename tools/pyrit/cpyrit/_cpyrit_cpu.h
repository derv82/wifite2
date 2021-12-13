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
*/

#ifndef CPYRIT

#define CPYRIT

#if (defined(__x86_64__))
    #define cpuid(func, ax, bx, cx, dx) \
        __asm__ __volatile__ ("cpuid;":\
        "=a" (ax), "=b" (bx), "=c" (cx), "=d" (dx) : "a" (func));
#elif (defined(__i386__))
    #define cpuid(func, ax, bx, cx, dx) \
        __asm__ __volatile__ ("pushl %%ebx; cpuid; movl %%ebx, %1; popl %%ebx":\
        "=a" (ax), "=r" (bx), "=c" (cx), "=d" (dx) : "a" (func));
#endif

#define HAVE_AESNI 0x2000000 /* CPUID.01H:ECX.AES[bit 25] */
#define HAVE_SSE2 0x4000000 /* CPUID.01H:EDX.AES[bit 26] */

#define HMAC_MD5_RC4 0
#define HMAC_SHA1_AES 1

typedef struct {
    uint32_t h0[4];
    uint32_t h1[4];
    uint32_t h2[4];
    uint32_t h3[4];
    uint32_t h4[4];
    uint32_t cst[6][4];
} fourwise_sha1_ctx;

typedef struct {
    uint32_t a[4];
    uint32_t b[4];
    uint32_t c[4];
    uint32_t d[4];
} fourwise_md5_ctx;

struct pmk_ctr
{
    SHA_CTX ctx_ipad;
    SHA_CTX ctx_opad;
    uint32_t e1[5];
    uint32_t e2[5];
};

typedef struct
{
    PyObject_HEAD
    char keyscheme;
    unsigned char *pke;
    unsigned char keymic[16];
    size_t eapolframe_size;
    unsigned char *eapolframe;
} EAPOLCracker;

struct ccm_nonce
{
    unsigned char priority;
    unsigned char a2[6];
    unsigned char pn[6];
};

struct A_i
{
    unsigned char flags;
    struct ccm_nonce nonce;
    unsigned short counter;
};

typedef struct
{
    PyObject_HEAD
    unsigned char *pke1;
    unsigned char *pke2;
    unsigned char S0[6];
    struct A_i A0;
} CCMPCracker;

typedef struct
{
    PyObject_HEAD
} CPUDevice;

typedef struct
{
    PyObject_HEAD
} CowpattyFile;

typedef struct
{
    PyObject_HEAD
    unsigned char *buffer, *current_ptr;
    Py_ssize_t buffersize;
    int current_idx, itemcount;
} CowpattyResult;

typedef struct
{
    PyObject_HEAD
    PyObject *device_name;
    PyObject *type;
    PyObject *datalink_name;
    pcap_t *p;
    int datalink;
    char status;
} PcapDevice;

#endif /* CPYRIT */
