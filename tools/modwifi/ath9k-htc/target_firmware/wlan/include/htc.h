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
#ifndef __HTC_H__
#define __HTC_H__

#ifndef ATH_TARGET
#endif

#define A_OFFSETOF(type,field) ((int)(&(((type *)NULL)->field)))

#define ASSEMBLE_UNALIGNED_UINT16(p,highbyte,lowbyte) \
        (((a_uint16_t)(((a_uint8_t *)(p))[(highbyte)])) << 8 | (a_uint16_t)(((a_uint8_t *)(p))[(lowbyte)]))
        
/* alignment independent macros (little-endian) to fetch UINT16s or UINT8s from a 
 * structure using only the type and field name.
 * Use these macros if there is the potential for unaligned buffer accesses. */
#define A_GET_UINT16_FIELD(p,type,field)			\
	ASSEMBLE_UNALIGNED_UINT16(p,				\
				  A_OFFSETOF(type,field) + 1,	\
				  A_OFFSETOF(type,field))

#define A_SET_UINT16_FIELD(p,type,field,value)				\
	{								\
		((a_uint8_t *)(p))[A_OFFSETOF(type,field)] = (a_uint8_t)((value) >> 8);	\
		((a_uint8_t *)(p))[A_OFFSETOF(type,field) + 1] = (a_uint8_t)(value); \
	}
  
#define A_GET_UINT8_FIELD(p,type,field) \
            ((a_uint8_t *)(p))[A_OFFSETOF(type,field)]
            
#define A_SET_UINT8_FIELD(p,type,field,value) \
    ((a_uint8_t *)(p))[A_OFFSETOF(type,field)] = (value)

/****** DANGER DANGER ***************
 * 
 *   The frame header length and message formats defined herein were
 *   selected to accommodate optimal alignment for target processing.  This reduces code
 *   size and improves performance.
 * 
 *   Any changes to the header length may alter the alignment and cause exceptions
 *   on the target. When adding to the message structures insure that fields are
 *   properly aligned.
 * 
 */

/* endpoint defines */
typedef enum
{
	ENDPOINT_UNUSED = -1,
	ENDPOINT0 = 0, /* this is reserved for the control endpoint */
	ENDPOINT1 = 1,  
	ENDPOINT2 = 2,   
	ENDPOINT3 = 3,
	ENDPOINT4,
	ENDPOINT5,
	ENDPOINT6,
	ENDPOINT7,
	ENDPOINT8,
	ENDPOINT_MAX = 22 /* maximum number of endpoints for this firmware build, max application
			     endpoints = (ENDPOINT_MAX - 1) */
} HTC_ENDPOINT_ID;

/* HTC frame header */
typedef PREPACK struct _HTC_FRAME_HDR{
        /* do not remove or re-arrange these fields, these are minimally required
         * to take advantage of 4-byte lookaheads in some hardware implementations */
	a_uint8_t   EndpointID;
	a_uint8_t   Flags;
	a_uint16_t  PayloadLen;       /* length of data (including trailer) that follows the header */
    
	/***** end of 4-byte lookahead ****/
    
	a_uint8_t   ControlBytes[4];
    
	/* message payload starts after the header */
    
} POSTPACK HTC_FRAME_HDR;

/* frame header flags */
#define HTC_FLAGS_NEED_CREDIT_UPDATE (1 << 0)
#define HTC_FLAGS_RECV_TRAILER       (1 << 1)
#define HTC_FLAGS_CREDIT_REDISTRIBUTION (1 << 2)

#define HTC_HDR_LENGTH  (sizeof(HTC_FRAME_HDR))
#define HTC_MAX_TRAILER_LENGTH   255
#define HTC_MAX_PAYLOAD_LENGTH   (2048 - sizeof(HTC_FRAME_HDR))

/* HTC control message IDs */
typedef enum {
	HTC_MSG_READY_ID = 1,
	HTC_MSG_CONNECT_SERVICE_ID = 2,
	HTC_MSG_CONNECT_SERVICE_RESPONSE_ID = 3,   
	HTC_MSG_SETUP_COMPLETE_ID = 4,
	HTC_MSG_CONFIG_PIPE_ID = 5,
	HTC_MSG_CONFIG_PIPE_RESPONSE_ID = 6,
} HTC_MSG_IDS;
 
#define HTC_MAX_CONTROL_MESSAGE_LENGTH  256
         
/* base message ID header */
typedef PREPACK struct {
	a_uint16_t MessageID;    
} POSTPACK HTC_UNKNOWN_MSG;
                                                     
/* HTC ready message
 * direction : target-to-host  */
typedef PREPACK struct {
	a_uint16_t  MessageID;    /* ID */
	a_uint16_t  CreditCount;  /* number of credits the target can offer */       
	a_uint16_t  CreditSize;   /* size of each credit */
	a_uint8_t   MaxEndpoints; /* maximum number of endpoints the target has resources for */
	a_uint8_t   _Pad1;
} POSTPACK HTC_READY_MSG;

