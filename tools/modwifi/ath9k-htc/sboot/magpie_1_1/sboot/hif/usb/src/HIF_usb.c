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
 * @File: HIF_usb.c
 * 
 * @Abstract: USB implementation of HIF
 * 
 * @Notes:
 */
#include "sys_cfg.h"
#include "dt_defs.h"
#include "reg_defs.h"

#include <osapi.h>
//#include <hif_api.h>
#include <Magpie_api.h>
#include <vdesc_api.h>
#include <adf_os_mem.h> 
#include <adf_os_io.h>
//#include <desc.h>
#include <dma_engine_api.h>

#include "hif_usb.h"

HIF_USB_CONTEXT g_hifUSBCtx;


static void send_buffer_via_fifo(VBUF *buf);
static int _HIFusb_get_reserved_headroom(hif_handle_t handle);
static struct zsDmaQueue* get_queue_from_pipe(int pipe);

int _HIFusb_get_max_msg_len(hif_handle_t handle, int pipe);

//#define OTUS_USB

static VBUF* usbfifo_get_command_buf()
{
    VBUF *buf;
     
    buf = g_hifUSBCtx.cmdQueue;
    g_hifUSBCtx.cmdQueue = buf->next_buf;
    buf->next_buf = NULL;
    return buf;
}

static void usbfifo_recv_command(VBUF *buf)
{
#if ENABLE_SW_SWAP_DATA_MODE
    VDESC *currVdesc;
    struct zsDmaDesc* usbDesc;
#endif
    
    #if ZM_FM_LOOPBACK == 1
    send_buffer_via_fifo(buf);
    #else
    
#if ENABLE_SW_SWAP_DATA_MODE
    currVdesc = (VDESC *)buf->desc_list;
    usbDesc = (struct zsDmaDesc *)currVdesc->hw_desc_buf;    
    usbDesc->dataSize = currVdesc->data_size;
    usbDesc->dataAddr = (volatile u32_t)(currVdesc->buf_addr + currVdesc->data_offset);
            
    DMA_Engine_swap_data(usbDesc);
#endif    
    g_hifUSBCtx.hifCb.recv_buf(NULL, buf, g_hifUSBCtx.hifCb.context);
    #endif
}

static VBUF* usbfifo_get_event_buf()
{
    VBUF *buf;

    buf = g_hifUSBCtx.eventBufQ.head;
    if ( g_hifUSBCtx.eventBufQ.head == g_hifUSBCtx.eventBufQ.tail ) {
        g_hifUSBCtx.eventBufQ.head = NULL;
        g_hifUSBCtx.eventBufQ.tail = NULL;
    } else {
        g_hifUSBCtx.eventBufQ.head = buf->next_buf;
    }

    buf->next_buf = NULL;    
    return buf;    
}

static void usbfifo_send_event_done(VBUF *buf)
{
    #if ZM_FM_LOOPBACK == 1    
        ; // LOOPBACK? 
    _HIFusb_return_recv_buf(NULL, HIF_USB_PIPE_COMMAND, buf);
    #else
    g_hifUSBCtx.hifCb.send_buf_done(buf, g_hifUSBCtx.hifCb.context); 
    #endif
}

#define MAGPIE_ENABLE_USBFIFO

hif_handle_t _HIFusb_init(HIF_CONFIG *pConfig) 
{
    USB_FIFO_CONFIG usbfifo;
    
#ifdef MAGPIE_ENABLE_USBFIFO    
    usbfifo.get_command_buf = usbfifo_get_command_buf;
    usbfifo.recv_command    = usbfifo_recv_command;
    usbfifo.get_event_buf   = usbfifo_get_event_buf;
    usbfifo.send_event_done = usbfifo_send_event_done;
    USBFIFO_init(&usbfifo);
#endif
    
    // Initialize the terminator descriptor for dnQ & upQ
    DMA_Engine_init_rx_queue(&g_hifUSBCtx.dnQ);
    DMA_Engine_init_tx_queue(&g_hifUSBCtx.upQ);
            
#if SYSTEM_MODULE_HP_EP5
    DMA_Engine_init_rx_queue(&g_hifUSBCtx.hpdnQ);    
#endif

#if SYSTEM_MODULE_HP_EP6
    DMA_Engine_init_rx_queue(&g_hifUSBCtx.mpdnQ); 
#endif

    g_hifUSBCtx.eventBufQ.head = NULL;
    g_hifUSBCtx.eventBufQ.tail = NULL;
    g_hifUSBCtx.cmdQueue = NULL;
    
    return NULL;
}

