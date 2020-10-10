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
 * @File: mbox_hw.h
 * 
 * @Abstract: mailbox hardware definitions
 * 
 * @Notes: 
 */

#ifndef __HIF_USB_H__
#define __HIF_USB_H__

#include <sys_cfg.h>
#include <vdesc_api.h>
//#include <desc.h>
#include <dma_engine_api.h>

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

             
#endif
