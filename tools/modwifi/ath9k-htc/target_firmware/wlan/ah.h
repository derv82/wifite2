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

#ifndef _ATH_AH_H_
#define _ATH_AH_H_

#include <ah_osdep.h>
#include <ah_desc.h>

#ifndef __ahdecl
#define __ahdecl
#endif

#define AR5416_DEVID_PCIE   0x0024  /* AR5416 PCI-E (XB) (Owl) */
#define HAL_RATE_TABLE_SIZE 33

typedef enum {
	HAL_OK           = 0,    /* No error */
	HAL_ENXIO        = 1,    /* No hardware present */
	HAL_ENOMEM       = 2,    /* Memory allocation failed */
	HAL_EIO          = 3,    /* Hardware didn't respond as expected */
	HAL_EEMAGIC      = 4,    /* EEPROM magic number invalid */
	HAL_EEVERSION    = 5,    /* EEPROM version invalid */
	HAL_EELOCKED     = 6,    /* EEPROM unreadable */
	HAL_EEBADSUM     = 7,    /* EEPROM checksum invalid */
	HAL_EEREAD       = 8,    /* EEPROM read problem */
	HAL_EEBADMAC     = 9,    /* EEPROM mac address invalid */
	HAL_EESIZE       = 10,   /* EEPROM size not supported */
	HAL_EEWRITE      = 11,   /* Attempt to change write-locked EEPROM */
	HAL_EINVAL       = 12,   /* Invalid parameter to function */
	HAL_ENOTSUPP     = 13,   /* Hardware revision not supported */
	HAL_ESELFTEST    = 14,   /* Hardware self-test failed */
	HAL_EINPROGRESS  = 15,   /* Operation incomplete */
	HAL_FULL_RESET   = 16,   /* Full reset done */
} HAL_STATUS;

typedef enum {
	AH_FALSE = 0,
	AH_TRUE  = 1,
} HAL_BOOL;

typedef enum {
	HAL_CAP_VEOL        = 0,
	HAL_CAP_BSSIDMASK   = 1,
	HAL_CAP_TSF_ADJUST  = 2,
	HAL_CAP_HT          = 5,
	HAL_CAP_RTS_AGGR_LIMIT = 6,
} HAL_CAPABILITY_TYPE;

typedef enum {
	HAL_TX_QUEUE_INACTIVE   = 0,
	HAL_TX_QUEUE_DATA   = 1,
	HAL_TX_QUEUE_BEACON = 2,
	HAL_TX_QUEUE_CAB    = 3,
	HAL_TX_QUEUE_PSPOLL = 4,
	HAL_TX_QUEUE_UAPSD  = 5,
} HAL_TX_QUEUE;

typedef enum {
	HAL_WME_AC_BK   = 0,
	HAL_WME_AC_BE   = 1,
	HAL_WME_AC_VI   = 2,
	HAL_WME_AC_VO   = 3,
	HAL_WME_UPSD    = 4,
	HAL_XR_DATA     = 5,
} HAL_TX_QUEUE_SUBTYPE;

#define HAL_NUM_TX_QUEUES  10

typedef enum {
	HAL_PKT_TYPE_NORMAL = 0,
	HAL_PKT_TYPE_ATIM   = 1,
	HAL_PKT_TYPE_PSPOLL = 2,
	HAL_PKT_TYPE_BEACON = 3,
	HAL_PKT_TYPE_PROBE_RESP = 4,
	HAL_PKT_TYPE_CHIRP  = 5,
	HAL_PKT_TYPE_GRP_POLL = 6,
} HAL_PKT_TYPE;

typedef enum {
	HAL_RX_CLEAR_CTL_LOW    = 0x1,    /* force control channel to appear busy */
	HAL_RX_CLEAR_EXT_LOW    = 0x2,    /* force extension channel to appear busy */
} HAL_HT_RXCLEAR;

