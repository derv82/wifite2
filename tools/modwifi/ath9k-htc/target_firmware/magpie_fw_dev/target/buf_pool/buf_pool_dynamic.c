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
 * @Abstract: Buf pool implementation: Dynamic version
 * 
 * @Notes: 
 */
#include <adf_os_mem.h>
#include <adf_os_module.h>
#include <osapi.h>
#include <Magpie_api.h> 
//#include <os/cmnos_api.h>
#include <buf_pool_api.h>
 
LOCAL htc_handle_t _buf_pool_dynamic_init(adf_os_handle_t handle);
LOCAL void _buf_pool_dynamic_create_pool(pool_handle_t handle, BUF_POOL_ID poolId, int nItems, int nSize);
LOCAL adf_nbuf_t  _buf_pool_dynamic_alloc_buf(pool_handle_t handle, BUF_POOL_ID poolId, int reserve);
LOCAL adf_nbuf_t  _buf_pool_dynamic_alloc_buf_align(pool_handle_t handle, BUF_POOL_ID poolId, int reserve, int align);
LOCAL void _buf_pool_dynamic_free_buf(pool_handle_t handle, BUF_POOL_ID poolId, adf_nbuf_t buf);
LOCAL void _buf_pool_dynamic_shutdown(pool_handle_t handle);
       
typedef struct _POOL_CONFIG {
    int nSize;
} POOL_CONFIG;
       
typedef struct _BUF_POOL_DYNAMIC_CONTEXT {
    adf_os_handle_t  OSHandle;
    POOL_CONFIG poolConf[POOL_ID_MAX]; 
} BUF_POOL_DYNAMIC_CONTEXT;

void buf_pool_module_install(struct buf_pool_api *pAPIs)
{   
    pAPIs->_init = _buf_pool_dynamic_init;
    pAPIs->_create_pool = _buf_pool_dynamic_create_pool;
    pAPIs->_alloc_buf = _buf_pool_dynamic_alloc_buf;
    pAPIs->_alloc_buf_align = _buf_pool_dynamic_alloc_buf_align;
    pAPIs->_free_buf = _buf_pool_dynamic_free_buf;
    pAPIs->_shutdown = _buf_pool_dynamic_shutdown;
}
 
LOCAL pool_handle_t _buf_pool_dynamic_init(adf_os_handle_t handle)
{
    BUF_POOL_DYNAMIC_CONTEXT *ctx;
    
    ctx = (BUF_POOL_DYNAMIC_CONTEXT *)adf_os_mem_alloc(sizeof(BUF_POOL_DYNAMIC_CONTEXT));
    ctx->OSHandle = handle;
    
    return ctx; 
}      
    
LOCAL void _buf_pool_dynamic_shutdown(pool_handle_t handle) 
{
    BUF_POOL_DYNAMIC_CONTEXT *ctx = (BUF_POOL_DYNAMIC_CONTEXT *)handle;
    
    adf_os_mem_free(ctx);
}

LOCAL void _buf_pool_dynamic_create_pool(pool_handle_t handle, BUF_POOL_ID poolId, int nItems, int nSize)
{
    BUF_POOL_DYNAMIC_CONTEXT *ctx = (BUF_POOL_DYNAMIC_CONTEXT *)handle;
    
    ctx->poolConf[poolId].nSize = nSize;
}
            
LOCAL adf_nbuf_t  _buf_pool_dynamic_alloc_buf(pool_handle_t handle, BUF_POOL_ID poolId, int reserve)
{
    BUF_POOL_DYNAMIC_CONTEXT *ctx = (BUF_POOL_DYNAMIC_CONTEXT *)handle;
    POOL_CONFIG *poolConf = &ctx->poolConf[poolId];
            
    return adf_nbuf_alloc(poolConf->nSize, 
                          reserve, 0);

}
    
LOCAL adf_nbuf_t  _buf_pool_dynamic_alloc_buf_align(pool_handle_t handle, BUF_POOL_ID poolId, int reserve, int align)
{
    BUF_POOL_DYNAMIC_CONTEXT *ctx = (BUF_POOL_DYNAMIC_CONTEXT *)handle;
    POOL_CONFIG *poolConf = &ctx->poolConf[poolId];

    return adf_nbuf_alloc(poolConf->nSize, 
                          reserve, align);

}

LOCAL void _buf_pool_dynamic_free_buf(pool_handle_t handle, BUF_POOL_ID poolId, adf_nbuf_t buf)
{
    //BUF_POOL_DYNAMIC_CONTEXT *ctx = (BUF_POOL_DYNAMIC_CONTEXT *)handle;
        
    adf_nbuf_free(buf);
}

adf_os_export_symbol(buf_pool_module_install);
