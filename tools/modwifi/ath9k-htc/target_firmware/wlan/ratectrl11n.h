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

#ifndef _RATECTRL11N_H_
#define _RATECTRL11N_H_

/* HT 20/40 rates. If 20 bit is enabled then that rate is
 * used only in 20 mode. If both 20/40 bits are enabled
 * then that rate can be used for both 20 and 40 mode */

#define TRUE_20	 	0x2	
#define TRUE_40 	0x4	
#define TRUE_2040	(TRUE_20|TRUE_40)
#define TRUE_ALL_11N	(TRUE_2040|TRUE)

enum {
	WLAN_RC_DS  = 0x01,
	WLAN_RC_40  = 0x02,
	WLAN_RC_SGI = 0x04,
	WLAN_RC_HT  = 0x08,
};

typedef enum {
	WLAN_RC_LEGACY      = 0,
	WLAN_RC_HT_LNPHY    = 1,
	WLAN_RC_HT_PLPHY    = 2,
	WLAN_RC_MAX         = 3
} WLAN_RC_VERS;

#define WLAN_RC_PHY_DS(_phy)   ((_phy == WLAN_RC_PHY_HT_20_DS)		\
                                || (_phy == WLAN_RC_PHY_HT_40_DS)	\
                                || (_phy == WLAN_RC_PHY_HT_20_DS_HGI)	\
                                || (_phy == WLAN_RC_PHY_HT_40_DS_HGI))   
#define WLAN_RC_PHY_40(_phy)   ((_phy == WLAN_RC_PHY_HT_40_SS)		\
                                || (_phy == WLAN_RC_PHY_HT_40_DS)	\
                                || (_phy == WLAN_RC_PHY_HT_40_SS_HGI)	\
                                || (_phy == WLAN_RC_PHY_HT_40_DS_HGI))   
#define WLAN_RC_PHY_20(_phy)   ((_phy == WLAN_RC_PHY_HT_20_SS)		\
                                || (_phy == WLAN_RC_PHY_HT_20_DS)	\
                                || (_phy == WLAN_RC_PHY_HT_20_SS_HGI)	\
                                || (_phy == WLAN_RC_PHY_HT_20_DS_HGI))   
#define WLAN_RC_PHY_SGI(_phy)  ((_phy == WLAN_RC_PHY_HT_20_SS_HGI)      \
                                || (_phy == WLAN_RC_PHY_HT_20_DS_HGI)   \
                                || (_phy == WLAN_RC_PHY_HT_40_SS_HGI)   \
                                || (_phy == WLAN_RC_PHY_HT_40_DS_HGI))   

#define WLAN_RC_PHY_HT(_phy)    (_phy >= WLAN_RC_PHY_HT_20_SS)

/* Returns the capflag mode */

#define WLAN_RC_CAP_MODE(capflag) (((capflag & WLAN_RC_HT_FLAG)?	\
				    (capflag & WLAN_RC_40_FLAG)?TRUE_40:TRUE_20: \
				    TRUE))

/* Return TRUE if flag supports HT20 && client supports HT20 or
 * return TRUE if flag supports HT40 && client supports HT40.
 * This is used becos some rates overlap between HT20/HT40.
 */

#define WLAN_RC_PHY_HT_VALID(flag, capflag) (((flag & TRUE_20) && !(capflag \
				& WLAN_RC_40_FLAG)) || ((flag & TRUE_40) && \
				  (capflag & WLAN_RC_40_FLAG)))

#define WLAN_RC_DS_FLAG         (0x01)
#define WLAN_RC_40_FLAG         (0x02)
#define WLAN_RC_HT40_SGI_FLAG   (0x04)
#define WLAN_RC_HT_FLAG         (0x08)
#define WLAN_RC_STBC_FLAG       (0x30)  /* 2 bits */
#define WLAN_RC_STBC_FLAG_S     (   4)
#define WLAN_RC_WEP_TKIP_FLAG   (0x100)

/* Index into the rate table */
#define INIT_RATE_MAX_20	23		
#define INIT_RATE_MAX_40	40