typedef enum {
	HAL_RX_FILTER_UCAST     = 0x00000001,   /* Allow unicast frames */
	HAL_RX_FILTER_MCAST     = 0x00000002,   /* Allow multicast frames */
	HAL_RX_FILTER_BCAST     = 0x00000004,   /* Allow broadcast frames */
	HAL_RX_FILTER_CONTROL   = 0x00000008,   /* Allow control frames */
	HAL_RX_FILTER_BEACON    = 0x00000010,   /* Allow beacon frames */
	HAL_RX_FILTER_PROM      = 0x00000020,   /* Promiscuous mode */
	HAL_RX_FILTER_XRPOLL    = 0x00000040,   /* Allow XR poll frmae */
	HAL_RX_FILTER_PROBEREQ  = 0x00000080,   /* Allow probe request frames */
	HAL_RX_FILTER_PHYERR    = 0x00000100,   /* Allow phy errors */
#ifdef MAGPIE_MERLIN
	HAL_RX_FILTER_PHYRADAR  =  0x00002000, /* Allow phy radar errors*/
	HAL_RX_FILTER_PSPOLL    = 0x00004000,   /* Allow PSPOLL frames */
	/*
	** PHY "Pseudo bits" should be in the upper 16 bits since the lower
	** 16 bits actually correspond to register 0x803c bits
	*/
#else
	HAL_RX_FILTER_PHYRADAR  = 0x00000200,   /* Allow phy radar errors*/
#endif
} HAL_RX_FILTER;

#define CHANNEL_QUARTER 0x8000  /* Quarter rate channel */
#define CHANNEL_HALF    0x4000  /* Half rate channel */

typedef enum {
	HAL_INT_RX      = 0x00000001,   /* Non-common mapping */
	HAL_INT_RXDESC  = 0x00000002,
	HAL_INT_RXNOFRM = 0x00000008,
	HAL_INT_RXEOL   = 0x00000010,
	HAL_INT_RXORN   = 0x00000020,
	HAL_INT_TX      = 0x00000040,   /* Non-common mapping */
	HAL_INT_TXDESC  = 0x00000080,
	HAL_INT_TXURN   = 0x00000800,
	HAL_INT_MIB     = 0x00001000,
	HAL_INT_RXPHY   = 0x00004000,
	HAL_INT_RXKCM   = 0x00008000,
	HAL_INT_SWBA    = 0x00010000,
	HAL_INT_BMISS   = 0x00040000,
	HAL_INT_BNR     = 0x00100000,   /* Non-common mapping */
	HAL_INT_GPIO    = 0x01000000,
	HAL_INT_CST     = 0x02000000,   /* Non-common mapping */
	HAL_INT_GTT     = 0x20000000,   /* Non-common mapping */
	HAL_INT_FATAL   = 0x40000000,   /* Non-common mapping */
	HAL_INT_GLOBAL  = 0x80000000,   /* Set/clear IER */
	HAL_INT_GENTIMER =0x08000000,   /* Non-common mapping */

	/* Interrupt bits that map directly to ISR/IMR bits */
	HAL_INT_COMMON  = HAL_INT_RXNOFRM
	| HAL_INT_RXDESC
	| HAL_INT_RXEOL
	| HAL_INT_RXORN
	| HAL_INT_TXURN
	| HAL_INT_TXDESC
	| HAL_INT_MIB
	| HAL_INT_RXPHY
	| HAL_INT_RXKCM
	| HAL_INT_SWBA
	| HAL_INT_BMISS
	| HAL_INT_GPIO,
	HAL_INT_NOCARD  = 0xffffffff    /* To signal the card was removed */
} HAL_INT;

#ifdef MAGPIE_MERLIN

#define HAL_RATESERIES_RTS_CTS    0x0001  /* use rts/cts w/this series */
#define HAL_RATESERIES_2040       0x0002  /* use ext channel for series */
#define HAL_RATESERIES_HALFGI     0x0004  /* use half-gi for series */
#define HAL_RATESERIES_STBC       0x0008  /* use STBC for series */

/* 11n */
typedef enum {
	HAL_HT_MACMODE_20   = 0,        /* 20 MHz operation */
	HAL_HT_MACMODE_2040 = 1,        /* 20/40 MHz operation */
} HAL_HT_MACMODE;

typedef enum {
	HAL_HT_PHYMODE_20   = 0,        /* 20 MHz operation */
	HAL_HT_PHYMODE_2040 = 1,        /* 20/40 MHz operation */
} HAL_HT_PHYMODE;

typedef enum {
	HAL_HT_EXTPROTSPACING_20 = 0,       /* 20 MHz spacing */
	HAL_HT_EXTPROTSPACING_25 = 1,       /* 25 MHz spacing */
} HAL_HT_EXTPROTSPACING;

typedef struct {
	HAL_HT_MACMODE          ht_macmode;     /* MAC - 20/40 mode */
	HAL_HT_PHYMODE          ht_phymode;     /* PHY - 20/40 mode */
	a_int8_t                ht_extoff;      /* ext channel offset */
	HAL_HT_EXTPROTSPACING   ht_extprotspacing;  /* ext channel protection spacing */
} HAL_HT_CWM;

typedef struct {
	a_uint8_t ht_txchainmask; /* tx chain mask    */
	a_uint8_t ht_rxchainmask; /* rx chain mask    */
} HAL_HT_MISC;

