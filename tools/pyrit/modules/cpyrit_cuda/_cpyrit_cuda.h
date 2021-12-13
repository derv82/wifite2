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

#include <stdint.h>
#include <cuda.h>

#ifndef CPYRIT_CUDA
#define CPYRIT_CUDA

#define THREADS_PER_BLOCK 64

#define GET_BE(n,b,i)                            \
{                                                \
    (n) = ( (uint32_t) (b)[(i)    ] << 24 )      \
        | ( (uint32_t) (b)[(i) + 1] << 16 )      \
        | ( (uint32_t) (b)[(i) + 2] <<  8 )      \
        | ( (uint32_t) (b)[(i) + 3]       );     \
}

#define PUT_BE(n,b,i)                             \
{                                                 \
    (b)[(i)    ] = (unsigned char) ( (n) >> 24 ); \
    (b)[(i) + 1] = (unsigned char) ( (n) >> 16 ); \
    (b)[(i) + 2] = (unsigned char) ( (n) >>  8 ); \
    (b)[(i) + 3] = (unsigned char) ( (n)       ); \
}

typedef struct {
    uint32_t h0,h1,h2,h3,h4;
} SHA_DEV_CTX;

#define CPY_DEVCTX(src, dst) \
{ \
    dst.h0 = src.h0; dst.h1 = src.h1; \
    dst.h2 = src.h2; dst.h3 = src.h3; \
    dst.h4 = src.h4; \
}

#define CUSAFECALL(cmd) \
{ \
    ret = (cmd); \
    if (ret != CUDA_SUCCESS) \
        goto errout; \
}

#define ALIGN_UP(offset, alignment) \
    (offset) = ((offset) + (alignment) - 1) & ~((alignment) - 1)

typedef struct {
    SHA_DEV_CTX ctx_ipad;
    SHA_DEV_CTX ctx_opad;
    SHA_DEV_CTX e1;
    SHA_DEV_CTX e2;
} gpu_inbuffer;

typedef struct {
    SHA_DEV_CTX pmk1;
    SHA_DEV_CTX pmk2;
} gpu_outbuffer;

#endif

