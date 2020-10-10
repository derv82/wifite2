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
 * @Abstract: host target communications
 * 
 * @Notes: 
 */
#include <osapi.h>
#include <Magpie_api.h> 
#include <htc.h>
#include <htc_api.h>
#include <hif_api.h>
#include <adf_os_mem.h> 
#include <adf_os_io.h> 

#include "htc_internal.h" 

//#define A_ASSERT(m)
#define A_UNCACHED_ADDR(addr) addr
//#define A_MEMZERO(v, size)

/*** statics vars ****/ 
//HTC_CONTEXT g_htcCtx;
//HTC_CONTEXT *g_pHTC = NULL;
 
/* prototypes */
LOCAL void HTCControlSvcProcessMsg(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t hdr_buf, adf_nbuf_t pBuffers, void *arg);
LOCAL void HTCControlSvcProcessSendComplete(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers, void *arg);
LOCAL void HTCMsgRecvHandler(adf_nbuf_t hdr_buf, adf_nbuf_t buf, void *context);
LOCAL void HTCSendDoneHandler(adf_nbuf_t buf, void *context);
LOCAL void HTCFreeMsgBuffer(HTC_CONTEXT *pHTC, adf_nbuf_t pBuffer);
LOCAL adf_nbuf_t HTCAllocMsgBuffer(HTC_CONTEXT *pHTC);
//LOCAL void HTC_EnqueuePausedRecv(HTC_ENDPOINT *pEndpoint, 
//                                 VBUF   *pFirstBuf,
//                                 VBUF   *pLastBuf);
//LOCAL VBUF* HTC_DequeuePausedRecv(HTC_ENDPOINT *pEndpoint);
LOCAL void HTCCheckAndSendCreditReport(HTC_CONTEXT *pHTC, A_UINT32 EpMask, HTC_ENDPOINT *pEndpoint, HTC_ENDPOINT_ID Id);
LOCAL void AdjustCreditThreshold(HTC_ENDPOINT  *pEndpoint);
//LOCAL void _HTC_AddBufferResources(int buffers);
LOCAL void HTC_AssembleBuffers(HTC_CONTEXT *pHTC, int Count, int Size);
LOCAL htc_handle_t _HTC_Init(/*A_UINT32 dataAddr,*/
        HTC_SETUP_COMPLETE_CB SetupComplete,
                         HTC_CONFIG *pConfig);
LOCAL void _HTC_RegisterService(htc_handle_t handle, HTC_SERVICE *pService);
LOCAL void _HTC_Ready(htc_handle_t handle);
LOCAL void ReturnBuffers(htc_handle_t htcHandle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers, A_BOOL sendCreditFlag);
LOCAL void _HTC_ReturnBuffers(htc_handle_t handle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers);
LOCAL void _HTC_ReturnBuffersList(htc_handle_t htcHandle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_queue_t bufHead);
LOCAL void _HTC_SendMsg(htc_handle_t handle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers);
void _HTC_PauseRecv(HTC_ENDPOINT_ID EndpointID);
void _HTC_ResumeRecv(HTC_ENDPOINT_ID EndpointID);
LOCAL void HTCProcessConnectMsg(HTC_CONTEXT *pHTC, HTC_CONNECT_SERVICE_MSG *pMsg);
LOCAL void HTCProcessConfigPipeMsg(HTC_CONTEXT *pHTC, HTC_CONFIG_PIPE_MSG *pMsg);
LOCAL void RedistributeCredit(adf_nbuf_t buf, int toPipeId);                         
LOCAL void _HTC_Shutdown(htc_handle_t htcHandle);

     /* macro to check if the service wants to prevent credit dribbling by using 
        a dynamic threshold */
#define CHECK_AND_ADJUST_CREDIT_THRESHOLD(pEndpoint)                                        \
    if ((pEndpoint)->ConnectionFlags & HTC_CONNECT_FLAGS_REDUCE_CREDIT_DRIBBLE) { \
        AdjustCreditThreshold((pEndpoint));                                       \
    }    

/***********************************************************************************************/
/************************ MODULE API implementation *******************************************/
#if 0
LOCAL void _HTC_AddBufferResources(int buffers)
{
    (void)buffers;
    //MboxHW_AddDMAResources(buffers);   
}
#endif

LOCAL void HTC_AssembleBuffers(HTC_CONTEXT *pHTC, int Count, int Size)
{
    BUF_Pool_create_pool(pHTC->PoolHandle, POOL_ID_HTC_CONTROL, Count, Size);       
}