typedef struct {
	HAL_HT_CWM  cwm;
	HAL_HT_MISC misc;
} HAL_HT;

/* channelFlags */
#define CHANNEL_CW_INT  0x0002  /* CW interference detected on channel */
#define CHANNEL_TURBO   0x0010  /* Turbo Channel */
#define CHANNEL_CCK     0x0020  /* CCK channel */
#define CHANNEL_OFDM    0x0040  /* OFDM channel */
#define CHANNEL_2GHZ    0x0080  /* 2 GHz spectrum channel. */
#define CHANNEL_5GHZ    0x0100  /* 5 GHz spectrum channel */
#define CHANNEL_PASSIVE 0x0200  /* Only passive scan allowed in the channel */
#define CHANNEL_DYN     0x0400  /* dynamic CCK-OFDM channel */
#define CHANNEL_XR      0x0800  /* XR channel */
#define CHANNEL_STURBO  0x2000  /* Static turbo, no 11a-only usage */
#define CHANNEL_HALF    0x4000  /* Half rate channel */
#define CHANNEL_QUARTER 0x8000  /* Quarter rate channel */
#define CHANNEL_HT20    0x10000 /* HT20 channel */
#define CHANNEL_HT40    0x20000 /* HT40 channel */
#define CHANNEL_HT40U 	0x40000 /* control channel can be upper channel */
#define CHANNEL_HT40L 	0x80000 /* control channel can be lower channel */

/* privFlags */
#define CHANNEL_INTERFERENCE    0x01
#define CHANNEL_DFS             0x02 /* DFS required on channel */
#define CHANNEL_4MS_LIMIT	0x04 /* 4msec packet limit on this channel */
#define CHANNEL_DFS_CLEAR       0x08 /* if channel has been checked for DFS */

#define CHANNEL_A       (CHANNEL_5GHZ|CHANNEL_OFDM)
#define CHANNEL_B       (CHANNEL_2GHZ|CHANNEL_CCK)
#define CHANNEL_PUREG   (CHANNEL_2GHZ|CHANNEL_OFDM)
#define CHANNEL_G       (CHANNEL_2GHZ|CHANNEL_OFDM)
#define CHANNEL_T       (CHANNEL_5GHZ|CHANNEL_OFDM|CHANNEL_TURBO)
#define CHANNEL_ST      (CHANNEL_T|CHANNEL_STURBO)
#define CHANNEL_108G    (CHANNEL_2GHZ|CHANNEL_OFDM|CHANNEL_TURBO)
#define CHANNEL_108A    CHANNEL_T
#define CHANNEL_X       (CHANNEL_5GHZ|CHANNEL_OFDM|CHANNEL_XR)

#define CHANNEL_G_HT20  (CHANNEL_2GHZ|CHANNEL_HT20)
#define CHANNEL_A_HT20  (CHANNEL_5GHZ|CHANNEL_HT20)
#define CHANNEL_G_HT40  (CHANNEL_2GHZ|CHANNEL_HT20|CHANNEL_HT40)
#define CHANNEL_A_HT40  (CHANNEL_5GHZ|CHANNEL_HT20|CHANNEL_HT40)
#define CHANNEL_ALL				\
	(CHANNEL_OFDM |				\
	 CHANNEL_CCK |				\
	 CHANNEL_2GHZ |				\
	 CHANNEL_5GHZ |				\
	 CHANNEL_TURBO |			\
	 CHANNEL_HT20 |				\
	 CHANNEL_HT40)
#define CHANNEL_ALL_NOTURBO     (CHANNEL_ALL &~ CHANNEL_TURBO)

typedef struct {
	a_int32_t    rateCount;
	a_uint8_t    rateCodeToIndex[HAL_RATE_TABLE_SIZE];
	struct {
		a_uint8_t    valid;
		a_uint8_t    phy;
		a_int16_t    txPower;
		a_int16_t    txPower2Chains;
		a_int16_t    txPower3Chains;
		a_uint32_t   rateKbps;
		a_uint8_t    rateCode;
		a_uint8_t    shortPreamble;
		a_uint8_t    dot11Rate;
		a_uint8_t    controlRate;
		a_uint16_t   lpAckDuration;
		a_uint16_t   spAckDuration;
	} info[HAL_RATE_TABLE_SIZE];
} HAL_RATE_TABLE;

