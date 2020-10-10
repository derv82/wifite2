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
 * @File: 
 * 
 * @Abstract: Wireless Module Interface Service Implementation
 * 
 * @Notes: 
 */
#include <osapi.h>
#include <Magpie_api.h>
#include <htc.h>
#include <htc_services.h>
#include <wmi_svc_api.h>
#include <adf_os_mem.h> 
#include <adf_os_io.h>

#include "wmi_internal.h"

static void WMIRecvMessageHandler(HTC_ENDPOINT_ID EndPt, adf_nbuf_t hdr_buf,
				  adf_nbuf_t pHTCBuf, void *arg)
{
	void *pContext;
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)arg;
	WMI_DISPATCH_TABLE *pCurrentTable;
	WMI_DISPATCH_ENTRY*pCurrentEntry;    
	WMI_CMD_HANDLER pCmdHandler;
	A_UINT8* pCmdBuffer; 
	int i;
	A_UINT16 cmd;
	A_UINT16 seq;
	int length;
	a_uint8_t *anbdata;
	a_uint32_t anblen;
	WMI_CMD_HDR *cmdHdr;
            
	adf_os_assert(hdr_buf == ADF_NBUF_NULL);

	do {
		length = adf_nbuf_len(pHTCBuf);
		if (length < sizeof(WMI_CMD_HDR)) {
			break;    
		}

		adf_nbuf_peek_header(pHTCBuf, &anbdata, &anblen);
        
		pCurrentTable = pWMI->pDispatchHead;
		length = length - sizeof(WMI_CMD_HDR);
        
		cmdHdr = (WMI_CMD_HDR *)anbdata;
		cmd = adf_os_ntohs(cmdHdr->commandId);
		seq = adf_os_ntohs(cmdHdr->seqNo);
        
		pCmdBuffer = anbdata + sizeof(WMI_CMD_HDR); 
		pCmdHandler = NULL;
        
		while (pCurrentTable != NULL) {
            
			pContext = pCurrentTable->pContext;
			pCurrentEntry = pCurrentTable->pTable;
        
			/* scan table entries */
			for (i = 0; i < pCurrentTable->NumberOfEntries; i++, pCurrentEntry++) {
				if (pCurrentEntry->CmdID == cmd) {
					/* found a match */
					pCmdHandler = pCurrentEntry->pCmdHandler;
        
					/* optionally check length */
					if ((pCurrentEntry->CheckLength != 0) &&
					    (length < pCurrentEntry->CheckLength)) {
						/* do not process command */
						pCmdHandler = NULL;
					}
					/* end search */                
					break;    
				}                        
			} 
            
			if (pCmdHandler != NULL) {
				/* found a handler */
				break;
			}
                
			/* scan next table */
			pCurrentTable = pCurrentTable->pNext;
		}
         
		if (NULL == pCmdHandler) {
			break;    
		}
            
		/* if we get here, we have a command handler to dispatch */
                
		/* call dispatch function */
		pCmdHandler(pContext, cmd, seq, pCmdBuffer, length);
                  
	} while (FALSE);
    
    
        /* Invalidate the buffer (including HTC header). Note : we only need to invalidate up to the portion
	 * that was used (cache invalidate will also round up to the nearest cache line).  
	 * The rest of the buffer should still be coherent.
	 * */

	HTC_ReturnBuffers(pWMI->HtcHandle, EndPt, pHTCBuf);         
}

/* send completion handler when any HTC buffers are returned */
static void _WMI_SendCompleteHandler(HTC_ENDPOINT_ID Endpt, adf_nbuf_t pHTCBuf, void *arg)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)arg;
	WMI_BUF_CONTEXT *ctx;
	BUF_POOL_ID poolId;
    
	ctx = (WMI_BUF_CONTEXT *)adf_nbuf_get_priv(pHTCBuf);
        
	if ( ctx->EventClass == WMI_EVT_CLASS_CMD_EVENT ) {
		poolId = POOL_ID_WMI_SVC_EVENT;
	} else {
		poolId = POOL_ID_WMI_SVC_CMD_REPLY;
	}
        
	BUF_Pool_free_buf(pWMI->PoolHandle, poolId, pHTCBuf);
}

static A_UINT8 WMIServiceConnect(HTC_SERVICE *pService,
                                 HTC_ENDPOINT_ID eid, 
                                 A_UINT8 *pDataIn, 
                                 int LengthIn,
                                 A_UINT8 *pDataOut,
                                 int *pLengthOut)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)pService->ServiceCtx;
    
        /* save the eid to use */
	pWMI->ControlEp = eid;
	return HTC_SERVICE_SUCCESS;
}

/**************  public APIS ********************************************/
    