LOCAL htc_handle_t _HTC_Init(HTC_SETUP_COMPLETE_CB SetupComplete,
                             HTC_CONFIG *pConfig)
{
    HIF_CALLBACK       hifCBConfig;
    HTC_CONTEXT        *pHTC;    
    
    //if (NULL == g_pHTC) 
    {
        pHTC = (HTC_CONTEXT *)adf_os_mem_alloc(sizeof(HTC_CONTEXT));
        //g_pHTC = &g_htcCtx;
    } 
    
    adf_os_mem_zero(pHTC, sizeof(HTC_CONTEXT));

    pHTC->OSHandle = pConfig->OSHandle;
    pHTC->PoolHandle = pConfig->PoolHandle;
    pHTC->hifHandle = pConfig->HIFHandle;
                        
    //A_MEMZERO(&hwConfig,sizeof(hwConfig));  
    hifCBConfig.send_buf_done = A_INDIR(htc._HTC_SendDoneHandler);
    hifCBConfig.recv_buf = A_INDIR(htc._HTC_MsgRecvHandler);
    hifCBConfig.context = pHTC;
    
    /* initialize hardware layer */
    HIF_register_callback(pConfig->HIFHandle, &hifCBConfig);
                             
        /* see if the host wants us to override the number of ctrl buffers */
    //g_pHTC->NumBuffersForCreditRpts = (HOST_INTEREST->hi_mbox_io_block_sz >> 16) & 0xF;
    pHTC->NumBuffersForCreditRpts = 0;
    
    if (0 == pHTC->NumBuffersForCreditRpts) {
        /* nothing to override, simply set default */
        pHTC->NumBuffersForCreditRpts = HTC_DEFAULT_NUM_CTRL_BUFFERS; 
    }    
    
    //g_pHTC->MaxEpPendingCreditRpts = (HOST_INTEREST->hi_mbox_io_block_sz >> 20) & 0xF;
    pHTC->MaxEpPendingCreditRpts = 0;
    
    if (0 == pHTC->MaxEpPendingCreditRpts) {
        pHTC->MaxEpPendingCreditRpts = HTC_DEFAULT_MAX_EP_PENDING_CREDIT_REPORTS;    
    }
    /* calculate the total allocation size based on the number of credit report buffers */
    pHTC->CtrlBufferAllocSize = MIN_CREDIT_BUFFER_ALLOC_SIZE * pHTC->NumBuffersForCreditRpts;
    /* we need at least enough buffer space for 1 ctrl message */
    pHTC->CtrlBufferAllocSize = A_MAX(pHTC->CtrlBufferAllocSize,MAX_HTC_SETUP_MSG_SIZE);
    
    //A_PRINTF("%d, %d, (%d, %d) %s-%s \n",g_pHTC->NumBuffersForCreditRpts,g_pHTC->CtrlBufferAllocSize,
    //                        MIN_BUF_SIZE_FOR_RPTS, MIN_CREDIT_BUFFER_ALLOC_SIZE,__DATE__, __TIME__);
                                          
    /* save the size of each buffer/credit we will receive */
    pHTC->RecvBufferSize = pConfig->CreditSize; //RecvBufferSize;
    pHTC->TotalCredits = pConfig->CreditNumber;
    //g_pHTC->FreeCreditList = pConfig->CreditList;
    pHTC->TotalCreditsAssigned = 0;
     
    /* setup the pseudo service that handles HTC control messages */
    pHTC->HTCControlService.ProcessRecvMsg = A_INDIR(htc._HTC_ControlSvcProcessMsg);
    pHTC->HTCControlService.ProcessSendBufferComplete = A_INDIR(htc._HTC_ControlSvcProcessSendComplete);
    pHTC->HTCControlService.TrailerSpcCheckLimit = HTC_CTRL_BUFFER_CHECK_SIZE;
    pHTC->HTCControlService.MaxSvcMsgSize = MAX_HTC_SETUP_MSG_SIZE;
    pHTC->HTCControlService.ServiceCtx = pHTC;
    
    /* automatically register this pseudo service to endpoint 1 */
    pHTC->Endpoints[ENDPOINT0].pService = &pHTC->HTCControlService;
    HIF_get_default_pipe(pHTC->hifHandle, &pHTC->Endpoints[ENDPOINT0].UpLinkPipeID, 
                                          &pHTC->Endpoints[ENDPOINT0].DownLinkPipeID);
    
    /* Initialize control pipe so we could receive the HTC control packets */
    // @TODO: msg size!
    HIF_config_pipe(pHTC->hifHandle, pHTC->Endpoints[ENDPOINT0].UpLinkPipeID, 1);    
    
    /* set the first free endpoint */
    pHTC->CurrentEpIndex = ENDPOINT1;
    pHTC->SetupCompleteCb = SetupComplete;
    
        /* setup buffers for just the setup phase, we only need 1 buffer to handle
        * setup */
    HTC_AssembleBuffers(pHTC, 4, MAX_HTC_SETUP_MSG_SIZE);
   
    /* start hardware layer so that we can queue buffers */
    HIF_start(pHTC->hifHandle);
    
    return pHTC;
}

LOCAL void _HTC_Shutdown(htc_handle_t htcHandle)
{
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;
    
    adf_os_mem_free(pHTC);
}

LOCAL void _HTC_RegisterService(htc_handle_t htcHandle, HTC_SERVICE *pService)
{
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;
    
        /* add it to the list */
    pService->pNext = pHTC->pServiceList;
    pHTC->pServiceList = pService;
}

LOCAL void _HTC_Ready(htc_handle_t htcHandle)
{
    adf_nbuf_t      pBuffer;
    HTC_READY_MSG   *pReady;
    a_uint8_t       *addr;
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;
    
    pBuffer = HTCAllocMsgBuffer(pHTC);
    //A_ASSERT(pBuffer != NULL);
       
    /* an optimization... the header length is chosen to
     * be aligned on a 16 bit bounday, the fields in the message are designed to
     * be aligned */
    addr = adf_nbuf_put_tail(pBuffer, sizeof(HTC_READY_MSG));       
    pReady = (HTC_READY_MSG *)addr;     
    A_MEMZERO(pReady,sizeof(HTC_READY_MSG));  
    pReady->MessageID = adf_os_htons(HTC_MSG_READY_ID);
    pReady->CreditSize = adf_os_htons((A_UINT16)pHTC->RecvBufferSize);
    //A_ASSERT(g_pHTC->TotalCredits <= MAX_HTC_CREDITS);
    pReady->CreditCount = adf_os_htons((A_UINT16)pHTC->TotalCredits);
    pReady->MaxEndpoints = ENDPOINT_MAX;
       
    /* send out the message */
    //A_DATA_CACHE_FLUSH(pBuffer->buffer, pBuffer->actual_length);    
    HTC_SendMsg(pHTC, ENDPOINT0, pBuffer);
    /* now we need to wait for service connection requests */
}