typedef struct {
	a_uint32_t   Tries;
	a_uint32_t   Rate;
	a_uint32_t   PktDuration;
	a_uint32_t   ChSel;
	a_uint32_t   RateFlags;
	a_uint32_t   RateIndex;
	a_uint32_t   TxPowerCap;     /* in 1/2 dBm units */
} HAL_11N_RATE_SERIES;

#else

typedef struct {
	a_int32_t    rateCount;
	a_uint8_t    rateCodeToIndex[HAL_RATE_TABLE_SIZE];
	struct {
		a_uint8_t    valid;
		a_uint8_t    phy;
		a_uint32_t   rateKbps;
		a_uint8_t    rateCode;
		a_uint8_t    shortPreamble;
		a_uint8_t    dot11Rate;
		a_uint8_t    controlRate;
		a_uint16_t   lpAckDuration;
		a_uint16_t   spAckDuration;
	} info[HAL_RATE_TABLE_SIZE];
} HAL_RATE_TABLE;

#define HAL_RATESERIES_RTS_CTS    0x0001  /* use rts/cts w/this series */
#define HAL_RATESERIES_2040       0x0002  /* use ext channel for series */
#define HAL_RATESERIES_HALFGI     0x0004  /* use half-gi for series */
#define HAL_RATESERIES_STBC       0x0008  /* use STBC for series */

typedef struct {
	a_uint32_t   Tries;
	a_uint32_t   Rate;
	a_uint32_t   PktDuration;
	a_uint32_t   ChSel;
	a_uint32_t   RateFlags;
} HAL_11N_RATE_SERIES;

#endif

enum {
	HAL_MODE_11A    = 0x001,        /* 11a channels */
	HAL_MODE_TURBO  = 0x002,        /* 11a turbo-only channels */
	HAL_MODE_11B    = 0x004,        /* 11b channels */
	HAL_MODE_PUREG  = 0x008,        /* 11g channels (OFDM only) */
	HAL_MODE_11G    = 0x008,        /* XXX historical */
	HAL_MODE_108G   = 0x020,        /* 11a+Turbo channels */
	HAL_MODE_108A   = 0x040,        /* 11g+Turbo channels */
	HAL_MODE_XR     = 0x100,        /* XR channels */
	HAL_MODE_11A_HALF_RATE = 0x200,     /* 11A half rate channels */
	HAL_MODE_11A_QUARTER_RATE = 0x400,  /* 11A quarter rate channels */
	HAL_MODE_11NG   = 0x4000,           /* 11ng channels */
	HAL_MODE_11NA   = 0x8000,           /* 11na channels */
	HAL_MODE_ALL    = 0xffff
};

typedef enum {
	HAL_KEY_TYPE_CLEAR,
	HAL_KEY_TYPE_WEP,
	HAL_KEY_TYPE_AES,
	HAL_KEY_TYPE_TKIP,
	HAL_KEY_TYPE_WAPI,
} HAL_KEY_TYPE;

struct ath_desc;
struct ath_rx_status;

struct ath_hal
{
	a_uint32_t ah_magic;
	HAL_SOFTC ah_sc;
	adf_os_device_t ah_dev;
           
	a_uint32_t ah_macVersion;
	a_uint16_t ah_macRev;
	a_uint16_t ah_phyRev;
	const HAL_RATE_TABLE *__ahdecl(*ah_getRateTable)(struct ath_hal *,
							 a_uint32_t mode);
	void      __ahdecl(*ah_detach)(struct ath_hal*);
	HAL_BOOL  __ahdecl(*ah_updateTxTrigLevel)(struct ath_hal*,
						  HAL_BOOL incTrigLevel);
           
	/* Misc Functions */
	void      __ahdecl(*ah_setDefAntenna)(struct ath_hal*, a_uint32_t);	
	void      __ahdecl(*ah_setRxFilter)(struct ath_hal*, a_uint32_t);
           
                      
	/* Target Transmit Functions */
	HAL_BOOL  __ahdecl(*ah_setTxDP)(struct ath_hal*, a_uint32_t, a_uint32_t txdp);
	a_uint32_t __ahdecl(*ah_numTxPending)(struct ath_hal *, a_uint32_t q);           
	HAL_BOOL  __ahdecl(*ah_startTxDma)(struct ath_hal*, a_uint32_t);
	HAL_BOOL  __ahdecl(*ah_stopTxDma)(struct ath_hal*, a_uint32_t);
           
	HAL_BOOL  __ahdecl(*ah_abortTxDma)(struct ath_hal *);
           