static wmi_handle_t _WMI_Init(WMI_SVC_CONFIG *pWmiConfig)
{
	WMI_SVC_CONTEXT *pWMI = NULL;
	int eventSize = WMI_SVC_MAX_BUFFERED_EVENT_SIZE + sizeof(WMI_CMD_HDR) + HTC_HDR_SZ;
    
	pWMI = (WMI_SVC_CONTEXT *)adf_os_mem_alloc(sizeof(WMI_SVC_CONTEXT));
	if (pWMI == NULL) {
		return NULL;    
	}
        
	pWMI->pDispatchHead = NULL;
	pWMI->PoolHandle = pWmiConfig->PoolHandle;
	pWMI->HtcHandle = pWmiConfig->HtcHandle;    
                                         
	BUF_Pool_create_pool(pWmiConfig->PoolHandle, POOL_ID_WMI_SVC_CMD_REPLY, 
			     pWmiConfig->MaxCmdReplyEvts, eventSize);
        
	BUF_Pool_create_pool(pWmiConfig->PoolHandle, POOL_ID_WMI_SVC_EVENT, 
			     pWmiConfig->MaxEventEvts, eventSize);
            
	/* NOTE: since RAM allocation is zero-initialized, there is nothing to do for the 
	 * direct event pool */
     
        /* register the WMI control service */
	pWMI->WMIControlService.ProcessRecvMsg = A_INDIR(wmi_svc_api._WMI_RecvMessageHandler);
	pWMI->WMIControlService.ProcessSendBufferComplete = A_INDIR(wmi_svc_api._WMI_SendCompleteHandler);
	pWMI->WMIControlService.ProcessConnect = A_INDIR(wmi_svc_api._WMI_ServiceConnect);
	pWMI->WMIControlService.MaxSvcMsgSize = WMI_SVC_MSG_SIZE + sizeof(WMI_CMD_HDR);
        /* all buffers that are sent through the control endpoint are at least WMI_SVC_MAX_BUFFERED_EVENT_SIZE 
         * in size.  Any WMI event that supplies a data buffer must insure that the space in the buffer
         * is at least this size. */
	pWMI->WMIControlService.TrailerSpcCheckLimit = WMI_SVC_MAX_BUFFERED_EVENT_SIZE; 
	pWMI->WMIControlService.ServiceID = WMI_CONTROL_SVC;
	pWMI->WMIControlService.ServiceCtx = pWMI;
	HTC_RegisterService(pWmiConfig->HtcHandle, &pWMI->WMIControlService);
    
	return pWMI;
}

static int _WMI_GetPendingEventsCount(wmi_handle_t handle)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)handle;
	return pWMI->PendingEvents;
}

static int  _WMI_GetControlEp(wmi_handle_t handle)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)handle;
	return pWMI->ControlEp;
}

static void _WMI_RegisterDispatchTable(wmi_handle_t handle,
				       WMI_DISPATCH_TABLE *pDispatchTable)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)handle;
    
	if (NULL == pWMI->pDispatchHead) {
		pWMI->pDispatchHead = pDispatchTable;
		pWMI->pDispatchTail = pDispatchTable;        
	} else {
		/* link to the tail */
		pWMI->pDispatchTail->pNext = pDispatchTable;
		pWMI->pDispatchTail = pDispatchTable;        
	}
}

static adf_nbuf_t _WMI_AllocEvent(wmi_handle_t handle, WMI_EVT_CLASS EventClass,
				  int Length)
{     
	BUF_POOL_ID poolId;
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)handle;
	adf_nbuf_t buf;
	WMI_BUF_CONTEXT *ctx;
    
	if ( EventClass == WMI_EVT_CLASS_CMD_EVENT ) {
		poolId = POOL_ID_WMI_SVC_EVENT;
	} else {
		poolId = POOL_ID_WMI_SVC_CMD_REPLY;
	}
    
	buf = BUF_Pool_alloc_buf(pWMI->PoolHandle, 
				 poolId, 
				 sizeof(WMI_CMD_HDR) + HTC_GetReservedHeadroom(pWMI->HtcHandle));
     
	if ( buf != NULL ) {
		ctx = (WMI_BUF_CONTEXT *)adf_nbuf_get_priv(buf);
		ctx->EventClass = EventClass;
	}
	return buf;
}

static void _WMI_SendEvent(wmi_handle_t handle, adf_nbuf_t pEvt, 
                           A_UINT16 EventId, A_UINT16 SeqNo, int Length)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)handle;
	A_UINT8 *pBuffer;
        
	pBuffer = adf_nbuf_push_head(pEvt, sizeof(WMI_CMD_HDR));
	A_SET_UINT16_FIELD(pBuffer, WMI_CMD_HDR, commandId, adf_os_htons(EventId));        
	A_SET_UINT16_FIELD(pBuffer, WMI_CMD_HDR, seqNo, adf_os_htons(SeqNo));
	
	HTC_SendMsg(pWMI->HtcHandle, pWMI->ControlEp, pEvt);    
}

static void _WMI_Shutdown(wmi_handle_t handle)
{
	WMI_SVC_CONTEXT *pWMI = (WMI_SVC_CONTEXT *)handle;

	adf_os_mem_free(pWMI);
}

void WMI_service_module_install(WMI_SVC_APIS *pTbl)
{
	pTbl->_WMI_Init                     = _WMI_Init;
	pTbl->_WMI_RegisterDispatchTable    = _WMI_RegisterDispatchTable;
	pTbl->_WMI_AllocEvent               = _WMI_AllocEvent;
	pTbl->_WMI_SendEvent                = _WMI_SendEvent;
	pTbl->_WMI_SendCompleteHandler      = _WMI_SendCompleteHandler;
	pTbl->_WMI_GetPendingEventsCount    = _WMI_GetPendingEventsCount;
	pTbl->_WMI_GetControlEp             = _WMI_GetControlEp;
	pTbl->_WMI_Shutdown                 = _WMI_Shutdown;
	pTbl->_WMI_RecvMessageHandler       = WMIRecvMessageHandler;
	pTbl->_WMI_ServiceConnect           = WMIServiceConnect;
}
