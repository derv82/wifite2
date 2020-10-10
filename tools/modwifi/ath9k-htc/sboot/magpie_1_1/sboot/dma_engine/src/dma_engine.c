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
 * @File: dma_engine.c
 * 
 * @Abstract: DMA engine for Magpie
 * 
 * @Notes:
 */
#include "sys_cfg.h"
#include "dt_defs.h"
#include "reg_defs.h"
#include "desc.h"

#include <osapi.h>
//#include <HIF_api.h>
#include <dma_engine_api.h>
#include <Magpie_api.h>
#include <vdesc_api.h>
#include <adf_os_mem.h> 
#include <adf_os_io.h>

//#include "HIF_usb.h"

//HIF_USB_CONTEXT g_hifUSBCtx;

#define VDESC_TO_USBDESC(vdesc)     (struct zsDmaDesc *)((vdesc)->hw_desc_buf)

static void relinkUSBDescToVdesc(VBUF *buf, struct zsDmaDesc* desc);
static void config_queue(struct zsDmaQueue *q, VDESC *desc_list);

#if ENABLE_SW_SWAP_DATA_MODE
static void swapData(struct zsDmaDesc* usbDesc);
#endif

static void init_usb_desc(struct zsDmaDesc *usbDesc)
{
    usbDesc->status = ZM_OWN_BITS_SW;
    usbDesc->ctrl = 0;
    usbDesc->dataSize = 0;
    usbDesc->totalLen = 0;
    usbDesc->lastAddr = 0;
    usbDesc->dataAddr = 0;
    usbDesc->nextAddr = 0;    
}

void _DMAengine_init() 
{

}

void _DMAengine_init_rx_queue(struct zsDmaQueue *q) 
{
    VDESC *desc;
    struct zsDmaDesc *usbDesc;
    
    desc = VDESC_alloc_vdesc();
    if ( desc != NULL ) {
        usbDesc = VDESC_TO_USBDESC(desc);
        init_usb_desc(usbDesc);
        
        q->head = q->terminator = usbDesc;
    }   
}

void _DMAengine_init_tx_queue(struct zsTxDmaQueue *q) 
{
    _DMAengine_init_rx_queue((struct zsDmaQueue *)q);
    q->xmited_buf_head = NULL;
    q->xmited_buf_tail = NULL;     
}

#if ENABLE_SW_SWAP_DATA_MODE

static void swapData(struct zsDmaDesc* usbDesc)
{
    int len = (usbDesc->dataSize & 0xfffffffc) >> 2;
    int i;
    A_UINT32 *dataAddr = (A_UINT32 *)usbDesc->dataAddr;
    A_UINT32 data;
    
    if ( ( usbDesc->dataSize & 3 ) != 0 ) {
        len += 1;
    }
    
    for ( i = 0; i < len; i++ ) {
        data = dataAddr[i];
        
        dataAddr[i] = __bswap32(data);
    }    
}

#endif

void _DMAengine_return_recv_buf(struct zsDmaQueue *q, VBUF *buf)
{    
    /* Re-link the VDESC of buf into USB descriptor list & queue the descriptors 
       into downQ
     */     
    config_queue(q, buf->desc_list);   
    VBUF_free_vbuf(buf);              
}

static void config_queue(struct zsDmaQueue *q, VDESC *desc_list)
{   
    VDESC *theDesc;
    struct zsDmaDesc *usbDesc;
    struct zsDmaDesc* prevUsbDesc = NULL;
    struct zsDmaDesc* headUsbDesc;
        
    theDesc = desc_list;
    while ( theDesc != NULL ) {            
        usbDesc = (struct zsDmaDesc *)VDESC_get_hw_desc(theDesc);
        init_usb_desc(usbDesc);
       
        theDesc->data_offset = 0; //RAY 0723
        usbDesc->dataAddr = (volatile u32_t)(theDesc->buf_addr + theDesc->data_offset);
        usbDesc->dataSize = theDesc->buf_size;
        
        if ( prevUsbDesc == NULL ) {
            headUsbDesc = usbDesc;
            prevUsbDesc = usbDesc;
        } else {
            prevUsbDesc->nextAddr = usbDesc;
            prevUsbDesc = usbDesc;
        }                
        
        theDesc = theDesc->next_desc;
    }
    
    headUsbDesc->lastAddr = prevUsbDesc;
    DMA_Engine_reclaim_packet(q, headUsbDesc);   
                    
    return;
}