void _HIFusb_shutdown(hif_handle_t handle) 
{
    // nothing to do in FW
}

void _HIFusb_register_callback(hif_handle_t handle, HIF_CALLBACK *pConfig) 
{
    //HIF_INPROC_CONTEXT *hifInprocCtx = (HIF_INPROC_CONTEXT *)handle;        
    
    g_hifUSBCtx.hifCb.send_buf_done = pConfig->send_buf_done;
    g_hifUSBCtx.hifCb.recv_buf      = pConfig->recv_buf;
    g_hifUSBCtx.hifCb.context       = pConfig->context;
        
    return;
}

//#define MAGPIE_REG_USB_
void _HIFusb_start(hif_handle_t handle) 
{
#ifdef OTUS_USB    
    ZM_PTA_DN_DMA_ADDRH_REG = (u32_t)g_hifUSBCtx.dnQ.head >> 16;
    ZM_PTA_DN_DMA_ADDRL_REG = (u32_t)g_hifUSBCtx.dnQ.head & 0xffff;
    
    ZM_PTA_UP_DMA_ADDRH_REG = (u32_t)g_hifUSBCtx.upQ.head >> 16;
    ZM_PTA_UP_DMA_ADDRL_REG = (u32_t)g_hifUSBCtx.upQ.head & 0xffff;       
#else
    A_PRINTF("\n\r\t=>[dnQ] 0x%08x \n[", (u32_t)g_hifUSBCtx.dnQ.head);
    A_PRINTF("\t=>[upQ] 0x%08x \n[", (u32_t)g_hifUSBCtx.upQ.head);
    
    MAGPIE_REG_USB_RX0_DESC_START = (u32_t)g_hifUSBCtx.dnQ.head;
    MAGPIE_REG_USB_TX0_DESC_START = (u32_t)g_hifUSBCtx.upQ.head;
#if SYSTEM_MODULE_HP_EP5
    A_PRINTF("\t=>[hp dnQ] 0x%08x \n[", (u32_t)g_hifUSBCtx.hpdnQ.head);
    MAGPIE_REG_USB_RX1_DESC_START = (u32_t)g_hifUSBCtx.hpdnQ.head;
#endif

#if SYSTEM_MODULE_HP_EP6
    A_PRINTF("\t=>[mp dnQ] 0x%08x \n[", (u32_t)g_hifUSBCtx.mpdnQ.head);
    MAGPIE_REG_USB_RX2_DESC_START = (u32_t)g_hifUSBCtx.mpdnQ.head;
#endif

    MAGPIE_REG_USB_INTERRUPT_MASK =  0xffffffff;    // enable all interrupt, refer to 7-34, Ryan
    MAGPIE_REG_USB_RX0_DMA_START = 1; 

#if SYSTEM_MODULE_HP_EP5
    MAGPIE_REG_USB_RX1_DMA_START = 1;
 #endif

#if SYSTEM_MODULE_HP_EP6
    MAGPIE_REG_USB_RX2_DMA_START = 1;
#endif
#endif    
}

static int _HIFusb_get_reserved_headroom(hif_handle_t handle)
{
    return 0;
}

static void config_command_pipe(VDESC *desc_list)
{
    VDESC *theDesc;
    VBUF  *buf;
    
    theDesc = desc_list;
    while ( theDesc != NULL ) {
        buf = VBUF_alloc_vbuf();
        
        buf->desc_list = theDesc;
        theDesc = theDesc->next_desc;
        buf->desc_list->next_desc = NULL;
        
        if ( g_hifUSBCtx.cmdQueue == NULL ) {
            g_hifUSBCtx.cmdQueue = buf;
        } else {
            buf->next_buf = g_hifUSBCtx.cmdQueue;
            g_hifUSBCtx.cmdQueue = buf;
        }
    }    
}

