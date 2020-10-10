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

#ifndef _HIF_API_H
#define _HIF_API_H

#include <adf_nbuf.h>

/* mailbox hw module configuration structure */
typedef struct _HIF_CONFIG {
    int dummy;
} HIF_CONFIG;

typedef struct _HIF_CALLBACK {
    /* callback when a buffer has be sent to the host*/
    void (*send_buf_done)(adf_nbuf_t buf, void *context);
    /* callback when a receive message is received */
    void (*recv_buf)(adf_nbuf_t hdr_buf, adf_nbuf_t buf, void *context);
    /* context used for all callbacks */
    void *context;
} HIF_CALLBACK;

typedef void* hif_handle_t;

/* hardware API table structure (API descriptions below) */
struct hif_api {
    hif_handle_t (*_init)(HIF_CONFIG *pConfig);
            
    void (* _shutdown)(hif_handle_t);
    
    void (*_register_callback)(hif_handle_t, HIF_CALLBACK *);
    
    int  (*_get_total_credit_count)(hif_handle_t);
    
    void (*_start)(hif_handle_t);

    void (*_config_pipe)(hif_handle_t handle, int pipe, int creditCount);
    
    int  (*_send_buffer)(hif_handle_t handle, int pipe, adf_nbuf_t buf);

    void (*_return_recv_buf)(hif_handle_t handle, int pipe, adf_nbuf_t buf);                                 
    //void (*_set_recv_bufsz)(int pipe, int bufsz);
    //void (*_pause_recv)(int pipe);
    //void (*_resume_recv)(int pipe);
    int  (*_is_pipe_supported)(hif_handle_t handle, int pipe);
    
    int  (*_get_max_msg_len)(hif_handle_t handle, int pipe);
    
    int  (*_get_reserved_headroom)(hif_handle_t handle);
    
    void (*_isr_handler)(hif_handle_t handle);
    
    void (*_get_default_pipe)(hif_handle_t handle, A_UINT8 *pipe_uplink, A_UINT8 *pipe_downlink);
    
        /* room to expand this table by another table */
    void *pReserved;
};

extern void generic_hif_module_install(struct hif_api *apis);

#endif /* #ifndef _HIF_API_H */