LOCAL void ReturnBuffers(htc_handle_t htcHandle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers, A_BOOL sendCreditFlag)
{   
    int         nbufs = 1;
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;
    
    //A_ASSERT(EndpointID < ENDPOINT_MAX);
 
    /* supply some head-room again */
    adf_nbuf_push_head(pBuffers, HTC_HDR_LENGTH);
    //A_DATA_CACHE_INVAL(pBuffers->buffer, pBuffers->actual_length + HTC_HDR_SZ);
              
    /* enqueue all buffers to the single mailbox */
    HIF_return_recv_buf(pHTC->hifHandle, pHTC->Endpoints[EndpointID].UpLinkPipeID, pBuffers);    
    //A_ASSERT(nbufs != 0);
     
    if (pHTC->StateFlags & HTC_STATE_SETUP_COMPLETE) {       
        A_UINT32    epCreditMask = (1 << EndpointID);
        /* we are running normally */
        /* update pending credit counts with the number of buffers that were added */
        pHTC->Endpoints[EndpointID].CreditsToReturn += (A_INT16)nbufs;
        pHTC->Endpoints[EndpointID].CreditsConsumed -= (A_INT16)nbufs;  
        //A_ASSERT(g_pHTC->Endpoints[EndpointID].CreditsConsumed >= 0);          
        /* update bit map that this endpoint has non-zero credits */
        pHTC->EpCreditPendingMap |= epCreditMask; 

        if (sendCreditFlag) {
            HTCCheckAndSendCreditReport(pHTC, epCreditMask,&pHTC->Endpoints[EndpointID],EndpointID);
        }

    } else {
        /* we have not started yet so all return operations are simply adding buffers
         * to the interface at startup, so we can keep track of how many total 
         * credits we get */
        /* update global count that will be returned to the host */
        pHTC->TotalCredits += nbufs;
    }     
}

LOCAL void _HTC_ReturnBuffersList(htc_handle_t htcHandle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_queue_t bufHead)
{
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;
    adf_nbuf_t netbuf, tmpNbuf;

    /* retrieve each nbuf in the queue */
    netbuf = adf_nbuf_queue_first(&bufHead);

    while (netbuf) {

        tmpNbuf = netbuf;
        netbuf = adf_nbuf_queue_next(netbuf);

        ReturnBuffers(htcHandle, EndpointID, tmpNbuf, FALSE);
    }

    HTCCheckAndSendCreditReport(pHTC, (1 << EndpointID),&pHTC->Endpoints[EndpointID],EndpointID);
}

LOCAL void _HTC_ReturnBuffers(htc_handle_t htcHandle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers)
{
    ReturnBuffers(htcHandle, EndpointID, pBuffers, TRUE);
}
 
LOCAL void _HTC_SendMsg(htc_handle_t htcHandle, HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers)
{
    HTC_FRAME_HDR       *pHTCHdr;
    int                 totsz;
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;  
    HTC_BUF_CONTEXT *ctx;
    
    ctx = (HTC_BUF_CONTEXT *)adf_nbuf_get_priv(pBuffers);
    
    /* init total size (this does not include the space we will put in for the HTC header) */
    totsz = adf_nbuf_len(pBuffers);
    
    /* the first buffer stores the header */
        /* back up buffer by a header size when we pass it down, by agreed upon convention the caller
    * points the buffer to it's payload and leaves head room for the HTC header  
    * Note: in HTCSendDoneHandler(), we undo this so that the caller get's it's buffer
        *       back untainted */   
    pHTCHdr = (HTC_FRAME_HDR *)adf_nbuf_push_head(pBuffers, HTC_HDR_LENGTH);
    
    /* flag that this is the header buffer that was modified */
    ctx->htc_flags |= HTC_FLAGS_BUF_HDR;   
    /* mark where this buffer came from */
    ctx->end_point = EndpointID;      
    /* the header start is ALWAYS aligned since we DMA it directly */
    //pHTCHdr = (HTC_FRAME_HDR *)A_UNCACHED_ADDR(VBUF_GET_DATA_ADDR(pBuffers));
        /* set some fields, the rest of them will be filled below when we check for
        * trailer space */
    pHTCHdr->Flags = 0;
    pHTCHdr->EndpointID = EndpointID;    
       
    //A_ASSERT(totsz <= g_pHTC->Endpoints[EndpointID].pService->MaxSvcMsgSize);  
    /* check opportunistically if we can return any reports via a trailer */
    do {
        int               room,i,totalReportBytes;
        A_UINT32          creditsPendingMap, compareMask;
        HTC_CREDIT_REPORT *pCreditRpt;
        HTC_RECORD_HDR    *pRecHdr;
        int               pipeMaxLen;
        A_UINT32          roomForPipeMaxLen;
                          
        /* figure out how much room the last buffer can spare */
        pipeMaxLen = HIF_get_max_msg_len(pHTC->hifHandle, pHTC->Endpoints[EndpointID].DownLinkPipeID);
        roomForPipeMaxLen = pipeMaxLen - adf_nbuf_headroom(pBuffers) - adf_nbuf_len(pBuffers);
        if ( roomForPipeMaxLen < 0 ) {
            roomForPipeMaxLen = 0;
        }
                        
        room = adf_os_min( adf_nbuf_tailroom(pBuffers), roomForPipeMaxLen);
        if (room < (int)(sizeof(HTC_CREDIT_REPORT) + sizeof(HTC_RECORD_HDR))) {
            /* no room for any reports */
            break;    
        }   
            /* note, a record header only has 8 bit fields, so this is safe.
            * we need an uncached pointer here too */            
        totalReportBytes = 0;
        
        /* get a copy */        
        creditsPendingMap = pHTC->EpCreditPendingMap;   
                           
            /* test pending map to see if we can send a report , if any
        * credits are available, we might as well send them on the 
            * unused space in the buffer */
        if (creditsPendingMap) { 
            
            pRecHdr = (HTC_RECORD_HDR *)adf_nbuf_put_tail(pBuffers, sizeof(HTC_RECORD_HDR));            
            
                /* set the ID, the length will be updated with the number of credit reports we
                * can fit (see below) */
            pRecHdr->RecordID = HTC_RECORD_CREDITS;
            pRecHdr->Length = 0;
            /* the credit report follows the record header */         
            totalReportBytes += sizeof(HTC_RECORD_HDR);
            room -= sizeof(HTC_RECORD_HDR);
            
            /* walkthrough pending credits map and build the records */
            for (i = 0; 
                 (creditsPendingMap != 0) && (room >= (int)sizeof(HTC_CREDIT_REPORT)); 
                 i++) {                
                     compareMask = (1 << i);
                     if (compareMask & creditsPendingMap) {
                        
                         pCreditRpt = (HTC_CREDIT_REPORT *)adf_nbuf_put_tail(pBuffers, sizeof(HTC_CREDIT_REPORT));
                                    
                         /* clear pending mask, we are going to return all these credits */
                         creditsPendingMap &= ~(compareMask);
                         /* add this record */
                         pCreditRpt->EndpointID = i;
                         pCreditRpt->Credits = (A_UINT8)pHTC->Endpoints[i].CreditsToReturn;
                         /* remove pending credits, we always send deltas */
                         pHTC->Endpoints[i].CreditsToReturn = 0; 
                         /* adjust new threshold for this endpoint if needed */
                         CHECK_AND_ADJUST_CREDIT_THRESHOLD(&pHTC->Endpoints[i]);
                         /* update this record length */
                         pRecHdr->Length += sizeof(HTC_CREDIT_REPORT);
                         room -= sizeof(HTC_CREDIT_REPORT);
                         totalReportBytes += sizeof(HTC_CREDIT_REPORT);

                         if ( room < sizeof(HTC_CREDIT_REPORT) ) {
                             break;
                         }
                     }
                 }
            
                 /* update new pending credits map */       
                 pHTC->EpCreditPendingMap = creditsPendingMap;
        }
        
        if (totalReportBytes <= 0) {
            break;
        }
        
            /* must fit into a byte, this should never actually happen since
        * the maximum possible number of endpoints is 32. 
        * The trailer can have at most 1 credit record with up to 32  reports in the record.
        * The trailer can have at most 1 lookahead record with only 1 lookahead report in the record.
        * 
            * */
        //A_ASSERT(totalReportBytes <= 255);
        
        /* set header option bytes */ 
        pHTCHdr->ControlBytes[0] = totalReportBytes;
        /* HTC frame contains a trailer */
        pHTCHdr->Flags |= HTC_FLAGS_RECV_TRAILER;
        /* increment total size by the reports we added */
        totsz += totalReportBytes;
        /* adjust the last buffer we used for adding on the trailer */                                 
    } while (FALSE);
          
    if (totsz == 0) {
        //A_ASSERT(FALSE);
    }
    
    /* set length for message (this includes any reports that were added above) */
    pHTCHdr->PayloadLen = adf_os_htons(totsz);  
    HIF_send_buffer(pHTC->hifHandle, pHTC->Endpoints[EndpointID].DownLinkPipeID, pBuffers);       
}

