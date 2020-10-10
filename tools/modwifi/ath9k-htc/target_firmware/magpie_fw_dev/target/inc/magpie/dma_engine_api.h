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
 * @File: dma_engine_api.h
 * 
 * @Abstract: DMA Engine api
 * 
 * @Notes:
 */

#ifndef _DMA_ENGINE_API_H
#define _DMA_ENGINE_API_H

#include <vbuf_api.h>
#include <vdesc_api.h>

struct zsDmaDesc
{
#if 1   // BIG_ENDIAN
    volatile u16_t      ctrl;       // Descriptor control
    volatile u16_t      status;     // Descriptor status
    volatile u16_t      totalLen;   // Total length
    volatile u16_t      dataSize;   // Data size
#else
    volatile u16_t      status;     // Descriptor status
    volatile u16_t      ctrl;       // Descriptor control
    volatile u16_t      dataSize;   // Data size
    volatile u16_t      totalLen;   // Total length
#endif
    struct zsDmaDesc*   lastAddr;   // Last address of this chain
    volatile u32_t      dataAddr;   // Data buffer address
    struct zsDmaDesc*   nextAddr;   // Next TD address
};

struct zsDmaQueue
{
    struct zsDmaDesc* head;
    struct zsDmaDesc* terminator;
};

// Subclass of zsDmaQueue for TX
struct zsTxDmaQueue
{
    struct zsDmaDesc* head;
    struct zsDmaDesc* terminator;
    
    /* Below are fields specific to TX */
    VBUF *xmited_buf_head;
    VBUF *xmited_buf_tail;        
};

/* hardware API table structure (API descriptions below) */
struct dma_engine_api 
{
    void  (*_init)();

    void  (*_init_rx_queue)(struct zsDmaQueue *q);
    
    void  (*_init_tx_queue)(struct zsTxDmaQueue *q);
                    
    void  (*_config_rx_queue)(struct zsDmaQueue *q, int num_desc, int buf_size);
    
    void  (*_xmit_buf)(struct zsTxDmaQueue *q, VBUF *buf);
    
    void  (*_flush_xmit)(struct zsDmaQueue *q);
    
    VBUF* (*_reap_recv_buf)(struct zsDmaQueue *q);
    
    void  (*_return_recv_buf)(struct zsDmaQueue *q, VBUF *buf);
    
    VBUF* (*_reap_xmited_buf)(struct zsTxDmaQueue *q);
    
    void  (*_swap_data)(struct zsDmaDesc* desc);
    
    int   (*_has_compl_packets)(struct zsDmaQueue *q);
    
    void  (*_desc_dump)(struct zsDmaQueue *q);
    
    /* The functions below are for patchable */
    struct zsDmaDesc* (*_get_packet)(struct zsDmaQueue* q);
    void  (*_reclaim_packet)(struct zsDmaQueue* q, struct zsDmaDesc* desc);
    void (*_put_packet)(struct zsDmaQueue* q, struct zsDmaDesc* desc);
    
    /* room to expand this table by another table */
    void *pReserved;
};

extern void dma_engine_module_install(struct dma_engine_api *apis);

#endif /* #ifndef _DMA_ENGINE_API_H */
