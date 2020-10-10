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
/*
 * @File: VBUF_api.h
 * 
 * @Abstract: Host Interface api
 * 
 * @Notes:
 */

#ifndef _VBUF_API_H
#define _VBUF_API_H

#include <vdesc_api.h>

#define MAX_BUF_CTX_LEN     20

typedef struct _VBUF
{
    VDESC           *desc_list;
    struct _VBUF    *next_buf; 
    A_UINT16        buf_length; 
    A_UINT8         reserved[2];
    A_UINT8         ctx[MAX_BUF_CTX_LEN];  
    //A_UINT8         end_point;    
    //A_UINT8         reserved[1]; 
} VBUF;

#define VBUF_GET_DATA_ADDR(vbuf)    (vbuf->desc_list->buf_addr + vbuf->desc_list->data_offset)

/* hardware API table structure (API descriptions below) */
struct vbuf_api {
    void (*_init)(int nBuf);
    VBUF* (*_alloc_vbuf)(void);
    VBUF* (*_alloc_vbuf_with_size)(int size, int reserve);
    void (*_free_vbuf)(VBUF *buf);

        /* room to expand this table by another table */
    void *pReserved;    
};

extern void vbuf_module_install(struct vbuf_api *apis);

#endif /* #ifndef _HIF_API_H */
