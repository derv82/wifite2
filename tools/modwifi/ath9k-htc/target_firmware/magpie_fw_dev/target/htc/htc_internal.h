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
 * @Abstract: internal data and structure definitions for HTC
 * 
 * @Notes: 
 */

#ifndef HTC_INTERNAL_H_
#define HTC_INTERNAL_H_

/* minimum buffer size to hold up to 8 endpoint reports, lookahead and the HTC header */
#define MIN_BUF_SIZE_FOR_RPTS (A_ROUND_UP((sizeof(HTC_LOOKAHEAD_REPORT) +              \
                                          (sizeof(HTC_CREDIT_REPORT)) * 8 +            \
                                          (sizeof(HTC_RECORD_HDR)) * 2  ) +            \
                                          HTC_HDR_LENGTH,                              \
                                          sizeof(A_UINT32)))
/* minimum allocation for a credit message */                                   
#define MIN_CREDIT_BUFFER_ALLOC_SIZE     (MIN_BUF_SIZE_FOR_RPTS)

/* max ctrl buffers size for a setup message */
#define MAX_HTC_SETUP_MSG_SIZE           64            /* The max size of USB command/event pipe is 64 bytes */

/* check size for trailer space */
#define HTC_CTRL_BUFFER_CHECK_SIZE       (MIN_BUF_SIZE_FOR_RPTS - HTC_HDR_LENGTH)

#define HTC_DEFAULT_NUM_CTRL_BUFFERS              6

#define HTC_DEFAULT_MAX_EP_PENDING_CREDIT_REPORTS 3  /* an EP should not have more than this many outstanding reports */

#define HTC_FLAGS_CRPT_EP_MASK      0x1F     /* if the message is a credit report this is the endpoint 
                                                that issued it */

#define HTC_FLAGS_CREDIT_RPT       (1 << 5)  /* the buffer was a credit report */
#define HTC_FLAGS_BUF_HDR          (1 << 6)  /* the buffer was manipulated and a header added */
#define HTC_FLAGS_RECV_END_MSG     (1 << 7)  /* this buffer is the last buffer for the recev
                                                message (used for recv pause logic) */     
                                                                                                                              
#define HTC_MAILBOX                 0        /* we use mailbox 0 for all communications */
#define HTC_ANY_ENDPOINT_MASK       0xFFFFFFFF
#define HTC_LOOKAHEAD_POST_VALID    0x55
#define HTC_LOOKAHEAD_PRE_VALID     0xAA
#define MAX_HTC_CREDITS             255

typedef struct _HTC_ENDPOINT {
	A_INT16       CreditsToReturn;       /* credits that are ready to be returned to the host */
	HTC_SERVICE   *pService;             /* service that is bound to this endpoint */
#ifdef HTC_PAUSE_RESUME_REF_COUNTING 
	int           PauseRefCount;         /* reference count */
#endif
	A_INT16       CreditReturnThreshhold;   /* threshold before credits are returned via NULL pkts,
						   this reduces dribbling effect */    
	A_INT16       CreditsConsumed;          /* number of credits consumed (outstanding) on the endpoint */  
	A_UINT16      ConnectionFlags;          /* HTC connection flags */          
	int           PendingCreditReports;     /* no. of pending credit reports issued by this endpoint */    
	A_UINT8       DownLinkPipeID;           /* The pipe ID to be use for the direction: target -> host */
	A_UINT8       UpLinkPipeID;             /* The pipe ID to be use for the direction: host   -> target */
} HTC_ENDPOINT;

typedef struct _HTC_CONTEXT {
	adf_os_handle_t OSHandle;
	HTC_ENDPOINT    Endpoints[ENDPOINT_MAX];  /* endpoint state structs */
	A_UINT32        EpHostNeedsCreditMap;     /* credit update bit map for all EPs */
	A_UINT32        EpCreditPendingMap;       /* credits pending bit map for all EPs */
	A_UINT32        EpRecvPausedMap;          /* recv pause state bit map for all EPs */
	HTC_ENDPOINT_ID CurrentEpIndex;           /* current unused endpoint index */
	HTC_SERVICE     HTCControlService;        /* the pseudo service that handles EP0 traffic */
	HTC_SERVICE     *pServiceList;            /* the service list */
	int             RecvBufferSize;           /* the length of each recv buffer that HTC is given */
	A_UINT32        StateFlags;               /* state flags */
	HTC_SETUP_COMPLETE_CB SetupCompleteCb;    /* caller supplied setup completion routine */
	int             TotalCredits;             /* total credits in system */
	int             TotalCreditsAssigned;
	int             NumBuffersForCreditRpts;      /* number of control buffers for credit reports */
	int             CtrlBufferAllocSize;          /* length of allocation */
	A_UINT8         *pCtrlBuffer;                 /* control buffer to be carved up for messages */
	int             MaxEpPendingCreditRpts;       /* maximum number of pending credit reports that any 1 EP can have */
	hif_handle_t    hifHandle;
	pool_handle_t   PoolHandle;

	// Left a door for extension the structure
	void *pReserved;      
} HTC_CONTEXT;

#define HTC_STATE_SETUP_COMPLETE    (1 << 0)  /* HTC host-target setup is complete */
#define HTC_SEND_CREDIT_UPDATE_SOON (1 << 1)  /* Credit update message needs to be sent */
#define HTC_STATE_BUFF_REALLOC      (1 << 2)  /* buffers have been reallocated for credit messages */

#endif /*HTC_INTERNAL_H_*/
