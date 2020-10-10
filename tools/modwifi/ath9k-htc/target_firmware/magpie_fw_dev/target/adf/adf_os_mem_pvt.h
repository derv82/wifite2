/*
 * Copyright (c) 2013 Qualcomm Atheros, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the
 * disclaimer below) provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *  * Neither the name of Qualcomm Atheros nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
 * GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
 * HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
 * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
 * IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#ifndef ADF_OS_MEM_PVT_H
#define ADF_OS_MEM_PVT_H

#include "cmnos_api.h"
#include "Magpie_api.h"

static inline void *	__adf_os_mem_alloc(adf_os_size_t size)
{
//    return (malloc(size,M_DEVBUF,M_DONTWAIT | M_ZERO));
    return A_ALLOCRAM(size);
}

static inline void 		__adf_os_mem_free(void *buf)
{
    //Should not be called in FW!
    //free(buf,M_DEVBUF);
}

/* move a memory buffer */
static inline void 		__adf_os_mem_copy(void *dst, const void *src, adf_os_size_t size)
{
    A_MEMCPY(dst,src,size);    
}

/* set a memory buffer */
static inline void
__adf_os_mem_set(void *buf, a_uint8_t b, adf_os_size_t size)
{
	A_MEMSET(buf, b, size);
}
static inline void
__adf_os_mem_move(void *dst, void *src, adf_os_size_t size)
{
	A_MEMMOVE(dst, src, size);
}
/* zero a memory buffer */
static inline void
__adf_os_mem_zero(void *buf, adf_os_size_t size)
{
    A_MEMZERO(buf,size);
}
/* compare two memory buffers */
static inline int
__adf_os_mem_cmp(void *buf1, void *buf2, adf_os_size_t size)
{
    return (A_MEMCMP (buf1, buf2, size) == 0) ? 0 : 1;
}
#endif
