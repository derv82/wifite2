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

#ifndef _RATECTRL_H_
#define _RATECTRL_H_

#include <adf_os_types.h>
#include <adf_os_dma.h>
#include <adf_os_timer.h>
#include <adf_os_lock.h>
#include <adf_os_io.h>
#include <adf_os_mem.h>
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>
#include <adf_net_types.h>
#include <adf_net_wcmd.h>

#include <ieee80211_var.h>

#include "if_athrate.h"
#include "if_athvar.h"

#define FALSE   0
#define TRUE    1

typedef int8_t          A_RSSI;
typedef int32_t         A_RSSI32;
typedef u_int8_t        WLAN_PHY;

#ifndef INLINE
#define INLINE          __inline
#endif

#ifndef A_MIN
#define A_MIN(a,b)      ((a)<(b)?(a):(b))
#endif

#ifndef A_MAX
#define A_MAX(a,b)      ((a)>(b)?(a):(b))
#endif

/*
 * Use the hal os glue code to get ms time; we supply
 * a null arg because we know it's not needed.
 */
#define A_MS_TICKGET()  OS_GETUPTIME(NULL)

#define WLAN_PHY_OFDM   IEEE80211_T_OFDM
#define WLAN_PHY_TURBO  IEEE80211_T_TURBO
#define WLAN_PHY_CCK    IEEE80211_T_CCK
#define WLAN_PHY_XR     (IEEE80211_T_TURBO+1)

enum {
	WLAN_RC_PHY_CCK,
	WLAN_RC_PHY_OFDM,
	WLAN_RC_PHY_TURBO,
	WLAN_RC_PHY_XR,
	WLAN_RC_PHY_HT_20_SS,
	WLAN_RC_PHY_HT_20_DS,
	WLAN_RC_PHY_HT_40_SS,
	WLAN_RC_PHY_HT_40_DS,
	WLAN_RC_PHY_HT_20_SS_HGI,
	WLAN_RC_PHY_HT_20_DS_HGI,
	WLAN_RC_PHY_HT_40_SS_HGI,
	WLAN_RC_PHY_HT_40_DS_HGI,
	WLAN_RC_PHY_MAX
};

#define IS_CHAN_TURBO(_c)   (((_c)->channelFlags & CHANNEL_TURBO) != 0)
#define IS_CHAN_2GHZ(_c)    (((_c)->channelFlags & CHANNEL_2GHZ) != 0)

#define PKTLOG_RATE_CTL_FIND(_sc, log_data, flags)   ath_log_rcfind(_sc, log_data, flags);
#define PKTLOG_RATE_CTL_UPDATE(_sc, log_data, flags) ath_log_rcupdate(_sc, log_data, flags);
#define ASSERT(condition)

#define WIRELESS_MODE_11NA      IEEE80211_MODE_11NA
#define WIRELESS_MODE_11NG      IEEE80211_MODE_11NG
#define WIRELESS_MODE_MAX       IEEE80211_MODE_MAX

#define RX_FLIP_THRESHOLD       3       /* XXX */

#ifdef MAGPIE_MERLIN  
#define MAX_TX_RATE_TBL         46
#else
#define MAX_TX_RATE_TBL         54//46
#endif

/*
 * State structures for new rate adaptation code
 *
 * NOTE: Modifying these structures will impact
 * the Perl script that parses packet logging data.
 * See the packet logging module for more information.
 */
typedef struct TxRateCrtlState_s {
	A_UINT8 per;                /* recent estimate of packet error rate (%) */
} TxRateCtrlState;

typedef struct TxRateCtrl_s {
	TxRateCtrlState state[MAX_TX_RATE_TBL];                         /* state for each rate */
	A_UINT8  rateTableSize;       /* rate table size */
	A_UINT8  probeRate;           /* rate we are probing at */
	A_UINT32 rssiTime;            /* msec timestamp for last ack rssi */
	A_UINT32 probeTime;           /* msec timestamp for last probe */
	A_UINT8  hwMaxRetryPktCnt;    /* num packets since we got HW max retry error */
	A_UINT8  maxValidRate;       /* maximum number of valid rate */
	A_UINT8  validRateIndex[MAX_TX_RATE_TBL];    /* rc Index is valid for this Sib */
	A_UINT32 perDownTime;         /* msec timstamp for last PER down step */
	A_UINT8  rcPhyMode;
	A_UINT8  rateMaxPhy;          /* Phy index for the max rate */
} TX_RATE_CTRL;

typedef struct phy_rate_ctrl {
	/* 11n state */
	A_UINT8  validPhyRateCount[WLAN_RC_PHY_MAX]; /* valid rate count */
	A_UINT8  validPhyRateIndex[WLAN_RC_PHY_MAX][MAX_TX_RATE_TBL]; /* index */    
}PHY_STATE_CTRL;

