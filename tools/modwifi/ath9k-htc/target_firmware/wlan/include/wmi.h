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
 * This file contains the definitions of the WMI protocol specified in the
 * Wireless Module Interface (WMI).  It includes definitions of all the
 * commands and events. Commands are messages from the host to the WM.
 * Events and Replies are messages from the WM to the host.
 *
 * Ownership of correctness in regards to WMI commands
 * belongs to the host driver and the WM is not required to validate
 * parameters for value, proper range, or any other checking.
 *
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/wlan/include/wmi.h#6 $
 */

#ifndef _WMI_H_
#define _WMI_H_

#include "athdefs.h"

#ifdef __cplusplus
extern "C" {
#endif

#define HTC_PROTOCOL_VERSION    0x0002
#define HTC_PROTOCOL_REVISION   0x0000

#define WMI_PROTOCOL_VERSION    0x0002
#define WMI_PROTOCOL_REVISION   0x0000

#define ATH_MAC_LEN             6               /* length of mac in bytes */
#define WMI_CMD_MAX_LEN         100
#define WMI_CONTROL_MSG_MAX_LEN     256
#define WMI_OPT_CONTROL_MSG_MAX_LEN 1536
#define IS_ETHERTYPE(_typeOrLen)        ((_typeOrLen) >= 0x0600)
#define RFC1042OUI      {0x00, 0x00, 0x00}

#define IP_ETHERTYPE 0x0800

#define WMI_IMPLICIT_PSTREAM 0xFF
#define WMI_MAX_THINSTREAM 15

struct host_app_area_s {
    a_uint32_t wmi_protocol_ver;
};

/*
 * Data Path
 */
typedef PREPACK struct {
    a_uint8_t     dstMac[ATH_MAC_LEN];
    a_uint8_t     srcMac[ATH_MAC_LEN];
    a_uint16_t    typeOrLen;
} POSTPACK ATH_MAC_HDR;

typedef PREPACK struct {
    a_uint8_t     dsap;
    a_uint8_t     ssap;
    a_uint8_t     cntl;
    a_uint8_t     orgCode[3];
    a_uint16_t    etherType;
} POSTPACK ATH_LLC_SNAP_HDR;

typedef enum {
    DATA_MSGTYPE = 0x0,
    CNTL_MSGTYPE,
    SYNC_MSGTYPE,
    OPT_MSGTYPE,
} WMI_MSG_TYPE;


typedef PREPACK struct {
    a_int8_t      rssi;            
    a_uint8_t     info;            /* WMI_MSG_TYPE in lower 2 bits - b1b0 */
                                 /* UP in next 3 bits - b4b3b2 */
#define WMI_DATA_HDR_MSG_TYPE_MASK  0x03
#define WMI_DATA_HDR_MSG_TYPE_SHIFT 0
#define WMI_DATA_HDR_UP_MASK        0x07
#define WMI_DATA_HDR_UP_SHIFT       2   
#define WMI_DATA_HDR_IS_MSG_TYPE(h, t)  (((h)->info & (WMI_DATA_HDR_MSG_TYPE_MASK)) == (t))
} POSTPACK WMI_DATA_HDR;


#define WMI_DATA_HDR_SET_MSG_TYPE(h, t) (h)->info = (((h)->info & ~(WMI_DATA_HDR_MSG_TYPE_MASK << WMI_DATA_HDR_MSG_TYPE_SHIFT)) | (t << WMI_DATA_HDR_MSG_TYPE_SHIFT))
#define WMI_DATA_HDR_SET_UP(h, p) (h)->info = (((h)->info & ~(WMI_DATA_HDR_UP_MASK << WMI_DATA_HDR_UP_SHIFT)) | (p << WMI_DATA_HDR_UP_SHIFT))

/*
 * Control Path
 */
typedef PREPACK struct {
    a_uint16_t    commandId;
    a_uint16_t    seqNo;
} POSTPACK WMI_CMD_HDR;        /* used for commands and events */

/*
 * List of Commnands
 */
typedef enum {
    WMI_ECHO_CMDID           = 0x0001,
    WMI_ACCESS_MEMORY_CMDID,

    /* Commands to Target */
    WMI_GET_FW_VERSION,
    WMI_DISABLE_INTR_CMDID,
    WMI_ENABLE_INTR_CMDID,
    WMI_ATH_INIT_CMDID,
    WMI_ABORT_TXQ_CMDID,
    WMI_STOP_TX_DMA_CMDID,
    WMI_ABORT_TX_DMA_CMDID,
    WMI_DRAIN_TXQ_CMDID,
    WMI_DRAIN_TXQ_ALL_CMDID,
    WMI_START_RECV_CMDID,
    WMI_STOP_RECV_CMDID,
    WMI_FLUSH_RECV_CMDID,
    WMI_SET_MODE_CMDID,
    WMI_NODE_CREATE_CMDID,
    WMI_NODE_REMOVE_CMDID,
    WMI_VAP_REMOVE_CMDID,
    WMI_VAP_CREATE_CMDID,
    WMI_REG_READ_CMDID,
    WMI_REG_WRITE_CMDID,
    WMI_RC_STATE_CHANGE_CMDID,
    WMI_RC_RATE_UPDATE_CMDID,
    WMI_TARGET_IC_UPDATE_CMDID,
    WMI_TX_AGGR_ENABLE_CMDID,
    WMI_TGT_DETACH_CMDID,
    WMI_NODE_UPDATE_CMDID,
    WMI_INT_STATS_CMDID,
    WMI_TX_STATS_CMDID,
    WMI_RX_STATS_CMDID,
    WMI_BITRATE_MASK_CMDID,
    WMI_REG_RMW_CMDID,

    /** New commands */
    WMI_DEBUGMSG_CMDID = 0x0080,
    WMI_REACTIVEJAM_CMDID,
    WMI_FASTREPLY_CMDID,
    WMI_CONSTANTJAM_CMDID,
} WMI_COMMAND_ID;


/*
 * Frame Types
 */
typedef enum {
    WMI_FRAME_BEACON        =   0,
    WMI_FRAME_PROBE_REQ,
    WMI_FRAME_PROBE_RESP,
    WMI_FRAME_ASSOC_REQ,
    WMI_FRAME_ASSOC_RESP,
    WMI_NUM_MGMT_FRAME 
} WMI_MGMT_FRAME_TYPE;

/*
 * Connect Command
 */
typedef enum {
    INFRA_NETWORK       = 0x01,
    ADHOC_NETWORK       = 0x02,
    ADHOC_CREATOR       = 0x04,
    OPT_NETWORK         = 0x08,
} NETWORK_TYPE;

typedef enum {
    OPEN_AUTH           = 0x01,
    SHARED_AUTH         = 0x02,
    LEAP_AUTH           = 0x04,  /* different from IEEE_AUTH_MODE definitions */
} DOT11_AUTH_MODE;

typedef enum {
    NONE_AUTH           = 0x01, 
    WPA_AUTH            = 0x02,
    WPA_PSK_AUTH        = 0x03,
    WPA2_AUTH           = 0x04,
    WPA2_PSK_AUTH       = 0x05,
    WPA_AUTH_CCKM       = 0x06,
    WPA2_AUTH_CCKM      = 0x07,
} AUTH_MODE;

typedef enum {
    NONE_CRYPT          = 0x01,
    WEP_CRYPT           = 0x02,
    TKIP_CRYPT          = 0x03,
    AES_CRYPT           = 0x04,
} CRYPTO_TYPE;

#define WMI_MIN_CRYPTO_TYPE NONE_CRYPT
#define WMI_MAX_CRYPTO_TYPE (AES_CRYPT + 1)

#define WMI_MIN_KEY_INDEX   0
#define WMI_MAX_KEY_INDEX   3

#define WMI_MAX_KEY_LEN     32

#define WMI_MAX_SSID_LEN    32

typedef enum {
    CONNECT_ASSOC_POLICY_USER = 0x0001,
    CONNECT_SEND_REASSOC = 0x0002,
    CONNECT_IGNORE_WPAx_GROUP_CIPHER = 0x0004,
    CONNECT_PROFILE_MATCH_DONE = 0x0008,
    CONNECT_IGNORE_AAC_BEACON = 0x0010,
    CONNECT_CSA_FOLLOW_BSS = 0x0020,
} WMI_CONNECT_CTRL_FLAGS_BITS;

#define DEFAULT_CONNECT_CTRL_FLAGS    (CONNECT_CSA_FOLLOW_BSS)

/*
 * WMI_ECHO_CMDID
 */
#define WMI_ECHOCMD_MSG_MAX_LEN         53//64 - HTC_HDR_LENGTH + sizeof(WMI_CMD_HDR) - 1

typedef PREPACK struct {
    a_uint8_t     msgSize;
    a_uint8_t     msgData[1];
} POSTPACK WMI_ECHO_CMD;

/*
 * WMI_ACCESS_MEMORY_CMDID
 */
#define WMI_ACCESS_MEMORY_MAX_TUPLES    8

typedef PREPACK struct {
    a_uint16_t    addressL;
    a_uint16_t    addressH;
    a_uint16_t    valueL;
    a_uint16_t    valueH;
} POSTPACK WMI_AVT;

typedef PREPACK struct {
    a_uint16_t     tupleNumL;
    a_uint16_t     tupleNumH;
    WMI_AVT      avt[1];
} POSTPACK WMI_ACCESS_MEMORY_CMD;

/**
 * WMI_DEBUGMSG_CMDID
 */

typedef PREPACK struct wmi_dmesg_cmd {
	a_uint16_t offset;
} POSTPACK WMI_DEBUGMSG_CMD;

typedef PREPACK struct {
	/** Length of zero signifies that no more data is available */
	a_uint8_t length;
	/** Debug message(s) **/
	a_uint8_t buffer[40];
} POSTPACK WMI_DEBUGMSG_RESP;

/*
 * WMI_REACTIVEJAM_CMDID
 */
typedef PREPACK struct {
	/** target BSSID mac address */
	a_uint8_t bssid[6];
	/** duration in miliseconds */
	a_uint32_t mduration;
} POSTPACK WMI_REACTIVEJAM_CMD;

/*
 * WMI_CONSTANTJAM_CMDID
 */

typedef PREPACK struct {
	/** A value from CONSTJAM_REQUEST to denote the request */
	a_uint8_t request;
	/** Set to 1 to disable CS and inter-frame-timeouts */
	a_uint8_t conf_radio;
	/** Length of the packet which is continuously transmitted */
	a_uint16_t len;
} POSTPACK WMI_CONSTANTJAM_CMD;

typedef PREPACK struct {
	/** Is 1 when jammer is running, 0 otherwise */
	a_uint8_t status;
} POSTPACK WMI_CONSTANTJAM_RESP;

enum CONSTJAM_REQUEST {
	CONSTJAM_START,
	CONSTJAM_STOP,
	CONSTJAM_STATUS
};

/*
 * WMI_FASTREPLY_CMDID
 */
typedef PREPACK struct {
	a_uint8_t type;
	union {
		// transmit response packet in multiple commands
		struct {
			a_uint8_t length;
			a_uint8_t offset;
			a_uint8_t datalen;
			a_uint8_t data[40];
		} pkt;
		// command to start monitoring
		struct {
			a_uint32_t mduration;
			a_uint8_t source[6];
			a_uint8_t jam;
		} start;
	};
} POSTPACK WMI_FASTREPLY_CMD;

enum FASTREPLY_TYPE {
	FASTREPLY_PACKET,
	FASTREPLY_START
};

/*
 * List of Events (target to host)
 */
typedef enum {
    WMI_TGT_RDY_EVENTID           = 0x1001,
    WMI_SWBA_EVENTID,
    WMI_FATAL_EVENTID,
    WMI_TXTO_EVENTID,
    WMI_BMISS_EVENTID,
    WMI_DELBA_EVENTID,
    WMI_TXSTATUS_EVENTID
} WMI_EVENT_ID;

typedef PREPACK struct {
	a_uint64_t tsf;
	a_uint8_t beaconPendingCount;
} POSTPACK WMI_SWBA_EVENT;

typedef PREPACK struct {
	a_uint8_t    cookie;
	a_uint8_t    ts_rate;
	a_uint8_t    ts_flags;
} POSTPACK __WMI_TXSTATUS_EVENT;

#define HTC_MAX_TX_STATUS 12

typedef PREPACK struct {
	a_uint8_t cnt;
	__WMI_TXSTATUS_EVENT txstatus[HTC_MAX_TX_STATUS];
} POSTPACK WMI_TXSTATUS_EVENT;

struct register_rmw {
	a_uint32_t reg;
	a_uint32_t set;
	a_uint32_t clr;
};

#ifndef ATH_TARGET
//#include "athendpack.h"
#endif

#ifdef __cplusplus
}
#endif

#endif /* _WMI_H_ */
