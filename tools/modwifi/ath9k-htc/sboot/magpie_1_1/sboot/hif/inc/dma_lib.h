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
#ifndef __DMA_LIB_H
#define __DMA_LIB_H


/***********************External***************************/

/**
 * @brief DMA engine numbers, HIF need to map them to there
 *        respective order
 */
typedef enum dma_engine{
    DMA_ENGINE_RX0,
    DMA_ENGINE_RX1,
    DMA_ENGINE_RX2,
    DMA_ENGINE_RX3,
    DMA_ENGINE_TX0,
    DMA_ENGINE_TX1,
    DMA_ENGINE_MAX
}dma_engine_t;

/**
 * @brief Interface type, each HIF should call with its own interface type
 */
typedef enum dma_iftype{
    DMA_IF_GMAC = 0x0,/* GMAC */
    DMA_IF_PCI  = 0x1,/*PCI */
    DMA_IF_PCIE = 0x2 /*PCI Express */
}dma_iftype_t;


struct dma_lib_api{
    A_UINT16  (*tx_init)(dma_engine_t eng_no, dma_iftype_t  if_type);
    void        (*tx_start)(dma_engine_t eng_no);
    A_UINT16  (*rx_init)(dma_engine_t eng_no, dma_iftype_t  if_type);
    void        (*rx_config)(dma_engine_t eng_no, a_uint16_t num_desc,
    						 a_uint16_t   gran);
    void        (*rx_start)(dma_engine_t  eng_no); 
    A_UINT32  (*intr_status)(dma_iftype_t  if_type);
    A_UINT16  (*hard_xmit)(dma_engine_t eng_no, VBUF *buf);
    void        (*flush_xmit)(dma_engine_t  eng_no);
    A_UINT16    (*xmit_done)(dma_engine_t   eng_no);
    VBUF *      (*reap_xmitted)(dma_engine_t  eng_no);
    VBUF *      (*reap_recv)(dma_engine_t  eng_no);
    void        (*return_recv)(dma_engine_t  eng_no, VBUF *buf);
    A_UINT16    (*recv_pkt)(dma_engine_t  eng_no);
};


/**
 * @brief Install the DMA lib api's this for ROM patching
 *        support
 * 
 * @param apis
 */
void        dma_lib_module_install(struct dma_lib_api  *apis);

#endif