	void      __ahdecl(*ah_set11nTxDesc)(struct ath_tx_desc *ds,
					     a_uint32_t pktLen, HAL_PKT_TYPE type,
					     a_uint32_t txPower, a_uint32_t keyIx,
					     HAL_KEY_TYPE keyType,
					     a_uint32_t flags);
	void      __ahdecl(*ah_set11nRateScenario)(struct ath_tx_desc *ds,
						   a_uint32_t durUpdateEn,
						   a_uint32_t rtsctsRate,
						   HAL_11N_RATE_SERIES series[],
						   a_uint32_t nseries, a_uint32_t flags);
	void      __ahdecl(*ah_set11nAggrFirst)(struct ath_tx_desc *ds, a_uint32_t aggrLen,
						a_uint32_t numDelims);
	void      __ahdecl(*ah_set11nAggrMiddle)(struct ath_tx_desc *ds, a_uint32_t numDelims);
	void      __ahdecl(*ah_set11nAggrLast)(struct ath_tx_desc *ds);
	void      __ahdecl(*ah_clr11nAggr)(struct ath_tx_desc *ds);
	void      __ahdecl(*ah_set11nBurstDuration)(struct ath_tx_desc *ds,
						    a_uint32_t burstDuration);
	void      __ahdecl(*ah_set11nVirtualMoreFrag)(struct ath_tx_desc *ds, a_uint32_t vmf);
           
	HAL_BOOL  __ahdecl(*ah_setupTxDesc)(struct ath_tx_desc *,
					    a_uint32_t pktLen, a_uint32_t hdrLen,
					    HAL_PKT_TYPE type, a_uint32_t txPower,
					    a_uint32_t txRate0, a_uint32_t txTries0,
					    a_uint32_t keyIx, a_uint32_t flags,
					    a_uint32_t rtsctsRate, a_uint32_t rtsctsDuration);
	HAL_BOOL  __ahdecl(*ah_fillTxDesc)(struct ath_tx_desc *,
					   a_uint32_t segLen, HAL_BOOL firstSeg,
					   HAL_BOOL lastSeg, const struct ath_tx_desc *);
	HAL_BOOL  __ahdecl (*ah_fillKeyTxDesc) (struct ath_tx_desc *, HAL_KEY_TYPE);
	HAL_STATUS __ahdecl(*ah_procTxDesc)(struct ath_hal *, struct ath_tx_desc *);
	HAL_BOOL  __ahdecl(*ah_setBssIdMask)(struct ath_hal *, const a_uint8_t*);
	void      __ahdecl(*ah_setPCUConfig)(struct ath_hal *);
	void      __ahdecl(*ah_setMulticastFilter)(struct ath_hal*,
						   a_uint32_t filter0, a_uint32_t filter1);

	u_int64_t __ahdecl(*ah_getTsf64)(struct ath_hal*);
           
	/* Target receive Functions */
	void	   __ahdecl(*ah_setRxDP)(struct ath_hal*, a_uint32_t rxdp);
	HAL_BOOL  __ahdecl(*ah_setupRxDesc)(struct ath_rx_desc *,
					    a_uint32_t size, a_uint32_t flags);
	HAL_STATUS __ahdecl(*ah_procRxDesc)(struct ath_hal *, struct ath_desc *,
					    a_uint32_t phyAddr, struct ath_desc *next, u_int64_t tsf);
	HAL_STATUS __ahdecl(*ah_procRxDescFast)(struct ath_hal *ah, 
						struct ath_rx_desc *ds, a_uint32_t pa,
						struct ath_desc *nds, 
						struct ath_rx_status *rx_stats);
	HAL_BOOL  __ahdecl(*ah_stopDmaReceive)(struct ath_hal*);
	void      __ahdecl(*ah_stopPcuReceive)(struct ath_hal*);
	void      __ahdecl(*ah_enableReceive)(struct ath_hal*);
           
	/* Interrupt functions */
	HAL_BOOL  __ahdecl(*ah_isInterruptPending)(struct ath_hal*);
	HAL_BOOL  __ahdecl(*ah_getPendingInterrupts)(struct ath_hal*, HAL_INT*);
	HAL_INT   __ahdecl(*ah_setInterrupts)(struct ath_hal*, HAL_INT);
};


extern struct ath_hal * __ahdecl ath_hal_attach_tgt(a_uint32_t devid, HAL_SOFTC,
						    adf_os_device_t dev,
						    a_uint32_t flags, HAL_STATUS* status);

extern a_uint16_t __ahdecl ath_hal_computetxtime(struct ath_hal *,
						 const HAL_RATE_TABLE *rates,
						 a_uint32_t frameLen,
						 a_uint16_t rateix,
						 HAL_BOOL shortPreamble);
#endif /* _ATH_AH_H_ */