#define HTC_SERVICE_META_DATA_MAX_LENGTH 128

/* connect service
 * direction : host-to-target */
typedef PREPACK struct {
	a_uint16_t  MessageID;
	a_uint16_t  ServiceID;           /* service ID of the service to connect to */       
	a_uint16_t  ConnectionFlags;     /* connection flags */
	a_uint8_t   DownLinkPipeID;
	a_uint8_t   UpLinkPipeID;

#define HTC_CONNECT_FLAGS_REDUCE_CREDIT_DRIBBLE (1 << 2)  /* reduce credit dribbling when 
                                                             the host needs credits */  
#define HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_MASK             (0x3)  
#define HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_ONE_FOURTH        0x0
#define HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_ONE_HALF          0x1
#define HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_THREE_FOURTHS     0x2
#define HTC_CONNECT_FLAGS_THRESHOLD_LEVEL_UNITY             0x3
                                                             
	a_uint8_t   ServiceMetaLength;   /* length of meta data that follows */
	a_uint8_t   _Pad1;
    
	/* service-specific meta data starts after the header */
    
} POSTPACK HTC_CONNECT_SERVICE_MSG;

/* connect response
 * direction : target-to-host */
typedef PREPACK struct {
	a_uint16_t  MessageID;
	a_uint16_t  ServiceID;            /* service ID that the connection request was made */
	a_uint8_t   Status;               /* service connection status */ 
	a_uint8_t   EndpointID;           /* assigned endpoint ID */
	a_uint16_t  MaxMsgSize;           /* maximum expected message size on this endpoint */
	a_uint8_t   ServiceMetaLength;    /* length of meta data that follows */
	a_uint8_t   _Pad1;               
    
	/* service-specific meta data starts after the header */
    
} POSTPACK HTC_CONNECT_SERVICE_RESPONSE_MSG;

typedef PREPACK struct {
	a_uint16_t  MessageID;
	/* currently, no other fields */
} POSTPACK HTC_SETUP_COMPLETE_MSG;

/* config pipe
 * direction : host-to-target */
typedef PREPACK struct {
	a_uint16_t  MessageID;
	a_uint8_t   PipeID;           /* Pipe ID of the service to connect to */       
	a_uint8_t   CreditCount;      /* CreditCount */                                                            
	//a_uint8_t   _Pad1;        
} POSTPACK HTC_CONFIG_PIPE_MSG;

/* config pipe
 * direction : host-to-target */
typedef PREPACK struct {
	a_uint16_t  MessageID;
	a_uint8_t   PipeID;           /* Pipe ID of the service to connect to */       
	a_uint8_t   Status;           /* status */                                                            
	//a_uint8_t   _Pad1;        
} POSTPACK HTC_CONFIG_PIPE_RESPONSE_MSG;

/* connect response status codes */
#define HTC_SERVICE_SUCCESS      0  /* success */
#define HTC_SERVICE_NOT_FOUND    1  /* service could not be found */
#define HTC_SERVICE_FAILED       2  /* specific service failed the connect */
#define HTC_SERVICE_NO_RESOURCES 3  /* no resources (i.e. no more endpoints) */  
#define HTC_SERVICE_NO_MORE_EP   4  /* specific service is not allowing any more 
                                       endpoints */

/* shihhung: config pipe response status code */
#define HTC_CONFIGPIPE_SUCCESS    0
#define HTC_CONFIGPIPE_NOSUCHPIPE 1
#define HTC_CONFIGPIPE_NORESOURCE 2

/* report record IDs */
typedef enum {
	HTC_RECORD_NULL  = 0,
	HTC_RECORD_CREDITS   = 1,
	HTC_RECORD_LOOKAHEAD = 2,   
} HTC_RPT_IDS;

typedef PREPACK struct {
	a_uint8_t RecordID;     /* Record ID */
	a_uint8_t Length;       /* Length of record */
} POSTPACK HTC_RECORD_HDR;

typedef PREPACK struct {
	a_uint8_t EndpointID;     /* Endpoint that owns these credits */
	a_uint8_t Credits;        /* credits to report since last report */
} POSTPACK HTC_CREDIT_REPORT;

typedef PREPACK struct {    
	a_uint8_t PreValid;         /* pre valid guard */
	a_uint8_t LookAhead[4];     /* 4 byte lookahead */
	a_uint8_t PostValid;        /* post valid guard */
    
	/* NOTE: the LookAhead array is guarded by a PreValid and Post Valid guard bytes.
	 * The PreValid bytes must equal the inverse of the PostValid byte */
    
} POSTPACK HTC_LOOKAHEAD_REPORT;

#ifndef ATH_TARGET
//#include "athendpack.h"
#endif

#endif /* __HTC_H__ */
