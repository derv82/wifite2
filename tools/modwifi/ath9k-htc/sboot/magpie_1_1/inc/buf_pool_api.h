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
 * @File: buf_pool_api.h
 * 
 * @Abstract: BUF Pool api
 * 
 * @Notes:
 */

#ifndef _BUF_POOL_API_H
#define _BUF_POOL_API_H

#include <adf_nbuf.h>

/* endpoint defines */
typedef enum
{
    POOL_ID_HTC_CONTROL         = 0, 
    POOL_ID_WMI_SVC_CMD_REPLY   = 1,  
    POOL_ID_WMI_SVC_EVENT       = 2,
    POOL_ID_WLAN_RX_BUF         = 3,
    POOL_ID_MAX                 = 10 
} BUF_POOL_ID;

typedef void* pool_handle_t;

/* hardware API table structure (API descriptions below) */
struct buf_pool_api {
    pool_handle_t (*_init)(adf_os_handle_t handle);
            
    void (*_shutdown)(pool_handle_t handle);
    
    void (*_create_pool)(pool_handle_t handle, BUF_POOL_ID poolId, int nItems, int nSize);
    
    adf_nbuf_t  (*_alloc_buf)(pool_handle_t handle, BUF_POOL_ID poolId, int reserve);
    
    adf_nbuf_t  (*_alloc_buf_align)(pool_handle_t handle, BUF_POOL_ID poolId, int reserve, int align);
    
    void (*_free_buf)(pool_handle_t handle, BUF_POOL_ID poolId, adf_nbuf_t buf);
    
        /* room to expand this table by another table */
    void *pReserved;    
};

extern void buf_pool_module_install(struct buf_pool_api *apis);

#endif /* #ifndef _BUF_POOL_API_H */
