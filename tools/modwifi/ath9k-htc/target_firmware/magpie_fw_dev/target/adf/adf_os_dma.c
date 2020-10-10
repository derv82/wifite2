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
#include <adf_os_dma_pvt.h>
#include "Magpie_api.h"
#include "cmnos_api.h"

#if 0
void __adf_os_dma_load(void *arg, bus_dma_segment_t *dseg, int nseg, int error)
{
	if (error)
	   	return;

	adf_os_assert(nseg == 1);

	((bus_dma_segment_t *)arg)[0].ds_addr = dseg[0].ds_addr;
	((bus_dma_segment_t *)arg)[0].ds_len  = dseg[0].ds_len; 
}
#endif

/**
 * @brief Allocates a DMA region, uses the tag elem to store the
 *        tag value which constant for all the mappings done
 *        through this API.
 * 
 * @param osdev
 * @param size
 * @param coherent
 * @param dmap
 * 
 * @return void* (Virtual address)
 */
inline void*
__adf_os_dmamem_alloc(__adf_os_device_t osdev, adf_os_size_t size, 
                      a_bool_t coherent, __adf_os_dma_map_t *dmap)
{    
    (*dmap) = A_ALLOCRAM(sizeof(struct __adf_dma_map));
    
	if((*dmap) == NULL){
		goto fail_malloc;
	}
	    
    (*dmap)->ds_addr = A_ALLOCRAM(size);
    (*dmap)->ds_len = size;
    
    return (*dmap)->ds_addr;
    
fail_malloc: 
    return NULL;            
}