void _HTC_PauseRecv(HTC_ENDPOINT_ID EndpointID)
{
#if 0  // Disable first. Ray
#ifdef HTC_PAUSE_RESUME_REF_COUNTING    
    g_pHTC->Endpoints[EndpointID].PauseRefCount++;
#endif
        /* we are now paused */
    g_pHTC->EpRecvPausedMap |= (1 << EndpointID);
#endif    
}

void _HTC_ResumeRecv(HTC_ENDPOINT_ID EndpointID)
{
#if 0  // Disable first. Ray    
    HTC_BUFFER      *buffer;
    HTC_ENDPOINT    *pEndpoint;
    
    pEndpoint = &g_pHTC->Endpoints[EndpointID];

/* TODO: we can't quite use referencing counting yet until we clean up the WLAN
 * app, there are some un-matched pause/resume cases that need to be fixed */
#ifdef HTC_PAUSE_RESUME_REF_COUNTING  
    pEndpoint->PauseRefCount--;
    //A_ASSERT(pEndpoint->PauseRefCount >= 0);
    
        /* check reference count and unpause if it is zero */
    if (pEndpoint->PauseRefCount > 0) {
        return;    
    }   
#endif

    g_pHTC->EpRecvPausedMap &= ~(1 << EndpointID);        
        /* unload the paused receive queue */
    while ((buffer = HTC_DequeuePausedRecv(pEndpoint)) != NULL) {          
        /* note that the paused messages have already been processed at the HTC layer,
         * we can simply indicate the buffers to the service */
        pEndpoint->pService->ProcessRecvMsg(EndpointID,buffer);    
    }
#endif    
}

int _HTC_GetReservedHeadroom(htc_handle_t htcHandle)
{
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)htcHandle;  
    
    return HTC_HDR_LENGTH + HIF_get_reserved_headroom(pHTC->hifHandle);
}
    
void htc_module_install(struct htc_apis *pAPIs)
{   
    pAPIs->_HTC_Init = _HTC_Init;
    pAPIs->_HTC_ReturnBuffers = _HTC_ReturnBuffers;
    pAPIs->_HTC_ReturnBuffersList = _HTC_ReturnBuffersList;
    pAPIs->_HTC_Ready = _HTC_Ready;
    pAPIs->_HTC_RegisterService = _HTC_RegisterService;
    pAPIs->_HTC_SendMsg = _HTC_SendMsg;   
    pAPIs->_HTC_Shutdown = _HTC_Shutdown;
    pAPIs->_HTC_GetReservedHeadroom = _HTC_GetReservedHeadroom;
    pAPIs->_HTC_MsgRecvHandler = HTCMsgRecvHandler;
    pAPIs->_HTC_SendDoneHandler = HTCSendDoneHandler;
    pAPIs->_HTC_ControlSvcProcessMsg = HTCControlSvcProcessMsg;
    pAPIs->_HTC_ControlSvcProcessSendComplete = HTCControlSvcProcessSendComplete;
    
    //pAPIs->_HTC_PauseRecv = _HTC_PauseRecv;
    //pAPIs->_HTC_ResumeRecv = _HTC_ResumeRecv; 
    //pAPIs->_HTC_AddBufferResources = _HTC_AddBufferResources;
        /* save ptr to the ptr to the context for external code to inspect/modify internal module state */
    //pAPIs->pReserved = &g_pHTC;
}

/*******************************************************************************************/
/****************   INTERNAL ROUTINES to this MODULE ***************************************/

