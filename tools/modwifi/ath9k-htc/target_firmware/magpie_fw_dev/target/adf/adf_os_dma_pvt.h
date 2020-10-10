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
#ifndef __ADF_NBUF_DMA_PVT_H
#define __ADF_NBUF_DMA_PVT_H

#include <adf_os_types.h>
#include <adf_os_util.h>

inline void*
__adf_os_dmamem_alloc(__adf_os_device_t osdev, adf_os_size_t size, 
                      a_bool_t coherent, __adf_os_dma_map_t *dmap);

/* 
 * Free a previously mapped DMA buffer 
 * Direction doesnt matter, since this API is called at closing time.
 */
static inline void
__adf_os_dmamem_free(adf_os_device_t    osdev, __adf_os_size_t size, a_bool_t coherent,
                                         void *vaddr, __adf_os_dma_map_t dmap)
{ 

}


//#define __adf_os_dmamem_map2addr(_dmap)    ((_dmap)->seg[0].ds_addr)
#define __adf_os_dmamem_map2addr(_dmap) ((adf_os_dma_addr_t)(_dmap)->ds_addr)

static inline void 
__adf_os_dmamem_cache_sync(__adf_os_device_t osdev, __adf_os_dma_map_t dmap, adf_os_cache_sync_t sync)
{

}


static inline adf_os_size_t
__adf_os_cache_line_size(void)
{
    /**
     * Todo
     */
   return 0;
}

#endif
