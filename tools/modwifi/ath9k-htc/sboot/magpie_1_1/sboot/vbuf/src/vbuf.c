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
 * @File: vbuf.c
 * 
 * @Abstract: 
 * 
 * @Notes:
 */


#include <osapi.h>
#include <vbuf_api.h>
#include <Magpie_api.h>

#include "vbuf.h"

#define VBUF_SIZE           sizeof(VBUF)

struct VBUF_CONTEXT g_vbufCtx;

void _vbuf_init(int nBuf);
VBUF* _vbuf_alloc_vbuf(void);
void _vbuf_free_vbuf(VBUF *buf);

void _vbuf_init(int nBuf) 
{
    int i;
    VBUF *vbuf;
    
    //vbuf = (VBUF*)dataAddr;
    vbuf = (VBUF*)A_ALLOCRAM(VBUF_SIZE);
    vbuf->next_buf = NULL;
    vbuf->desc_list = NULL;
                    
    g_vbufCtx.free_buf_head = vbuf;
    
    for(i=1; i<nBuf; i++)
    {
        //vbuf = (VBUF*)(dataAddr + i*VBUF_SIZE);
        vbuf = (VBUF*)A_ALLOCRAM(VBUF_SIZE);
        
        vbuf->desc_list = NULL;
        vbuf->next_buf = g_vbufCtx.free_buf_head;
        g_vbufCtx.free_buf_head = vbuf;
    }    
    
    g_vbufCtx.nVbufNum = nBuf;
    //return (dataAddr + nBuf*VBUF_SIZE);
    return;
}

VBUF* _vbuf_alloc_vbuf(void)
{
    VBUF *allocBuf = NULL;
    
    if ( g_vbufCtx.free_buf_head != NULL )
    {
        allocBuf = g_vbufCtx.free_buf_head;
        g_vbufCtx.nVbufNum--;
        
        g_vbufCtx.free_buf_head = allocBuf->next_buf;
        allocBuf->next_buf = NULL;        
    }
    
    return allocBuf;
}

void _vbuf_free_vbuf(VBUF *buf)
{
    // assert buf != NULL
    
    buf->next_buf = g_vbufCtx.free_buf_head;
    g_vbufCtx.free_buf_head = buf;
    
    g_vbufCtx.nVbufNum++;
}

/* the exported entry point into this module. All apis are accessed through
 * function pointers */
void vbuf_module_install(struct vbuf_api *apis)
{    
        /* hook in APIs */
    apis->_init = _vbuf_init;
    apis->_alloc_vbuf = _vbuf_alloc_vbuf;
    apis->_free_vbuf = _vbuf_free_vbuf;
    
        /* save ptr to the ptr to the context for external code to inspect/modify internal module state */
    //apis->pReserved = &g_pMboxHWContext;
}
 