static void enable_rx(int pipe)
{
    if ( pipe == HIF_USB_PIPE_TX ) {
        #ifdef OTUS_USB      
        ZM_PTA_DN_DMA_TRIGGER_REG = 1;
        #else
        MAGPIE_REG_USB_RX0_DMA_START = 1;
        #endif    
    }
#if SYSTEM_MODULE_HP_EP5
    else if ( pipe == HIF_USB_PIPE_HP_TX ) {
        MAGPIE_REG_USB_RX1_DMA_START = 1;
    }
#endif
#if SYSTEM_MODULE_HP_EP6
    else if ( pipe == HIF_USB_PIPE_MP_TX ) {
        MAGPIE_REG_USB_RX2_DMA_START = 1;
    }
#endif      
}

static struct zsDmaQueue* get_queue_from_pipe(int pipe)
{   
    struct zsDmaQueue* q = NULL;
    
    if ( pipe == HIF_USB_PIPE_TX ) {
        q = &g_hifUSBCtx.dnQ;      
    } 
#if SYSTEM_MODULE_HP_EP5
    else if ( pipe == HIF_USB_PIPE_HP_TX )
    {
        q = &g_hifUSBCtx.hpdnQ;
    }
#endif
#if SYSTEM_MODULE_HP_EP6
    else if ( pipe == HIF_USB_PIPE_MP_TX )
    {
        q = &g_hifUSBCtx.mpdnQ; 
    }
#endif
    else {
        adf_os_assert(0);
    }
    
    return q;
}

//#define MAX_TX_BUF_SIZE            ZM_BLOCK_SIZE
//#define MAX_TX_BUF_SIZE            1600

