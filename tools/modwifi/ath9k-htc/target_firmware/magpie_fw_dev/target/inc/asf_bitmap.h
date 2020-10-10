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
#ifndef _ASF_BITMAP_H_
#define _ASF_BITMAP_H_

#include "adf_os_types.h"
#include "adf_os_mem.h"

#define ASF_BYTESZ   8

typedef a_uint8_t * asf_bitmap_t;

/* Bit map related macros. */
// setbit(a,i) ((a)[(i)/NBBY] |= 1<<((i)%NBBY))
// clrbit(a,i) ((a)[(i)/NBBY] &= ~(1<<((i)%NBBY)))
// isset(a,i)  ((a)[(i)/NBBY] & (1<<((i)%NBBY)))
// isclr(a,i)  (((a)[(i)/NBBY] & (1<<((i)%NBBY))) == 0)

#define asf_howmany(x, y)   (((x)+((y)-1))/(y))
#define asf_roundup(x, y)   ((((x)+((y)-1))/(y))*(y))


static inline a_uint8_t *
asf_bitmap_alloc(int sz_bits)
{
    a_uint8_t * bm;
    int sz_bytes = sz_bits / ASF_BYTESZ;

    bm = adf_os_mem_alloc(sz_bytes);
    if (bm == NULL)
        return NULL;

    adf_os_mem_zero(bm, sz_bytes);
    return bm;
}

static inline void
asf_bitmap_free(a_uint8_t *bm)
{
    adf_os_mem_free(bm);
}

static inline void
asf_bitmap_setbit(a_uint8_t *bm, int pos)
{
    bm[pos / ASF_BYTESZ] |= 1 << (pos % ASF_BYTESZ);
}


static inline void
asf_bitmap_clrbit(a_uint8_t *bm, int pos)
{
    bm[pos / ASF_BYTESZ] &= ~(1 << (pos % ASF_BYTESZ));
}

static inline a_bool_t
asf_bitmap_isset(a_uint8_t *bm, int pos)
{
    return bm[pos / ASF_BYTESZ] & (1 << (pos % ASF_BYTESZ));
}

static inline a_bool_t
asf_bitmap_isclr(a_uint8_t *bm, int pos)
{
    return ((bm[pos / ASF_BYTESZ] & (1 << (pos % ASF_BYTESZ))) == 0);
}

#endif /* _ASF_BITMAP_H */