/* free message to the free list */
//LOCAL void HTCFreeMsgBuffer(HTC_BUFFER *pBuffer)
LOCAL void HTCFreeMsgBuffer(HTC_CONTEXT *pHTC, adf_nbuf_t buf) 
{
    BUF_Pool_free_buf(pHTC->PoolHandle, POOL_ID_HTC_CONTROL, buf);      
}

/* HTC control message allocator (also used for empty frames to send trailer options) */
//LOCAL HTC_BUFFER *HTCAllocMsgBuffer(void)
LOCAL adf_nbuf_t HTCAllocMsgBuffer(HTC_CONTEXT *pHTC)
{
    return BUF_Pool_alloc_buf(pHTC->PoolHandle, POOL_ID_HTC_CONTROL, HTC_GetReservedHeadroom(pHTC));   
}

LOCAL void HTCCheckAndSendCreditReport(HTC_CONTEXT *pHTC, A_UINT32 EpMask, HTC_ENDPOINT *pEndpoint, HTC_ENDPOINT_ID Eid)
{
    adf_nbuf_t  pCredBuffer;
    HTC_BUF_CONTEXT *ctx;    
        
    do {
        /* check if host needs credits */
        if (!(pHTC->EpHostNeedsCreditMap & EpMask)) {
            /* host does not need any credits for this set */
            break;    
        }
        /* check if any are pending */
        if (!(pHTC->EpCreditPendingMap & EpMask)) {
            /* nothing to send up */
            break;    
        }  
        /* was an endpoint specified? */
        if (pEndpoint != NULL) {
            /* see if a threshold is in effect for this endpoint */
            if (pEndpoint->CreditReturnThreshhold != 0) {
                if (pEndpoint->CreditsToReturn < pEndpoint->CreditReturnThreshhold) {
                    /* this endpoint is using a threshold to prevent credits from dribbling
                     * back to the host */
                    break;
                }
            }
         
            if (pEndpoint->PendingCreditReports >= pHTC->MaxEpPendingCreditRpts) {
                /* this endpoint already has some reports outstanding */
                /* flag that as soon as a buffer is reaped, we issue a credit update to
                 * pick up this credit that is being held up because the endpoint has already
                 * exceeded the max outstanding credit report limit */    
               pHTC->StateFlags |= HTC_SEND_CREDIT_UPDATE_SOON;
                break;    
            }                         
        }
        
        /* if we get here we have some credits to send up */
                        
        /* allocate a message buffer for the trailer */
        pCredBuffer = HTCAllocMsgBuffer(pHTC);
        if (NULL == pCredBuffer) {
            /* no buffers left to send an empty message with trailers, host will just
            * have to wait until we get our endpoint 0 messages back.. */
            /* mark that we need to send an update as soon as we can get a buffer back */
            pHTC->StateFlags |= HTC_SEND_CREDIT_UPDATE_SOON;
            break;    
        }
        
        ctx = (HTC_BUF_CONTEXT *)adf_nbuf_get_priv(pCredBuffer);
        if (pEndpoint != NULL) {
            /* keep track of pending reports */
            pEndpoint->PendingCreditReports++; 
            /* save the endpoint in order to decrement the count when the send completes */
            ctx->htc_flags = Eid | HTC_FLAGS_CREDIT_RPT;
        }   
            
        /* this is an empty message, the HTC_SendMsg will tack on a trailer in the remaining
         * space, NOTE: no need to flush the cache, the header and trailers are assembled
         * using uncached addresses */
        HTC_SendMsg(pHTC, ENDPOINT0, pCredBuffer);    
    
    } while (FALSE);      
}
        
/* called in response to the arrival of a service connection message */
LOCAL void HTCProcessConnectMsg(HTC_CONTEXT *pHTC, HTC_CONNECT_SERVICE_MSG *pMsg)
{
    HTC_SERVICE                         *pService = pHTC->pServiceList;
    A_UINT8                             connectStatus = HTC_SERVICE_NOT_FOUND;
    //HTC_BUFFER                          *pBuffer;
    adf_nbuf_t                          pBuffer;
    HTC_CONNECT_SERVICE_RESPONSE_MSG    *pRspMsg;
    int                                 metaDataOutLen = 0;
    A_UINT16                            serviceId = adf_os_ntohs(pMsg->ServiceID);
    
    pBuffer = HTCAllocMsgBuffer(pHTC);
    //A_ASSERT(pBuffer != NULL);
    /* note : this will be aligned */
    pRspMsg = (HTC_CONNECT_SERVICE_RESPONSE_MSG *)
                adf_nbuf_put_tail(pBuffer, sizeof(HTC_CONNECT_SERVICE_RESPONSE_MSG));
                                 
    A_MEMZERO(pRspMsg,sizeof(HTC_CONNECT_SERVICE_RESPONSE_MSG));
    pRspMsg->MessageID = adf_os_htons(HTC_MSG_CONNECT_SERVICE_RESPONSE_ID);
    /* reflect the service ID for this connect attempt */
    pRspMsg->ServiceID = adf_os_htons(serviceId);

    while (pService) {
        
        if (pHTC->CurrentEpIndex >= ENDPOINT_MAX) {
            /* no more endpoints */
            connectStatus = HTC_SERVICE_NO_RESOURCES;
            break;    
        }

        if (serviceId == pService->ServiceID) {
            /* we found a match */             
            A_UINT8     *pMetaDataIN = NULL; 
            A_UINT8     *pMetaDataOut;
            
            /* outgoing meta data resides in the space after the response message */
            pMetaDataOut = ((A_UINT8 *)pRspMsg) + sizeof(HTC_CONNECT_SERVICE_RESPONSE_MSG);
            
            if (pMsg->ServiceMetaLength != 0) {
                //A_ASSERT(pMsg->ServiceMetaLength <= HTC_SERVICE_META_DATA_MAX_LENGTH);
                /* the meta data follows the connect service message */
                pMetaDataIN = ((A_UINT8 *)pMsg) + sizeof(HTC_CONNECT_SERVICE_MSG);
            }

            //A_ASSERT(pService->ProcessConnect != NULL);
            /* call the connect callback with the endpoint to use and pointers to meta data */
            connectStatus = pService->ProcessConnect(pService,
                    pHTC->CurrentEpIndex,
                    pMetaDataIN,
                    pMsg->ServiceMetaLength,
                    pMetaDataOut,
                    &metaDataOutLen);
            
            /* check if the service accepted this connection request */
            if (HTC_SERVICE_SUCCESS == connectStatus) {
                //A_ASSERT(metaDataOutLen <= HTC_SERVICE_META_DATA_MAX_LENGTH);
                /* set the length of the response meta data going back to the host */
                pRspMsg->ServiceMetaLength = (A_UINT8)metaDataOutLen;
                /* set the endpoint ID the host will now communicate over */
                pRspMsg->EndpointID = pHTC->CurrentEpIndex;
                /* return the maximum message size for this service */
                pRspMsg->MaxMsgSize = adf_os_htons((A_UINT16)pService->MaxSvcMsgSize);
                /* assign this endpoint to this service, this will be used in routing messages */
                pHTC->Endpoints[pHTC->CurrentEpIndex].pService = pService;
                /* set connection flags */
                pHTC->Endpoints[pHTC->CurrentEpIndex].ConnectionFlags = pMsg->ConnectionFlags;
                
                pHTC->Endpoints[pHTC->CurrentEpIndex].DownLinkPipeID = pMsg->DownLinkPipeID;
                pHTC->Endpoints[pHTC->CurrentEpIndex].UpLinkPipeID = pMsg->UpLinkPipeID;
                
                /* mark that we are now connected */
                pService->ServiceFlags |= HTC_SERVICE_FLAGS_CONNECTED;
                /* bump up our index, this EP is now in use */
                pHTC->CurrentEpIndex++;   
            }

            break;
        }       
        
        pService = pService->pNext;   
    }
                   
    pRspMsg->Status = connectStatus;    
    
    /* send out the response message */
    //A_DATA_CACHE_FLUSH(pBuffer->buffer, pBuffer->actual_length);
    HTC_SendMsg(pHTC, ENDPOINT0, pBuffer); 
}

