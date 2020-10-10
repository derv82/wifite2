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
 * @File: HIF_api.h
 * 
 * @Abstract: Host Interface api
 * 
 * @Notes:
 */

#ifndef _USB_FIFO_API_H
#define _USB_FIFO_API_H

#include "vbuf_api.h"

typedef struct _USB_FIFO_CONFIG {
        /* callback to get the buf for receiving commands from USB FIFO */
    VBUF* (*get_command_buf)(void);
        /* callback when receiving a command */
    void (*recv_command)(VBUF *cmd);    
        /* callback to get the buf for event to send to the host */
    VBUF* (*get_event_buf)(void);
        /* callback to indicate the event has been sent to the host */
    void (*send_event_done)(VBUF *buf);
    
        /* context used for all callbacks */
    //void *context;
} USB_FIFO_CONFIG;

/* hardware API table structure (API descriptions below) */
struct usbfifo_api {
    void (*_init)(USB_FIFO_CONFIG *pConfig);
    void (*_enable_event_isr)(void);

        /* room to expand this table by another table */
    void *pReserved;    
};

extern void usbfifo_module_install(struct usbfifo_api *apis);

#endif /* #ifndef _USB_FIFO_API_H */
