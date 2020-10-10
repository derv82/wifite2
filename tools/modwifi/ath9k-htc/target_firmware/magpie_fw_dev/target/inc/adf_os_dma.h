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
/**
 * @ingroup adf_os_public
 * @file adf_os_dma.h
 * This file abstracts DMA operations.
 */

#ifndef _ADF_OS_DMA_H
#define _ADF_OS_DMA_H

#include <adf_os_types.h>
#include <adf_os_dma_pvt.h>

/*
 * @brief a dma address representation of a platform
 */

/**
 * @brief Allocate a DMA buffer and map it to local bus address space
 *
 * @param[in]  osdev     platform device instance
 * @param[in]  size      DMA buffer size
 * @param[in]  coherent  0 => cached.
 * @param[out] dmap      opaque coherent memory handle
 * 
 * @return     returns the virtual address of the memory
 */
static inline void *
adf_os_dmamem_alloc(adf_os_device_t     osdev, 
                    adf_os_size_t       size, 
                    a_bool_t            coherent, 
                    adf_os_dma_map_t   *dmap)
{
    return __adf_os_dmamem_alloc(osdev, size, coherent, dmap);
}

/**
 * @brief Free a previously mapped DMA buffer
 * 
 * @param[in] osdev     platform device instance
 * @param[in] size      DMA buffer size
 * @param[in] coherent  0 => cached.
 * @param[in] vaddr     virtual address of DMA buffer
 * @param[in] dmap      memory handle
 */
static inline void
adf_os_dmamem_free(adf_os_device_t    osdev,
                   adf_os_size_t      size,
                   a_bool_t           coherent,
                   void              *vaddr,
                   adf_os_dma_map_t   dmap)
{
    __adf_os_dmamem_free(osdev, size, coherent, vaddr, dmap);
}

/**
 * @brief given a dmamem map, returns the (bus) address
 *
 * @param[in] dmap      memory handle
 *
 * @return the (bus) address
 */
static inline adf_os_dma_addr_t
adf_os_dmamem_map2addr(adf_os_dma_map_t dmap)
{
    return(__adf_os_dmamem_map2addr(dmap));
}

/**
 * @brief Flush and invalidate cache for a given dmamem map
 *
 * @param[in] osdev     platform device instance
 * @param[in] dmap 		mem handle
 * @param[in] op        op code for sync type, (see @ref adf_os_types.h)
 */
static inline void
adf_os_dmamem_cache_sync(adf_os_device_t      osdev, 
                         adf_os_dma_map_t     dmap, 
                         adf_os_cache_sync_t  op)
{
    __adf_os_dmamem_cache_sync(osdev, dmap, op);
}

/**
 * @brief Get the cpu cache line size
 * 
 * @return The CPU cache line size in bytes.
 */
static inline adf_os_size_t
adf_os_cache_line_size(void)
{
    return __adf_os_cache_line_size();
}

#endif
