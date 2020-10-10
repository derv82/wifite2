/*
 * @File: mbox_hw.h
 * 
 * @Abstract: mailbox hardware definitions
 * 
 * @Notes: 
 *  * 
 * Copyright (c) 2008 Atheros Communications Inc.
 * All rights reserved.
 *
 */

#ifndef __HIF_USB_H__
#define __HIF_USB_H__

#include <hif_api.h>

#include <sys_cfg.h>
#include <vdesc_api.h>
#include <vbuf_api.h>
//#include <desc.h>
//#include <dma_engine_api.h>

#define HIF_USB_PIPE_TX             1
#define HIF_USB_PIPE_RX             2
#define HIF_USB_PIPE_INTERRUPT      3
#define HIF_USB_PIPE_COMMAND        4
#define HIF_USB_PIPE_HP_TX          5
#define HIF_USB_PIPE_MP_TX          6

struct VBUF_QUEUE
{
    VBUF *head;
    VBUF *tail;
};

    /* the mailbox hardware layer context */
typedef struct _HIF_USB_CONTEXT {
    HIF_CALLBACK                hifCb; 
    struct zsDmaQueue           dnQ;
    struct zsTxDmaQueue         upQ;
#if SYSTEM_MODULE_HP_EP5
    struct zsDmaQueue           hpdnQ;  // high priority
#endif
#if SYSTEM_MODULE_HP_EP6
    struct zsDmaQueue           mpdnQ;  // medium priority
#endif
    //struct VBUF_QUEUE           upVbufQ;
    VBUF                 		*cmdQueue;
    struct VBUF_QUEUE           eventBufQ;
    
    // Left a door for extension the structure
    void *pReserved;      
} HIF_USB_CONTEXT;

void hif_usb_module_install(struct hif_api *apis);
             
#endif