//void _HIFusb_config_pipe(hif_handle_t handle, int pipe, VDESC *desc_list)
void _HIFusb_config_pipe(hif_handle_t handle, int pipe, int creditCount)
{
    int i;
    VDESC *desc;
    VDESC *head = NULL;
    struct zsDmaQueue *q;
    
    if ( pipe != HIF_USB_PIPE_COMMAND ) {
        goto config_pipe;
    }
    
    // USB command pipe doesn't use FIFO
    for(i=0; i < creditCount; i++)
    {
        desc = VDESC_alloc_vdesc();
        
        adf_os_assert(desc != NULL);
        
        desc->buf_addr = (A_UINT8 *)adf_os_mem_alloc(HIF_get_max_msg_len(handle, pipe));
        desc->buf_size = HIF_get_max_msg_len(handle, pipe);
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
    
    config_command_pipe(head);
    return;
    
config_pipe:    
    q = get_queue_from_pipe(pipe);   
    DMA_Engine_config_rx_queue(q, creditCount, HIF_get_max_msg_len(handle, pipe));
    enable_rx(pipe);
    return;
}

static void send_buffer_via_fifo(VBUF *buf)
{
#if ENABLE_SW_SWAP_DATA_MODE
    VDESC *currVdesc;
    struct zsDmaDesc* usbDesc;
    
    //A_PRINTF("send_buffer_via_fifo buf len %d\n", buf->buf_length);
    currVdesc = (VDESC *)buf->desc_list;
    usbDesc = (struct zsDmaDesc *)currVdesc->hw_desc_buf;    
    usbDesc->dataSize = currVdesc->data_size;
    usbDesc->dataAddr = (volatile u32_t)(currVdesc->buf_addr + currVdesc->data_offset);
            
    DMA_Engine_swap_data(usbDesc);
#endif
    
    if ( g_hifUSBCtx.eventBufQ.head == NULL ) {
        g_hifUSBCtx.eventBufQ.head = buf;
        g_hifUSBCtx.eventBufQ.tail = buf;
    } else {
        g_hifUSBCtx.eventBufQ.tail->next_buf = buf;
        g_hifUSBCtx.eventBufQ.tail = buf;
    }
    
    USBFIFO_enable_event_isr();
}

int _HIFusb_send_buffer(hif_handle_t handle, int pipe, VBUF *buf)
{ 
    if ( pipe == HIF_USB_PIPE_INTERRUPT ) {
        send_buffer_via_fifo(buf);     
    } else {
        DMA_Engine_xmit_buf(&g_hifUSBCtx.upQ, buf);
#ifdef OTUS_USB                  
        ZM_PTA_UP_DMA_TRIGGER_REG = 1;
#else
        MAGPIE_REG_USB_TX0_DMA_START = 1;
#endif          
    }

    return 0;
}


void _HIFusb_return_recv_buf(hif_handle_t handle, int pipe, VBUF *buf)
{    
    struct zsDmaQueue *q;
    
    if ( pipe == HIF_USB_PIPE_COMMAND ) {
        if ( g_hifUSBCtx.cmdQueue == NULL ) {
            g_hifUSBCtx.cmdQueue = buf;
        } else {
            buf->next_buf = g_hifUSBCtx.cmdQueue;
            g_hifUSBCtx.cmdQueue = buf;
        }        
    } else {
        q = get_queue_from_pipe(pipe);
        DMA_Engine_return_recv_buf(q, buf);   
        enable_rx(pipe);              
    }
}
                           
void _HIFusb_set_recv_bufsz(hif_handle_t handle, int pipe, int bufsz)
{
    (void)pipe;
    (void)bufsz;    
}

void _HIFusb_pause_recv(hif_handle_t handle, int pipe)
{
    (void)pipe;
}

void _HIFusb_resume_recv(hif_handle_t handle, int pipe)
{
    (void)pipe;
}

int  _HIFusb_is_pipe_supported(hif_handle_t handle, int pipe)
{
    if ( pipe < HIF_USB_PIPE_TX || pipe > HIF_USB_PIPE_MP_TX ) {
        return 0;
    } else {    
        return 1;
    }
}
    
int _HIFusb_get_max_msg_len(hif_handle_t handle, int pipe)
{
    switch(pipe) {
        case HIF_USB_PIPE_INTERRUPT:
        case HIF_USB_PIPE_COMMAND:
            return 64;
            
        default:
            return 1600;
    }
}
    
static void handle_tx_complete_isr()
{
    VBUF *buf;
    
    //A_PRINTF("USB Tx complete\n\r");                           
    #if ZM_FM_LOOPBACK == 1
    VDESC *vdesc;
    struct zsDmaDesc* desc;
        
    desc = DMA_Engine_get_packet(&g_hifUSBCtx.upQ);
    vdesc = VDESC_HW_TO_VDESC(desc);
    
    if ( vdesc->control == HIF_USB_PIPE_TX ) {
        DMA_Engine_reclaim_packet(&g_hifUSBCtx.dnQ, desc);
    }
    #if SYSTEM_MODULE_HP_EP5  
    else if ( vdesc->control == HIF_USB_PIPE_HP_TX ) {
        DMA_Engine_reclaim_packet(&g_hifUSBCtx.hpdnQ, desc);
    }
    #endif
    #if SYSTEM_MODULE_HP_EP6
    else if ( vdesc->control == HIF_USB_PIPE_MP_TX ) {
        DMA_Engine_reclaim_packet(&g_hifUSBCtx.mpdnQ, desc);
    }    
    #endif
    
    #ifdef OTUS_USB            
    ZM_PTA_DN_DMA_TRIGGER_REG = 1;
    #else
    MAGPIE_REG_USB_RX0_DMA_START = 1;
    #endif            
    
    #else           			
	buf = DMA_Engine_reap_xmited_buf(&g_hifUSBCtx.upQ);
	g_hifUSBCtx.hifCb.send_buf_done(buf, g_hifUSBCtx.hifCb.context);
    #endif /* ZM_FM_LOOPBACK == 1 */    
}
    
static void handle_rx_complete_isr()
{
    VBUF *buf;
    
    #if ZM_FM_LOOPBACK == 1
    VDESC *vdesc;
    struct zsDmaDesc* desc;
               
    //A_PRINTF("USB Rx complete\n\r");    
    desc = DMA_Engine_get_packet(&g_hifUSBCtx.dnQ);
    vdesc = VDESC_HW_TO_VDESC(desc);
    vdesc->control = HIF_USB_PIPE_TX;
    
    DMA_Engine_put_packet(&g_hifUSBCtx.upQ, desc);
            
    #ifdef OTUS_USB 
    ZM_PTA_UP_DMA_TRIGGER_REG = 1;
    #else
    MAGPIE_REG_USB_TX0_DMA_START = 1;
    #endif
            
    #else
    buf = DMA_Engine_reap_recv_buf(&g_hifUSBCtx.dnQ);
    g_hifUSBCtx.hifCb.recv_buf(NULL, buf, g_hifUSBCtx.hifCb.context);
    #endif    
}
    
#if SYSTEM_MODULE_HP_EP5    
static void handle_hp_rx_complete_isr()
{
    VBUF *buf;
    
    #if ZM_FM_LOOPBACK == 1
    VDESC *vdesc;
    struct zsDmaDesc* desc;    
               
    desc = DMA_Engine_get_packet(&g_hifUSBCtx.hpdnQ);
    vdesc = VDESC_HW_TO_VDESC(desc);
    vdesc->control = HIF_USB_PIPE_HP_TX;
        
    DMA_Engine_put_packet(&g_hifUSBCtx.upQ, desc);
    MAGPIE_REG_USB_TX0_DMA_START = 1;

    #else
    buf = DMA_Engine_reap_recv_buf(&g_hifUSBCtx.hpdnQ);
    g_hifUSBCtx.hifCb.recv_buf(NULL, buf, g_hifUSBCtx.hifCb.context);
    #endif
}
#endif

#if SYSTEM_MODULE_HP_EP6
static void handle_mp_rx_complete_isr()
{
    VBUF *buf;
        
    #if ZM_FM_LOOPBACK == 1
    VDESC *vdesc;
    struct zsDmaDesc* desc;
               
    desc = DMA_Engine_get_packet(&g_hifUSBCtx.mpdnQ);
    vdesc = VDESC_HW_TO_VDESC(desc);
    vdesc->control = HIF_USB_PIPE_MP_TX;
        
    DMA_Engine_put_packet(&g_hifUSBCtx.upQ, desc);
    MAGPIE_REG_USB_TX0_DMA_START = 1;

    #else
    buf = DMA_Engine_reap_recv_buf(&g_hifUSBCtx.mpdnQ);
    g_hifUSBCtx.hifCb.recv_buf(NULL, buf, g_hifUSBCtx.hifCb.context);
    #endif
}
#endif
    
void _HIFusb_isr_handler(hif_handle_t h)
{
    //struct zsDmaDesc* desc;
    u32_t intr;

#ifdef OTUS_USB      
    intr = ZM_PTA_INT_FLAG_REG;
#else
    intr = MAGPIE_REG_USB_INTERRUPT;
#endif
    
#ifdef OTUS_USB     
    if ((intr & (ZM_PTA_DOWN_INT_BIT|ZM_PTA_UP_INT_BIT))!=0)
#else
    if ((intr & (MAGPIE_REG_USB_INTERRUPT_TX0_COMPL|MAGPIE_REG_USB_INTERRUPT_RX0_COMPL| 
        MAGPIE_REG_USB_INTERRUPT_RX1_COMPL|MAGPIE_REG_USB_INTERRUPT_RX2_COMPL)) != 0)
#endif        
    {       
#if SYSTEM_MODULE_HP_EP5
        do
        {
            if ( DMA_Engine_has_compl_packets(&g_hifUSBCtx.hpdnQ) )                  
            {
                handle_hp_rx_complete_isr();
            }       
            else
            {
                break;
            }
        }
        while(1);
#endif // endif SYSTEM_MODULE_HP_EP5               
         
#if SYSTEM_MODULE_HP_EP6
        do
        {
            if ( DMA_Engine_has_compl_packets(&g_hifUSBCtx.mpdnQ) )                
            {
                handle_mp_rx_complete_isr();
            }
            else
            {
                break;
            }           
        }
        while(1);
#endif // endif SYSTEM_MODULE_HP_EP5  
                 
        do
        {
            int check = 0;
            
            /* zgUpQ own bits changed */
            if ( DMA_Engine_has_compl_packets((struct zsDmaQueue *)&g_hifUSBCtx.upQ) )           
            {
                handle_tx_complete_isr();                       
                check = 1;
            }/* end of while */
                
            /* zgDnQ own bits changed */
            if ( DMA_Engine_has_compl_packets(&g_hifUSBCtx.dnQ) )                          
            {
                handle_rx_complete_isr();
                check = 1;
            }       
            
            if ( check == 0 )
            {
                break;
            }
        }       
        while(1);               
    }        
}

void _HIFusb_get_default_pipe(hif_handle_t handle, A_UINT8 *pipe_uplink, A_UINT8 *pipe_downlink)
{
    *pipe_uplink = HIF_USB_PIPE_COMMAND;            // Host   -> Target
    *pipe_downlink = HIF_USB_PIPE_INTERRUPT;        // Target -> Host
}
    
/* the exported entry point into this module. All apis are accessed through
 * function pointers */
void hif_usb_module_install(struct hif_api *apis)
{    
        /* hook in APIs */
    apis->_init = _HIFusb_init;
    apis->_start = _HIFusb_start;
    apis->_config_pipe = _HIFusb_config_pipe;
    apis->_isr_handler = _HIFusb_isr_handler;
    apis->_send_buffer = _HIFusb_send_buffer;
    apis->_return_recv_buf = _HIFusb_return_recv_buf;
    apis->_is_pipe_supported = _HIFusb_is_pipe_supported;
    apis->_get_max_msg_len = _HIFusb_get_max_msg_len;
    apis->_register_callback = _HIFusb_register_callback;
    apis->_shutdown = _HIFusb_shutdown;
    apis->_get_reserved_headroom = _HIFusb_get_reserved_headroom;
    apis->_get_default_pipe = _HIFusb_get_default_pipe;
        
        /* save ptr to the ptr to the context for external code to inspect/modify internal module state */
    //apis->pReserved = &g_pMboxHWContext;
}

void HIFusb_DescTraceDump(void )
{    
#if SYSTEM_MODULE_HP_EP5
    A_PRINTF("\n\r[hp dnQ] 0x%08x, ", (u32_t)g_hifUSBCtx.hpdnQ.head);
    A_PRINTF("DMA TRACE 0x%08x\n\r    [", HAL_WORD_REG_READ(MAGPIE_REG_USB_RX1_CUR_TRACE_ADDR));

    DMA_Engine_desc_dump(&g_hifUSBCtx.hpdnQ);
#endif

#if SYSTEM_MODULE_HP_EP6
    A_PRINTF("\n\r[mp dnQ] 0x%08x, ", (u32_t)g_hifUSBCtx.mpdnQ.head);
    A_PRINTF("DMA TRACE 0x%08x\n\r    [", HAL_WORD_REG_READ(MAGPIE_REG_USB_RX2_CUR_TRACE_ADDR));

    DMA_Engine_desc_dump(&g_hifUSBCtx.mpdnQ);
#endif

    A_PRINTF("\n\r[dnQ] 0x%08x, ", (u32_t)g_hifUSBCtx.dnQ.head);
    A_PRINTF("DMA TRACE 0x%08x\n\r    [", HAL_WORD_REG_READ(MAGPIE_REG_USB_RX0_CUR_TRACE_ADDR));
    DMA_Engine_desc_dump(&g_hifUSBCtx.dnQ);

    A_PRINTF("\n\n\r[upQ] 0x%08x, ", (u32_t)g_hifUSBCtx.upQ.head);
    A_PRINTF("DMA TRACE 0x%08x\n\r    [", HAL_WORD_REG_READ(MAGPIE_REG_USB_TX0_CUR_TRACE_ADDR));
    DMA_Engine_desc_dump((struct zsDmaQueue *)&g_hifUSBCtx.upQ);
}


