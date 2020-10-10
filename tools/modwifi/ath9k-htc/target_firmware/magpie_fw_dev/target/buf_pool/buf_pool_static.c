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
 * @File: 
 * 
 * @Abstract: Buf pool implementation: static version
 * 
 * @Notes: 
 */

#include <osapi.h>
#include <Magpie_api.h> 
#include <cmnos_api.h>
#include <buf_pool_api.h>
#include <vbuf_api.h>
#include <vdesc_api.h>
#include <adf_os_mem.h> 

#include "buf_pool_static.h"

LOCAL htc_handle_t _buf_pool_static_init(adf_net_handle_t handle);
LOCAL void _buf_pool_static_create_pool(pool_handle_t handle, BUF_POOL_ID poolId, int nItems, int nSize);
LOCAL adf_nbuf_t  _buf_pool_static_alloc_buf(pool_handle_t handle, BUF_POOL_ID poolId, int reserve);
LOCAL adf_nbuf_t  _buf_pool_static_alloc_buf_align(pool_handle_t handle, BUF_POOL_ID poolId, int reserve, int align);
LOCAL void _buf_pool_static_free_buf(pool_handle_t handle, BUF_POOL_ID poolId, adf_nbuf_t buf);
LOCAL void _buf_pool_static_shutdown(pool_handle_t handle);      

BUF_POOL_STATIC_CONTEXT g_poolCtx;

void buf_pool_module_install(struct buf_pool_api *pAPIs)
{   
    pAPIs->_init = _buf_pool_static_init;
    pAPIs->_create_pool = _buf_pool_static_create_pool;
    pAPIs->_alloc_buf = _buf_pool_static_alloc_buf;
    pAPIs->_alloc_buf_align = _buf_pool_static_alloc_buf_align;
    pAPIs->_free_buf = _buf_pool_static_free_buf;
    pAPIs->_shutdown = _buf_pool_static_shutdown;
}
 
LOCAL pool_handle_t _buf_pool_static_init(adf_os_handle_t handle)
{
#if 1
    int i;
    
    for(i=0; i < POOL_ID_MAX; i++) {
        g_poolCtx.bufQ[i] = NULL;
    }
    
    return &g_poolCtx;
#else    
    BUF_POOL_STATIC_CONTEXT *ctx;
    
    //ctx = (BUF_POOL_static_CONTEXT *)A_ALLOCRAM(sizeof(BUF_POOL_static_CONTEXT));
    ctx = (BUF_POOL_STATIC_CONTEXT *)adf_os_mem_alloc(sizeof(BUF_POOL_STATIC_CONTEXT));
    ctx->NetHandle = handle;
    
    return ctx; 
#endif    
}      
    
LOCAL void _buf_pool_static_shutdown(pool_handle_t handle) 
{
    // SHALL NOT BE USED in FW
}

LOCAL void _buf_pool_static_create_pool(pool_handle_t handle, BUF_POOL_ID poolId, int nItems, int nSize)
{
    int i;
    VBUF *buf;
    VDESC *desc;
    
    //BUF_POOL_STATIC_CONTEXT *ctx = (BUF_POOL_STATIC_CONTEXT *)handle;
    
    for ( i = 0; i < nItems; i++) {
        buf = VBUF_alloc_vbuf();
        desc = VDESC_alloc_vdesc();

        desc->buf_addr = (A_UINT8 *)adf_os_mem_alloc(nSize);
        desc->buf_size = nSize;
        desc->data_offset = 0;
        desc->data_size = 0;
        
        buf->buf_length = 0;        
        buf->desc_list = desc;
        
        if ( g_poolCtx.bufQ[poolId] == NULL ) {
            g_poolCtx.bufQ[poolId] = buf;
        } else {
            buf->next_buf = g_poolCtx.bufQ[poolId];
            g_poolCtx.bufQ[poolId] = buf;
        }
    }
}
            
LOCAL adf_nbuf_t  _buf_pool_static_alloc_buf(pool_handle_t handle, BUF_POOL_ID poolId, int reserve)
{
    VBUF *buf;
    
    buf = g_poolCtx.bufQ[poolId];
    if ( buf != NULL ) {
        g_poolCtx.bufQ[poolId] = buf->next_buf;
        
        buf->next_buf = NULL;
        buf->desc_list->data_offset = reserve;
        buf->desc_list->data_size = 0;
        buf->buf_length = 0;
    }
    
    return buf;
}

LOCAL adf_nbuf_t  _buf_pool_static_alloc_buf_align(pool_handle_t handle, BUF_POOL_ID poolId, int reserve, int align)
{
    return _buf_pool_static_alloc_buf(handle, poolId, reserve);
}
    
LOCAL void _buf_pool_static_free_buf(pool_handle_t handle, BUF_POOL_ID poolId, adf_nbuf_t buf)
{
    if ( g_poolCtx.bufQ[poolId] == NULL ) {
        g_poolCtx.bufQ[poolId] = buf;
    } else {
        buf->next_buf = g_poolCtx.bufQ[poolId];
        g_poolCtx.bufQ[poolId] = buf;
    }
}