/* per-node state */
struct atheros_node {
	TX_RATE_CTRL txRateCtrl;    /* rate control state proper */
	A_UINT32 lastRateKbps;      /* last rate in Kb/s */
	A_UINT8 singleStream    :1,   /* When TRUE, only single stream Tx possible */
		stbc            :2;   /* Rx stbc capability */

};

#define ATH_NODE_ATHEROS(an)    (an->an_rcnode)

/*
 * Rate Table structure for various modes - 'b', 'a', 'g', 'xr';
 * order of fields in info structure is important because hardcoded
 * structures are initialized within the hal for these
 */

typedef struct {
	int         rateCount;
	A_UINT8     rateCodeToIndex[RATE_TABLE_SIZE]; /* backward mapping */
	struct {
		int    valid;            /* Valid for use in rate control */
		WLAN_PHY  phy;              /* CCK/OFDM/TURBO/XR */
		A_UINT16  rateKbps;         /* Rate in Kbits per second */
		A_UINT16  userRateKbps;     /* User rate in KBits per second */
		A_UINT8   rateCode;         /* rate that goes into hw descriptors */
		A_UINT8   shortPreamble;    /* Mask for enabling short preamble in rate code for CCK */
		A_UINT8   dot11Rate;        /* Value that goes into supported rates info element of MLME */
		A_UINT8   controlRate;      /* Index of next lower basic rate, used for duration computation */
		A_RSSI    rssiAckValidMin;  /* Rate control related information */
		A_RSSI    rssiAckDeltaMin;  /* Rate control related information */
		A_UINT16  lpAckDuration;    /* long preamble ACK duration */
		A_UINT16  spAckDuration;    /* short preamble ACK duration*/
		A_UINT32  max4msFrameLen;   /* Maximum frame length(bytes) for 4ms tx duration */
		struct {
			A_UINT32  word4Retries;
			A_UINT32  word5Rates;
		} normalSched;
		struct {
			A_UINT32  word4Retries;
			A_UINT32  word5Rates;
		} shortSched;
		struct {
			A_UINT32  word4Retries;
			A_UINT32  word5Rates;
		} probeSched;
		struct {
			A_UINT32  word4Retries;
			A_UINT32  word5Rates;
		} probeShortSched;
		struct {
			A_UINT32  word4Retries;
			A_UINT32  word5Rates;
		} uapsd_normalSched;
		struct {
			A_UINT32  word4Retries;
			A_UINT32  word5Rates;
		} uapsd_shortSched;
#ifdef ATH_REMOVE_5G_RATE_TABLE
#ifdef ATH_REMOVE_TURBO_RATE_TABLE
#ifdef ATH_REMOVE_XR_RATE_TABLE
	} info[12];
#else
} info[32];
#endif
#else
} info[32];
#endif
#else
} info[32];
#endif
A_UINT32    probeInterval;        /* interval for ratectrl to probe for
				     other rates */
A_UINT32    rssiReduceInterval;   /* interval for ratectrl to reduce RSSI */
A_UINT8     regularToTurboThresh; /* upperbound on regular (11a or 11g)
				     mode's rate before switching to turbo*/
A_UINT8     turboToRegularThresh; /* lowerbound on turbo mode's rate before
				     switching to regular */
A_UINT8     pktCountThresh;       /* mode switch recommendation criterion:
				     number of consecutive packets sent at
				     rate beyond the rate threshold */
A_UINT8     initialRateMax;       /* the initial rateMax value used in
				     rcSibUpdate() */
A_UINT8     numTurboRates;        /* number of Turbo rates in the rateTable */
A_UINT8     xrToRegularThresh;    /* threshold to switch to Normal mode */
} RATE_TABLE;

/* per-device state */
struct atheros_softc {
        struct ath_ratectrl     arc;
        /* phy tables that contain rate control data */
        void                    *hwRateTable[WIRELESS_MODE_MAX];
	A_UINT32                tx_chainmask;
	A_UINT32                currentTxRateKbps;
	A_UINT32                currentTxRateIndex;
};

/*
 *  Update the SIB's rate control information
 *
 *  This should be called when the supported rates change
 *  (e.g. SME operation, wireless mode change)
 *
 *  It will determine which rates are valid for use.
 */
void
rcSibUpdate(struct ath_softc_tgt *sc,
	    struct ath_node_target *an,
	    A_BOOL keepState,
	    struct ieee80211_rateset *pRateSet);

/*
 *  This routine is called to initialize the rate control parameters
 *  in the SIB. It is called initially during system initialization
 *  or when a station is associated with the AP.
 */
void rcSibInit(struct ath_softc_tgt *, struct ath_node_target *);

/*
 * Determines and returns the new Tx rate index.
 */ 
A_UINT16 rcRateFind(struct ath_softc_tgt *, struct atheros_node *,
		    A_UINT32 frameLen,const  RATE_TABLE *pRateTable);

struct fusion_rate_info {
	A_UINT32 txrate;
	A_UINT8 rssi;
	A_UINT8 per;
};

void ar5416AttachRateTables(struct atheros_softc *sc);

#endif /* _RATECTRL_H_ */
