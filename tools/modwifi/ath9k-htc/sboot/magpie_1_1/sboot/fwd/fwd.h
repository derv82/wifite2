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
#ifndef __FWD_H
#define __FWD_H

#define FWD_TGT_RX_BUFS     5

typedef void (*jmp_func)(void);
/*
 * XXX Pack 'em
 */
typedef struct {
  a_uint16_t  more_data;     /* Is there more data? */
  a_uint16_t len;           /* Len this segment    */
  a_uint32_t offset;        /* Offset in the file  */
} fwd_cmd_t;
/*
 * No enums across platforms
 */
#define FWD_RSP_ACK     0x1
#define FWD_RSP_SUCCESS 0x2
#define FWD_RSP_FAILED  0x3

typedef struct {
    a_uint32_t  rsp;       /* ACK/SUCCESS/FAILURE */ 
    a_uint32_t  offset;    /* rsp for this ofset  */
}fwd_rsp_t;

typedef struct  {
    a_uint32_t     addr;
    hif_handle_t   hif_handle;
    a_uint8_t      rx_pipe;
    a_uint8_t      tx_pipe;
} fwd_tgt_softc_t;


hif_handle_t fwd_init();

void
fwd_retbuf_handler(VBUF *buf, void *ServiceCtx);
void 
fwd_hifrecv_handler(VBUF *hdr_buf, VBUF *buf, void *ServiceCtx );

#endif //__FWD_H