LOCAL void HTCProcessConfigPipeMsg(HTC_CONTEXT *pHTC, HTC_CONFIG_PIPE_MSG *pMsg)
{
    //HTC_SERVICE                         *pService = g_pHTC->pServiceList;
    //A_UINT8                             connectStatus = HTC_SERVICE_NOT_FOUND;
    adf_nbuf_t                          pBuffer;
    HTC_CONFIG_PIPE_RESPONSE_MSG        *pRspMsg;
        
    pBuffer = HTCAllocMsgBuffer(pHTC);
       
    //A_ASSERT(pBuffer != NULL);
    /* note : this will be aligned */
    pRspMsg = (HTC_CONFIG_PIPE_RESPONSE_MSG *)
                adf_nbuf_put_tail(pBuffer, sizeof(HTC_CONFIG_PIPE_RESPONSE_MSG));    
              
    A_MEMZERO(pRspMsg,sizeof(HTC_CONFIG_PIPE_RESPONSE_MSG));
    
    pRspMsg->MessageID = adf_os_htons(HTC_MSG_CONFIG_PIPE_RESPONSE_ID);
    /* reflect the service ID for this connect attempt */
    pRspMsg->PipeID = pMsg->PipeID;

    if ( HIF_is_pipe_supported(pHTC->hifHandle, pMsg->PipeID) ) {
        pRspMsg->Status = 0;            
    } else {
        pRspMsg->Status = 1; 
        goto config_done;
    }

    if ( (pHTC->TotalCreditsAssigned + pMsg->CreditCount) <= pHTC->TotalCredits ) {
        pHTC->TotalCreditsAssigned += pMsg->CreditCount;
    } else {
        pRspMsg->Status = 2;
        goto config_done;
    }
    
    HIF_config_pipe(pHTC->hifHandle, pMsg->PipeID, pMsg->CreditCount);
    
config_done:      
    /* send out the response message */
    //A_DATA_CACHE_FLUSH(pBuffer->buffer, pBuffer->actual_length);    
    HTC_SendMsg(pHTC, ENDPOINT0, pBuffer);             
}

/* process an incomming control message from the host */
LOCAL void HTCControlSvcProcessMsg(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t hdr_buf, adf_nbuf_t pBuffers, void *arg)
{  
    A_BOOL setupComplete = FALSE;
    a_uint8_t *anbdata;
    a_uint32_t anblen;
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)arg;
    HTC_UNKNOWN_MSG  *pMsg;
	
    adf_os_assert(hdr_buf == ADF_NBUF_NULL);

    /* we assume buffers are aligned such that we can access the message
    * parameters directly*/
    adf_nbuf_peek_header(pBuffers, &anbdata, &anblen);
    pMsg = (HTC_UNKNOWN_MSG *)anbdata;
    
    /* we cannot handle fragmented messages across buffers */
    //A_ASSERT(pBuffers->next == NULL);
    
    switch ( adf_os_ntohs(pMsg->MessageID) ) {        
        case HTC_MSG_CONNECT_SERVICE_ID:
            //A_ASSERT(pBuffers->actual_length >= sizeof(HTC_CONNECT_SERVICE_MSG));
            HTCProcessConnectMsg(pHTC, (HTC_CONNECT_SERVICE_MSG *)pMsg); 
            break;
        case HTC_MSG_CONFIG_PIPE_ID:
            HTCProcessConfigPipeMsg(pHTC, (HTC_CONFIG_PIPE_MSG *)pMsg); 
            break;            
        case HTC_MSG_SETUP_COMPLETE_ID:
                /* the host has indicated that it has completed all
            setup tasks and we can now let the services take over to
            run the rest of the application */
            setupComplete = TRUE;  
            /* can't get this more than once */
            //A_ASSERT(!(g_pHTC->StateFlags & HTC_STATE_SETUP_COMPLETE));            
            break;
        default:
            ;
            //A_ASSERT(FALSE);
    }  
        
    if (pHTC->StateFlags & HTC_STATE_SETUP_COMPLETE) {
        /* recycle buffer only if we are fully running */
        HTC_ReturnBuffers(pHTC, ENDPOINT0,pBuffers);
    } else {
        /* supply some head-room again */
        //A_DATA_CACHE_INVAL(pBuffers->buffer, pBuffers->actual_length + HTC_HDR_SZ);
        adf_nbuf_push_head(pBuffers, HTC_HDR_LENGTH);
            
        /* otherwise return the packet back to mbox */
        HIF_return_recv_buf(pHTC->hifHandle, pHTC->Endpoints[EndpointID].UpLinkPipeID, pBuffers);        
    }

    if (setupComplete) {        
        /* mark that setup has completed */
        pHTC->StateFlags |= HTC_STATE_SETUP_COMPLETE; 
        if (pHTC->SetupCompleteCb != NULL) {
            pHTC->SetupCompleteCb();
        }
    }
}

