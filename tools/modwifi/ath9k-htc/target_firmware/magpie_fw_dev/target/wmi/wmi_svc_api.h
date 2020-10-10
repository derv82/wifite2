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
 * This file contains the API for the Wireless Module Interface (WMI) Service
 */

#ifndef WMI_SVC_API_H_
#define WMI_SVC_API_H_

#include <htc.h>
#include <htc_api.h>
#include <wmi.h>
#include <adf_nbuf.h>
#include <buf_pool_api.h>

#define WMI_SVC_MAX_BUFFERED_EVENT_SIZE 100
#define WMI_SVC_MSG_SIZE                1536    /* maximum size of any WMI control or event message */

/* event classes */
typedef enum WMI_EVT_CLASS {
	WMI_EVT_CLASS_NONE = -1,
	WMI_EVT_CLASS_CMD_EVENT = 0,
	WMI_EVT_CLASS_CMD_REPLY = 1,            
	WMI_EVT_CLASS_MAX
} WMI_EVT_CLASS;

/* command handler callback when a message is dispatched */
typedef void (* WMI_CMD_HANDLER)(void *pContext,     /* application supplied context from dispatch table */
                                 A_UINT16 Command,      /* command ID that was dispatched */
                                 A_UINT16 SeqNo,
                                 A_UINT8 *pCmdBuffer,   /* command data, 256 bytes max, 32-bit aligned */
                                 int Length);      /* length of command (excludes WMI header) */

/* configuration settings for the WMI service */
typedef struct _WMI_SVC_CONFIG {
	htc_handle_t    HtcHandle;
	pool_handle_t   PoolHandle;
	int             MaxCmdReplyEvts;    /* total buffers for command replies */
	int             MaxEventEvts;       /* total buffers for low priority events */
} WMI_SVC_CONFIG;
                                                
/* command dispatch entry */
typedef struct _WMI_DISPATCH_ENTRY {
	WMI_CMD_HANDLER      pCmdHandler;    /* dispatch function */
	A_UINT16             CmdID;          /* WMI command to dispatch from */
	A_UINT16             CheckLength;    /* expected length of command, set to 0 to bypass check */    
} WMI_DISPATCH_ENTRY;

/* dispatch table that is used to register a set of dispatch entries */
typedef struct _WMI_DISPATCH_TABLE {
	struct _WMI_DISPATCH_TABLE *pNext;              /* next dispatch, WMI-reserved */
	void                       *pContext;           /* optional context that is passed to command handlers 
							   assigned to this dispatch table  */
	int                         NumberOfEntries;    /* number of elements pointed to by pTable */
	WMI_DISPATCH_ENTRY         *pTable;             /* start of table */
} WMI_DISPATCH_TABLE;

#define WMI_DISPATCH_ENTRY_COUNT(table) \
    (sizeof((table)) / sizeof(WMI_DISPATCH_ENTRY))  

    /* handy macro to declare a dispatch table */
#define WMI_DECLARE_DISPATCH_TABLE(name,dispatchEntries)         \
WMI_DISPATCH_TABLE name =                                        \
{   NULL, NULL, WMI_DISPATCH_ENTRY_COUNT(dispatchEntries), dispatchEntries }

    /* macro to programatically set the dispatch table context */
#define WMI_SET_DISPATCH_CONTEXT(pDispTable, pCtxt)  (pDispTable)->pContext = (pCtxt)

typedef struct _WMI_BUF_CONTEXT {
	HTC_BUF_CONTEXT     HtcBufCtx;
        
	WMI_EVT_CLASS       EventClass;   /* the event class this packet belongs to */ 
	A_UINT16            Flags;        /* internal flags reserved for WMI */     
} WMI_BUF_CONTEXT;

/* ROM-version, eventually. For now, in RAM */
    
typedef void* wmi_handle_t;
   
/* the API table */
typedef struct _wmi_svc_apis {
	wmi_handle_t    (* _WMI_Init)(WMI_SVC_CONFIG *pWmiConfig);
	void            (* _WMI_RegisterDispatchTable)(wmi_handle_t h, WMI_DISPATCH_TABLE *pDispatchTable);
	adf_nbuf_t      (* _WMI_AllocEvent)(wmi_handle_t h, WMI_EVT_CLASS EventClass, int Length);
	void            (* _WMI_SendEvent)(wmi_handle_t h, adf_nbuf_t pEvt, A_UINT16 EventId, A_UINT16 SeqNo, int Length);
	int             (* _WMI_GetPendingEventsCount)(wmi_handle_t handle);
	void            (* _WMI_SendCompleteHandler)(HTC_ENDPOINT_ID Endpt, adf_nbuf_t pHTCBuf, void *arg);
	int             (* _WMI_GetControlEp)(wmi_handle_t h);
	void            (* _WMI_Shutdown)(wmi_handle_t h);
    
	/* */
	void            (*_WMI_RecvMessageHandler)(HTC_ENDPOINT_ID EndPt, adf_nbuf_t hdr_buf, adf_nbuf_t pHTCBuf, void *arg);
	A_UINT8         (*_WMI_ServiceConnect)(HTC_SERVICE *pService, HTC_ENDPOINT_ID eid, 
					       A_UINT8 *pDataIn, 
					       int LengthIn,
					       A_UINT8 *pDataOut,
					       int *pLengthOut);
                                 
	void            *pReserved;  /* for expansion if need be */
} WMI_SVC_APIS;

extern void WMI_service_module_install(WMI_SVC_APIS *pAPIs);

#endif /*WMI_SVC_API_H_*/