//#define MAX_TX_BUF_SIZE            ZM_BLOCK_SIZE
//#define MAX_TX_BUF_SIZE            1600

void _DMAengine_config_rx_queue(struct zsDmaQueue *q, int num_desc, int buf_size)
{
    int i;
    VDESC *desc;
    VDESC *head = NULL;
        
    for(i=0; i < num_desc; i++)
    {
        desc = VDESC_alloc_vdesc();
        
        adf_os_assert(desc != NULL);
        
        desc->buf_addr = (A_UINT8 *)adf_os_mem_alloc(buf_size);
        desc->buf_size = buf_size;
        desc->next_desc = NULL;
        desc->data_offset = 0;
        desc->data_size = 0;
        desc->control = 0;
               
        if ( head == NULL )
        {
            head = desc;
        }
        else
        {
            desc->next_desc = head;
            head = desc;
        }
    }         
    
    config_queue(q, head);          
}

void _DMAengine_xmit_buf(struct zsTxDmaQueue *q, VBUF *buf)
{
    VDESC *currVdesc;
    struct zsDmaDesc* usbDesc;
    struct zsDmaDesc* prevUsbDesc = NULL;
    struct zsDmaDesc* headUsbDesc;   
        
    /* Re-link the VDESC of buf into USB descriptor list & queue the descriptors 
       into upQ
     */
    currVdesc = (VDESC *)buf->desc_list;
    while(currVdesc != NULL) {
        
        usbDesc = (struct zsDmaDesc *)currVdesc->hw_desc_buf;
                
        init_usb_desc(usbDesc);
        usbDesc->dataSize = currVdesc->data_size;
        usbDesc->dataAddr = (volatile u32_t)(currVdesc->buf_addr + currVdesc->data_offset);
        usbDesc->ctrl = 0;
        usbDesc->status = 0;

#if ENABLE_SW_SWAP_DATA_MODE && ENABLE_SWAP_DATA_MODE == 0
        swapData(usbDesc);
#endif

        if ( prevUsbDesc == NULL ) {
            headUsbDesc = usbDesc;
            
            usbDesc->ctrl |= ZM_FS_BIT;
            
            // how to get the total len???
            usbDesc->totalLen = buf->buf_length;
            prevUsbDesc = usbDesc;
        }
        else {
            prevUsbDesc->nextAddr = usbDesc;
            prevUsbDesc = usbDesc;
        }
             
        currVdesc = currVdesc->next_desc;
    }

    usbDesc->ctrl |= ZM_LS_BIT;
    headUsbDesc->lastAddr = usbDesc;

    if ( q->xmited_buf_head == NULL && q->xmited_buf_tail == NULL ) {
        q->xmited_buf_head = buf;
        q->xmited_buf_tail = buf;
        q->xmited_buf_head->next_buf = q->xmited_buf_tail;
    }
    else {
        q->xmited_buf_tail->next_buf = buf;
        q->xmited_buf_tail = buf;
    }

    DMA_Engine_put_packet((struct zsDmaQueue *)q, headUsbDesc); 
}
    
void _DMAengine_flush_xmit(struct zsDmaQueue *q)
{
}

int _DMAengine_has_compl_packets(struct zsDmaQueue *q)
{
    int has_compl_pkts = 0;
    
    if ((q->head != q->terminator) && 
        ((q->head->status & ZM_OWN_BITS_MASK) != ZM_OWN_BITS_HW)) {
        has_compl_pkts = 1;            
    }
    
    return has_compl_pkts;
}
    
VBUF* _DMAengine_reap_recv_buf(struct zsDmaQueue *q)
{
    struct zsDmaDesc* desc;
    VBUF *buf;
    //int i;
    //u8_t *tbuf = (u8_t *)desc->dataAddr;
            
    desc = DMA_Engine_get_packet(q);            
    
    if(!desc)
       return NULL;

#if ENABLE_SW_SWAP_DATA_MODE && ENABLE_SWAP_DATA_MODE == 0
    swapData(desc);
#endif
    
    buf = VBUF_alloc_vbuf();
    adf_os_assert(buf != NULL);
    
    relinkUSBDescToVdesc(buf, desc);
    return buf;
}
    