/* callback when endpoint 0 send buffers are completed */
LOCAL void HTCControlSvcProcessSendComplete(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t pBuffers, void *arg)
{
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)arg;
    HTC_BUF_CONTEXT *ctx;
    HTC_ENDPOINT_ID  creditRptEndpoint;
    
    ctx = (HTC_BUF_CONTEXT *)adf_nbuf_get_priv(pBuffers);       
    
    //A_ASSERT(EndpointID == ENDPOINT0);
    
    /* put them back into the pool */
#if 0    
    while (pBuffers != NULL) {
        pNext = pBuffers->next_buf;
        pBuffers->next_buf = NULL;       
        /* note: HTC does not send fragmented control messages, so each buffer
        * represents 1 full HTC control message */  
        if (pBuffers->desc_list->control & HTC_FLAGS_CREDIT_RPT) {                      
            /* extract the endpoint number that requested this credit report */     
            creditRptEndpoint = pBuffers->desc_list->control & HTC_FLAGS_CRPT_EP_MASK;    
            pBuffers->desc_list->control = 0;
            g_pHTC->Endpoints[creditRptEndpoint].PendingCreditReports--;  
            //A_ASSERT(g_pHTC->Endpoints[creditRptEndpoint].PendingCreditReports >= 0);           
        }
        /* free this one */
        HTCFreeMsgBuffer(pBuffers);
        pBuffers = pNext;
    }
#else
    if ( ctx->htc_flags & HTC_FLAGS_CREDIT_RPT ) {   
        /* extract the endpoint number that requested this credit report */ 
        creditRptEndpoint = ctx->htc_flags & HTC_FLAGS_CRPT_EP_MASK;    
        pHTC->Endpoints[creditRptEndpoint].PendingCreditReports--;  
        //A_ASSERT(g_pHTC->Endpoints[creditRptEndpoint].PendingCreditReports >= 0);             
    }
    
    HTCFreeMsgBuffer(pHTC, pBuffers);
#endif  
   
    if (pHTC->StateFlags & HTC_SEND_CREDIT_UPDATE_SOON) {
        /* this flag is set when the host could not send a credit report
         * because we ran out of HTC control buffers */
        pHTC->StateFlags &= ~HTC_SEND_CREDIT_UPDATE_SOON;
        /* send out a report if anything is pending */
        HTCCheckAndSendCreditReport(pHTC, HTC_ANY_ENDPOINT_MASK,NULL,ENDPOINT_MAX);
    }  
}

LOCAL void HTCSendDoneHandler(adf_nbuf_t buf, void *context)
{
    A_UINT8      current_eid;
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)context;
    HTC_BUF_CONTEXT *ctx;
      
    ctx = (HTC_BUF_CONTEXT *)adf_nbuf_get_priv(buf);
    current_eid = ctx->end_point;
        
    /* Walk through the buffers and fixup the ones we used for HTC headers.
     * The buffer list may contain more than one string of HTC buffers comprising of an
    * HTC message so we need to check every buffer */            
    adf_nbuf_pull_head(buf, HTC_HDR_LENGTH);
                   
    pHTC->Endpoints[current_eid].pService->
        ProcessSendBufferComplete(current_eid, 
                                  buf, 
                                  pHTC->Endpoints[current_eid].pService->ServiceCtx); 
}

#if 0
LOCAL void HTC_EnqueuePausedRecv(HTC_ENDPOINT *pEndpoint, 
                                 HTC_BUFFER *pFirstBuf,
                                 HTC_BUFFER *pLastBuf)
{
    //A_ASSERT(pLastBuf->next == NULL);
    
    if (NULL == pEndpoint->pRcvPausedQueueTail) {
        pEndpoint->pRcvPausedQueueTail = pLastBuf;
        pEndpoint->pRcvPausedQueueHead = pFirstBuf;        
    } else {
            /* queue to the tail */
        pEndpoint->pRcvPausedQueueTail->next = pFirstBuf;
        pEndpoint->pRcvPausedQueueTail = pLastBuf;        
    }
    
}
#endif

#if 0
LOCAL HTC_BUFFER *HTC_DequeuePausedRecv(HTC_ENDPOINT *pEndpoint)
{
    HTC_BUFFER *pHead;
    HTC_BUFFER *pCur;
    
    if (pEndpoint->pRcvPausedQueueHead != NULL) {
            /* there is a message in the queue */ 
        pHead = pEndpoint->pRcvPausedQueueHead;   
        pCur = pHead;
        
        while (pCur != NULL) {
                /* check for end marker on this buffer */    
            if (pCur->htc_flags & HTC_FLAGS_RECV_END_MSG) {
                pCur->htc_flags &= ~HTC_FLAGS_RECV_END_MSG;
                    /* advance the head */
                pEndpoint->pRcvPausedQueueHead = pCur->next;
                
                if (NULL == pEndpoint->pRcvPausedQueueHead) {
                        /* list is now empty */
                    pEndpoint->pRcvPausedQueueTail = NULL;    
                }
                    /* cut this message out */
                pCur->next = NULL;
                break;
            }            
            pCur = pCur->next;
        }       
            /* we should always find complete messages with the marker present */
        //A_ASSERT(pCur != NULL);
        return pHead;
    } else {
        //A_ASSERT(pEndpoint->pRcvPausedQueueTail == NULL);
        return NULL;   
    }
}
#endif
    