/*
 * Rate Table structure for various modes - 'b', 'a', 'g', 'xr';
 * order of fields in info structure is important because hardcoded
 * structures are initialized within the hal for these
 */

#ifndef MAGPIE_MERLIN // K2
#define RATE_TABLE_11N_SIZE             54
#else
#define RATE_TABLE_11N_SIZE             64
#endif

#define MAX_SUPPORTED_MCS 	    128

typedef struct regDataLenTable {
	A_UINT8     numEntries;
	A_UINT16    frameLenRateIndex[RATE_TABLE_11N_SIZE];
} REG_DATALEN_TABLE;

typedef struct {
	A_BOOL    valid;            /* Valid for use in rate control */
	A_BOOL    validSingleStream;/* Valid for use in rate control for single stream operation */
#ifdef MAGPIE_MERLIN
	A_BOOL    validSTBC;        /* Valid for use in rate control for single stream operation */
#endif    
	WLAN_PHY  phy;              /* CCK/OFDM/TURBO/XR */
	A_UINT32  rateKbps;         /* Rate in Kbits per second */
	A_UINT32  userRateKbps;     /* User rate in KBits per second */
	A_UINT8   rateCode;         /* rate that goes into hw descriptors */
	A_UINT8   shortPreamble;    /* Mask for enabling short preamble in rate code for CCK */
	A_UINT8   dot11Rate;        /* Value that goes into supported rates info element of MLME */
	A_UINT8   controlRate;      /* Index of next lower basic rate, used for duration computation */
	A_RSSI    rssiAckValidMin;  /* Rate control related information */
	A_RSSI    rssiAckDeltaMin;  /* Rate control related information */
	A_UINT8   baseIndex;        /* base rate index */
	A_UINT8   cw40Index;        /* 40cap rate index */
	A_UINT8   sgiIndex;         /* shortgi rate index */
	A_UINT8   htIndex;          /* shortgi rate index */
	A_UINT8   txChainMask_2ch;  /* transmit chain mask */
	A_UINT8   txChainMask_3ch;  /* transmit chain mask */
	A_UINT32  max4msframelen;   /* Maximum frame length(bytes) for 4ms tx duration */
	A_BOOL    uapsdvalid;       /* Valid for UAPSD nodes */
} rc11n_info_t;

typedef struct {
	A_UINT8          rateCount;
	A_UINT8          probeInterval;        /* interval for ratectrl to probe for other rates */
	A_UINT8          rssiReduceInterval;   /* interval for ratectrl to reduce RSSI */
	A_UINT8          initialRateMax;   /* the initial rateMax value used in rcSibUpdate() */
	rc11n_info_t     info[];
} RATE_TABLE_11N;

/*
 * Sets rate control so frames will be aggregated in an A-MPDU. This means
 * using a HT rate. We pick the lowest one for reliability.
 */
void rcForceAggrRate(struct ath_softc_tgt *sc,
		     struct ath_node_target *an,
		     struct ath_rc_series series[]);

/*
 * Determines and returns the new Tx rate index.
 */ 
void rcRateFind_11n(struct ath_softc_tgt *sc,
		    struct ath_node_target *an,
		    int numTries,
		    int numRates,
		    int stepDnInc,
		    unsigned int rcflag,
		    struct ath_rc_series series[],
		    int *isProbe);

/*
 * This routine is called by the Tx interrupt service routine to give
 * the status of previous frames.
 */
void rcUpdate_11n(struct ath_softc_tgt *sc,
		  struct ath_node_target *an,
		  A_UINT8 curTxAnt,
		  int finalTSIdx,
		  int Xretries,
		  struct ath_rc_series rcs[],
		  int nFrames,
		  int nBad,
		  int sh_lo_retry);

void ath_tx_status_update_rate(struct ath_softc_tgt *sc,
			       struct ath_rc_series rcs[],
			       int series,
			       WMI_TXSTATUS_EVENT *txs);

#endif /* _RATECTRL11N_H_ */
