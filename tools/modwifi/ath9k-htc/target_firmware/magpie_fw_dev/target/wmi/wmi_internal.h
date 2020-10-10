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
 * @Abstract: internal data and structure definitions for WMI service
 * 
 * @Notes: 
 */

#ifndef WMI_INTERNAL_H_
#define WMI_INTERNAL_H_

#define WMI_CMD_ALIGNMENT_SIZE  128

#ifdef WMI_DEBUG

/* WMI debug log definitions */

#define WMI_DBG0_LOG(debugid) \
    DBGLOG_ARG0_RECORD(DBGLOG_HEADER_UPPER_HALF(debugid, \
                       DBGLOG_MODULEID_WMI, 0))

#define WMI_DBG1_LOG(debugid, arg1) \
    DBGLOG_ARG1_RECORD(DBGLOG_HEADER_UPPER_HALF(debugid, \
                       DBGLOG_MODULEID_WMI, 1), arg1)

#define WMI_DBG2_LOG(debugid, arg1, arg2) \
    DBGLOG_ARG2_RECORD(DBGLOG_HEADER_UPPER_HALF(debugid, \
                       DBGLOG_MODULEID_WMI, 2), arg1, arg2)

#else
#define WMI_DBG0_LOG(debugid)
#define WMI_DBG1_LOG(debugid, arg1)
#define WMI_DBG2_LOG(debugid, arg1, arg2)
#endif /* WMI_DEBUG */

#define EVT_PKT_IN_USE        (1 << 0)
#define EVT_PKT_IS_FREE(e)    !((e)->Flags & EVT_PKT_IN_USE)  
#define EVT_MARK_FREE(e)      (e)->Flags &= ~EVT_PKT_IN_USE;
#define EVT_MARK_INUSE(e)     (e)->Flags |= EVT_PKT_IN_USE
#define IS_EVT_CLASS_BUFFERED(ec)   ((ec) != WMI_EVT_CLASS_DIRECT_BUFFER)

typedef struct _WMI_POOL_STATE {
	int     MaxAllocation;      /* maximum allocations allowed for this pool */
	int     CurrentAllocation;  /* current allocations outstanding */
} WMI_POOL_STATE; 

typedef struct _WMI_SVC_CONTEXT {
	htc_handle_t         HtcHandle;
	pool_handle_t        PoolHandle;    
	int                  PendingEvents;                      /* no. of pending events */
	HTC_SERVICE          WMIControlService;                  /* registered control service */
	HTC_ENDPOINT_ID      ControlEp;                          /* endpoint assigned to us */
	WMI_DISPATCH_TABLE  *pDispatchHead;                      /* dispatch list head ptr  */
	WMI_DISPATCH_TABLE  *pDispatchTail;                      /* dispatch list tail ptr */   

	// Left a door for extension the structure
	void *pReserved;
} WMI_SVC_CONTEXT;

#endif /*WMI_INTERNAL_H_*/
