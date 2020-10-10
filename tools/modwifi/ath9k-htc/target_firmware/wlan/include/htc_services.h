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
#ifndef __HTC_SERVICES_H__
#define __HTC_SERVICES_H__

/* Current service IDs */

typedef enum {
	RSVD_SERVICE_GROUP  = 0,
	WMI_SERVICE_GROUP   = 1, 
    
	HTC_TEST_GROUP = 254,
	HTC_SERVICE_GROUP_LAST = 255
} HTC_SERVICE_GROUP_IDS;

#define MAKE_SERVICE_ID(group,index) \
            (int)(((int)group << 8) | (int)(index))

/* NOTE: service ID of 0x0000 is reserved and should never be used */
#define HTC_CTRL_RSVD_SVC MAKE_SERVICE_ID(RSVD_SERVICE_GROUP,1)
#define HTC_LOOPBACK_RSVD_SVC MAKE_SERVICE_ID(RSVD_SERVICE_GROUP,2)
#define WMI_CONTROL_SVC   MAKE_SERVICE_ID(WMI_SERVICE_GROUP,0)

#define WMI_BEACON_SVC	  MAKE_SERVICE_ID(WMI_SERVICE_GROUP,1) 
#define WMI_CAB_SVC	  MAKE_SERVICE_ID(WMI_SERVICE_GROUP,2) 

#define WMI_UAPSD_SVC	  MAKE_SERVICE_ID(WMI_SERVICE_GROUP,3)
#define WMI_MGMT_SVC	  MAKE_SERVICE_ID(WMI_SERVICE_GROUP,4)

#define WMI_DATA_VO_SVC   MAKE_SERVICE_ID(WMI_SERVICE_GROUP,5)
#define WMI_DATA_VI_SVC   MAKE_SERVICE_ID(WMI_SERVICE_GROUP,6)

#define WMI_DATA_BE_SVC   MAKE_SERVICE_ID(WMI_SERVICE_GROUP,7)
#define WMI_DATA_BK_SVC   MAKE_SERVICE_ID(WMI_SERVICE_GROUP,8)

/* raw stream service (i.e. flash, tcmd, calibration apps) */
#define HTC_RAW_STREAMS_SVC MAKE_SERVICE_ID(HTC_TEST_GROUP,0)

#endif /*HTC_SERVICES_H_*/