VBUF* _DMAengine_reap_xmited_buf(struct zsTxDmaQueue *q)
{
    struct zsDmaDesc* desc;
    VBUF *sentBuf;
    
    desc = DMA_Engine_get_packet((struct zsDmaQueue *)q);
    
    if(!desc)
       return NULL;

    // assert g_hifUSBCtx.upVbufQ.head is not null
    // assert g_hifUSBCtx.upVbufQ.tail is not null  
    sentBuf = q->xmited_buf_head;
    if ( q->xmited_buf_head == q->xmited_buf_tail ) {
        q->xmited_buf_head = NULL;
        q->xmited_buf_tail = NULL;
    } else {        
        q->xmited_buf_head = q->xmited_buf_head->next_buf;       
    }
    
    sentBuf->next_buf = NULL;
    relinkUSBDescToVdesc(sentBuf, desc);
    return sentBuf;
}

void _DMAengine_desc_dump(struct zsDmaQueue *q)
{
    u32_t i=0;
    struct zsDmaDesc* tmpDesc;
        
    tmpDesc = q->head;

    do {
        if( tmpDesc == q->terminator )
        {
#ifdef DESC_DUMP_BOTH_DESCnDATA
            A_PRINTF("0x%08x(0x%08x,T)]", tmpDesc, tmpDesc->dataAddr);
#else
            A_PRINTF("0x%08x(T)]", tmpDesc);
#endif
            break;
        }
        else
#ifdef DESC_DUMP_BOTH_DESCnDATA
            A_PRINTF("0x%08x(0x%08x,%c)->", tmpDesc, tmpDesc->dataAddr, (tmpDesc->status&ZM_OWN_BITS_HW)?'H':'S');
#else
            A_PRINTF("0x%08x(%c)->", tmpDesc, (tmpDesc->status&ZM_OWN_BITS_HW)?'H':'S');
#endif
        
        if( (++i%5)==0 ) 
        {
            A_PRINTF("\n\r   ");
        }   
        
        tmpDesc = tmpDesc->nextAddr;            
    }while(1);   
    A_PRINTF("\n\r"); 
}
    
/* the exported entry point into this module. All apis are accessed through
 * function pointers */
void dma_engine_module_install(struct dma_engine_api *apis)
{    
        /* hook in APIs */
    apis->_init                 = _DMAengine_init;
    apis->_config_rx_queue      = _DMAengine_config_rx_queue;
    apis->_xmit_buf             = _DMAengine_xmit_buf;
    apis->_flush_xmit           = _DMAengine_flush_xmit;
    apis->_reap_recv_buf        = _DMAengine_reap_recv_buf;
    apis->_return_recv_buf      = _DMAengine_return_recv_buf;
    apis->_reap_xmited_buf      = _DMAengine_reap_xmited_buf;
    apis->_swap_data            = swapData;
    apis->_has_compl_packets    = _DMAengine_has_compl_packets;
    apis->_init_rx_queue        = _DMAengine_init_rx_queue;
    apis->_init_tx_queue        = _DMAengine_init_tx_queue;    
    apis->_desc_dump            = _DMAengine_desc_dump;
    apis->_get_packet           = zfDmaGetPacket;
    apis->_reclaim_packet       = zfDmaReclaimPacket;
    apis->_put_packet           = zfDmaPutPacket;
    
        /* save ptr to the ptr to the context for external code to inspect/modify internal module state */
    //apis->pReserved = &g_pMboxHWContext;
}
 
static void relinkUSBDescToVdesc(VBUF *buf, struct zsDmaDesc* desc)
{
    VDESC *vdesc;
    VDESC *prevVdesc = NULL;
    struct zsDmaDesc *currDesc = desc;
                 
    vdesc = VDESC_HW_TO_VDESC(currDesc);          
    buf->desc_list = vdesc;
    buf->buf_length = currDesc->totalLen;        
    
    while(currDesc != NULL) {      
        vdesc->data_size = currDesc->dataSize;                   
        //vdesc->data_offset = 0; // TODO: bad!!
        
        if ( prevVdesc == NULL ) {
            prevVdesc = vdesc;
        } else {
            prevVdesc->next_desc = vdesc;
            prevVdesc = vdesc;
        }
        
        if ( currDesc->ctrl & ZM_LS_BIT ) {
            vdesc->next_desc = NULL;
            currDesc = NULL;
            break;
        } else {
            currDesc = currDesc->nextAddr;
            vdesc = VDESC_HW_TO_VDESC(currDesc);
        }
    }        
}
