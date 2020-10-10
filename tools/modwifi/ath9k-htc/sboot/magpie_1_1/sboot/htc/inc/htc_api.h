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
 * @File: htc_api.h
 * 
 * @Abstract: host-target communications API
 * 
 * @Notes: 
 */

#ifndef __HTC_API_H__
#define __HTC_API_H__

#include <osapi.h>
#include <htc.h>
//#include <htc_buf.h>
//#include <htc_services.h>
#include <adf_nbuf.h>
#include <buf_pool_api.h>

#define HTC_HDR_SZ          HTC_HDR_LENGTH
#define HTC_BUFSZ_MAX_SEND  2048

typedef void (* HTC_SERVICE_ProcessRecvMsg)(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t, adf_nbuf_t, void *ServiceCtx);
typedef void (* HTC_SERVICE_ProcessSendBufferComplete)(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t, void *ServiceCtx);
 
/* HTC service structure :
 * the caller is required to allocate storage for the service structure and register the
 * structure using HTC_RegisterService()  The service must set the following fields:
 *    ProcessRecvMsg
 *    ProcessSendBufferComplete
 *    ProcessConnect
 *    ServiceID
 *    MaxSvcMsgSize (for message validation)
 * */
typedef struct _HTC_SERVICE {
    struct _HTC_SERVICE *pNext;
        /* Callback for processing receive messages.  HTC calls this callback whenever a 
         * message arrives on the endpoint assigned to this service.
         * HTC_BUFFER is a chain of buffers containing a full application message.
         * HTC_BUFFER->buffer points to the start of the msg buffer (past the HTC header) */
    //void (* ProcessRecvMsg)(HTC_ENDPOINT_ID EndpointID, HTC_BUFFER *); 
    void (* ProcessRecvMsg)(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t, adf_nbuf_t, void *ServiceCtx); 
        /* callback to process completed send buffers */
    //void (* ProcessSendBufferComplete)(HTC_ENDPOINT_ID EndpointID, HTC_BUFFER *); 
    void (* ProcessSendBufferComplete)(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t, void *ServiceCtx); 
        /* optional callback when a connection request occurs.
         * The EndpointID is the assigned endpoint, the callback returns a connect 
         * response status code to allow or disallow the connection.
         * pDataIn points to the optional meta data supplied in the connection request
         * pDataOut points to a buffer to send back meta data 
         * If no callback is supplied, HTC assumes the connect is allowed  */
    A_UINT8 (* ProcessConnect)(struct _HTC_SERVICE *pService,
                               HTC_ENDPOINT_ID     EndpointID, 
                               A_UINT8 *pDataIn, 
                               int      LengthIn,
                               A_UINT8 *pDataOut,
                               int     *pLengthOut); 
    A_UINT16  ServiceID;        /* service ID to match connection requests */
    A_UINT16  ServiceFlags;     /* service flags */
    A_UINT16  MaxSvcMsgSize;    /* maximum length of service-specific messages exchanged on the endpoint */
    A_UINT16  TrailerSpcCheckLimit;  /* amount of space in each send buffer that HTC can check for trailer
                                        data. This should be set to the smallest HTC buffer that can be sent 
                                        through the service. The service can disable trailer data insertion
                                        by setting this value to 0. */
    void      *ServiceCtx;
} HTC_SERVICE;

#define HTC_SERVICE_FLAGS_CONNECTED         (1 << 0)  /* service has at least 1 connection */

#define IS_SERVICE_CONNECTED(s) ((s)->ServiceFlags & HTC_SERVICE_FLAGS_CONNECTED)

   /* configuration settings for the WMI service */
typedef struct _HTC_CONFIG {
    int         CreditSize;    /*  */
    int         CreditNumber;
    //int         ControlDownLinkPipeID;
    //int         ControlUpLinkPipeID;
    adf_os_handle_t   OSHandle;
    hif_handle_t      HIFHandle;
    pool_handle_t     PoolHandle;
} HTC_CONFIG;

typedef struct _HTC_BUF_CONTEXT {
    A_UINT8         end_point;
    A_UINT8         htc_flags;      /* htc flags (used by HTC layer only) */     
} HTC_BUF_CONTEXT;

typedef void* htc_handle_t;

/*
 * setup complete function, supplied by HTC caller at HTC_init time.
 * HTC calls this function after the host has indicated that the service connection
 * phase is complete.
 * 
 */
typedef void (* HTC_SETUP_COMPLETE_CB)(void);

struct htc_apis {
    htc_handle_t (* _HTC_Init)(HTC_SETUP_COMPLETE_CB, HTC_CONFIG *pConfig);    
    void (* _HTC_Shutdown)(htc_handle_t);
    void (* _HTC_RegisterService)(htc_handle_t, HTC_SERVICE *);
    void (* _HTC_Ready)(htc_handle_t);
    void (* _HTC_ReturnBuffers)(htc_handle_t handle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t);
    void (* _HTC_ReturnBuffersList)(htc_handle_t handle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_queue_t);
    void (* _HTC_SendMsg)(htc_handle_t handle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t);        
    int  (* _HTC_GetReservedHeadroom)(htc_handle_t handle);
    
    //void (* _HTC_PauseRecv)(HTC_ENDPOINT_ID EndpointID);
    //void (* _HTC_ResumeRecv)(HTC_ENDPOINT_ID EndpointID);
    //void (* _HTC_AddBufferResources)(int buffers);
    
    /* These APIs below are for patch purpose only */
    void (*_HTC_MsgRecvHandler)(adf_nbuf_t hdr_buf, adf_nbuf_t buf, void *context);
    void (*_HTC_SendDoneHandler)(adf_nbuf_t buf, void *context);
    void (*_HTC_ControlSvcProcessMsg)(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t hdr_buf, adf_nbuf_t buf, void *arg);
    void (*_HTC_ControlSvcProcessSendComplete)(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers, void *arg);
    
    void *pReserved;  /* for expansion if need be */
};

extern void htc_module_install(struct htc_apis *pAPIs);

#endif /* _HTC_API_H__ */