LOCAL void AdjustCreditThreshold(HTC_ENDPOINT  *pEndpoint)
{

    A_INT16 creditsOutstanding = pEndpoint->CreditsToReturn + pEndpoint->CreditsConsumed;
        /* set the new threshold based on the number of credits that have been consumed
         * and which have not been returned by the app.
         * Note: it is okay for this threshold to be zero which indicates no threshold 
         * is in use */    
    switch (pEndpoint->ConnectionFlags & HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_MASK) {
        case HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_ONE_FOURTH :
            creditsOutstanding >>= 2;
            break;                    
        case HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_ONE_HALF :
            creditsOutstanding >>= 1;
            break;
        case HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_THREE_FOURTHS :  
            creditsOutstanding = (creditsOutstanding * 3) >> 2;                  
            break;
        /* default case is unity */    
    }
    
    pEndpoint->CreditReturnThreshhold = creditsOutstanding;
    
}

LOCAL void RedistributeCredit(adf_nbuf_t buf, int toPipeId)
{

}
            
/* callback from the mailbox hardware layer when a full message arrives */
LOCAL void HTCMsgRecvHandler(adf_nbuf_t hdr_buf, adf_nbuf_t buffer, void *context)
{
    A_UINT16       totsz;
    HTC_ENDPOINT  *pEndpoint;
    A_UINT32       eidMask;
    int            eid;    
    a_uint8_t      *anbdata;
    a_uint32_t     anblen;
    HTC_FRAME_HDR  *pHTCHdr;
    HTC_CONTEXT *pHTC = (HTC_CONTEXT *)context;
    adf_nbuf_t tmp_nbuf;
                
    if (hdr_buf == ADF_NBUF_NULL) {
        /* HTC hdr is not in the hdr_buf */
        tmp_nbuf = buffer;
    }
    else {
        tmp_nbuf = hdr_buf;
    }
                
    adf_nbuf_peek_header(tmp_nbuf, &anbdata, &anblen);        
    pHTCHdr = (HTC_FRAME_HDR *)anbdata; 
      
    totsz = adf_os_ntohs(pHTCHdr->PayloadLen); 
    
    //A_ASSERT(pHTCHdr->EndpointID < ENDPOINT_MAX);   
    eid = pHTCHdr->EndpointID; 
    
    pEndpoint = &pHTC->Endpoints[eid];
    eidMask = 1 << eid;

    if (pHTCHdr->Flags & HTC_FLAGS_CREDIT_REDISTRIBUTION) {
        /* The pipe id where the credit is redistributed to is carried in Control
        * Byte 0 */
        RedistributeCredit(tmp_nbuf, pHTCHdr->ControlBytes[0]);
        return;
    }

    if (pHTC->StateFlags & HTC_STATE_SETUP_COMPLETE) {
        /* after setup we keep track of credit consumption to allow us to
        * adjust thresholds to reduce credit dribbling */  
        pEndpoint->CreditsConsumed ++;
    }

    /* from the design document, we put the endpoint into a "host-needs-credit" state
    * when we receive a frame with the NEED_CREDIT_UPDATE flag set .
    * if the host received credits through an opportunistic path, then it can
    * issue a another frame with this bit cleared, this signals the target to clear
    * the "host-needs-credit" state */    
    if (pHTCHdr->Flags & HTC_FLAGS_NEED_CREDIT_UPDATE) {
        /* the host is running low (or is out) of credits on this
        * endpoint, update mask */
        pHTC->EpHostNeedsCreditMap |= eidMask; 
        /* check and set new threshold since host has reached a low credit situation */
        CHECK_AND_ADJUST_CREDIT_THRESHOLD(pEndpoint);                          
    } else {
        /* clear the flag */
        pHTC->EpHostNeedsCreditMap &= ~(eidMask);       
        pEndpoint->CreditReturnThreshhold = 0; 
    }

    /* Adjust the first buffer to point to the start of the actual 
       payload, the first buffer contains the header */
    adf_nbuf_pull_head(tmp_nbuf, HTC_HDR_LENGTH);
                    
    /* NOTE : This callback could re-queue the recv buffers within this calling context.
    *        The callback could also send a response message within the context of this callback
    *        as the result of parsing this message.  In either case, if there are
    *        pending credits and the host needs them, a credit report will be sent either through 
    *        the response message trailer or a NULL message through HTC_ReturnBuffers().
    */       
        
    //A_ASSERT(totsz <= pEndpoint->pService->MaxSvcMsgSize);       

#if 0    
    /* is this endpoint paused? */ 
    if (g_pHTC->EpRecvPausedMap & eidMask) {
        /* note that curr_buf is the last buffer */  
        /* mark the last buffer so that it indicates the end of this message */
        //curr_buf->htc_flags |= HTC_FLAGS_RECV_END_MSG;
        /* enqueue this message to our pause queues */
        //HTC_EnqueuePausedRecv(pEndpoint,bufinfo,curr_buf);
    } else {           
        /* pass the message to the service */
        pEndpoint->pService->ProcessRecvMsg(eid, buffer, pEndpoint->pService->ServiceCtx);
    }                           
#else
    pEndpoint->pService->ProcessRecvMsg(eid, hdr_buf, buffer, pEndpoint->pService->ServiceCtx);
#endif

    /* Calls to HTC_ReturnBuffers drives the endpoint credit reporting state machine. 
    * We do not want to delay credits for too long in the event that the application is 
    * holding onto buffers for excessive periods of time.  This gives us "some" better
    * opportunities to send up credits. */
    HTCCheckAndSendCreditReport(pHTC, eidMask, pEndpoint, eid); 
}
