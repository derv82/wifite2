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
 * Copyright (c) 2002-2005 Sam Leffler, Errno Consulting
 * Copyright (c) 2002-2005 Atheros Communications, Inc.
 * All rights reserved.
 *
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/wlan/target/hal/main/ah_internal.h#2 $
 */
#ifndef _ATH_AH_INTERAL_H_
#define _ATH_AH_INTERAL_H_

#include <stdarg.h>

#define IEEE80211_AMPDU_LIMIT_MAX   (64 * 1024 - 1)

#define AH_NULL 0
#define AH_MIN(a,b) ((a)<(b)?(a):(b))
#define AH_MAX(a,b) ((a)>(b)?(a):(b))

/*
 * Common assertion interface.  Note: it is a bad idea to generate
 * an assertion failure for any recoverable event.  Instead catch
 * the violation and, if possible, fix it up or recover from it; either
 * with an error return value or a diagnostic messages.  System software
 * does not panic unless the situation is hopeless.
 */
#ifdef AH_ASSERT
#define HALASSERT(_x) do {			\
		adf_os_assert(_x)		\
		} while (0)
#else
#define HALASSERT(_x)
#endif /* AH_ASSERT */

#ifndef NBBY
#define NBBY    8           /* number of bits/byte */
#endif

#define IEEE80211_ADDR_LEN 6

/*
 * Internal form of a HAL_CHANNEL.  Note that the structure
 * must be defined such that you can cast references to a
 * HAL_CHANNEL so don't shuffle the first two members.
 */
typedef struct {
	a_uint16_t   channel;    /* NB: must be first for casting */
	a_uint32_t   channelFlags;
	a_uint8_t    privFlags;
	int8_t       maxRegTxPower;
	int8_t       maxTxPower;
	int8_t       minTxPower; /* as above... */
	a_uint8_t    regClassId; /* Regulatory class id */
	HAL_BOOL     bssSendHere;
	a_uint8_t    gainI;
	HAL_BOOL     iqCalValid;
	HAL_BOOL     oneTimeCalsDone;
	int8_t       iCoff;
	int8_t       qCoff;
	a_int16_t    rawNoiseFloor;
	a_int16_t    finalNoiseFloor;
	int8_t       antennaMax;
	a_uint32_t   regDmnFlags;    /* Flags for channel use in reg */
	a_uint32_t   conformanceTestLimit;   /* conformance test limit from reg domain */
	a_uint16_t   mainSpur;		/* cached spur value for this cahnnel */
	u_int64_t    ah_tsf_last;    /* tsf @ which time accured is computed */
	u_int64_t    ah_channel_time;	/* time on the channel  */
	u_int64_t    dfsTsf; /* Tsf when channel leaves NOL */
} HAL_CHANNEL_INTERNAL;

typedef struct {
	a_uint32_t   halChanSpreadSupport   : 1,
		halSleepAfterBeaconBroken   : 1,
		halCompressSupport      : 1,
		halBurstSupport         : 1,
		halFastFramesSupport    : 1,
		halChapTuningSupport    : 1,
		halTurboGSupport        : 1,
		halTurboPrimeSupport    : 1,
		halXrSupport            : 1,
		halMicAesCcmSupport     : 1,
		halMicCkipSupport       : 1,
		halMicTkipSupport       : 1,
		halCipherAesCcmSupport  : 1,
		halCipherCkipSupport    : 1,
		halCipherTkipSupport    : 1,
		halPSPollBroken         : 1,
		halVEOLSupport          : 1,
		halBssIdMaskSupport     : 1,
		halMcastKeySrchSupport  : 1,
		halTsfAddSupport        : 1,
		halChanHalfRate         : 1,
		halChanQuarterRate      : 1,
		halHTSupport            : 1,
		halGTTSupport           : 1,
		halFastCCSupport        : 1,
		halExtChanDfsSupport    : 1,
		halUseCombinedRadarRssi : 1,
		halCSTSupport           : 1,
		halRifsRxSupport        : 1,
		halRifsTxSupport        : 1,
#ifdef MAGPIE_MERLIN
		halforcePpmSupport      : 1,
		halAutoSleepSupport     : 1,
		hal4kbSplitTransSupport : 1,
		halEnhancedPmSupport    : 1,
		halMbssidAggrSupport    : 1,
		halTkipWepHtRateSupport : 1,
#endif
		halRfSilentSupport	: 1;
	a_uint32_t   halWirelessModes;
	a_uint16_t   halTotalQueues;
	a_uint16_t   halKeyCacheSize;
	a_uint16_t   halLow5GhzChan, halHigh5GhzChan;
	a_uint16_t   halLow2GhzChan, halHigh2GhzChan;
	a_uint16_t   halNumMRRetries;
	a_uint8_t    halTxChainMask;
	a_uint8_t    halRxChainMask;
	a_uint16_t   halRtsAggrLimit;
	a_uint16_t   halJapanRegCap;
	a_uint8_t    halNumGpioPins;
} HAL_CAPABILITIES;


#if !defined(_NET_IF_IEEE80211_H_) && !defined(_NET80211__IEEE80211_H_)
/*
 * Stuff that would naturally come from _ieee80211.h
 */
#define IEEE80211_ADDR_LEN      6
#define IEEE80211_WEP_KEYLEN    5   /* 40bit */
#define IEEE80211_WEP_IVLEN     3   /* 24bit */
#define IEEE80211_WEP_KIDLEN    1   /* 1 octet */
#define IEEE80211_WEP_CRCLEN    4   /* CRC-32 */
#define IEEE80211_CRC_LEN       4
#define IEEE80211_MTU           1500
#define IEEE80211_MAX_LEN       (2300 + IEEE80211_CRC_LEN + \
    (IEEE80211_WEP_IVLEN + IEEE80211_WEP_KIDLEN + IEEE80211_WEP_CRCLEN))

#define WLAN_CTRL_FRAME_SIZE    (2+2+6+4)   /* ACK+FCS */

enum {
	IEEE80211_T_DS,         /* direct sequence spread spectrum */
	IEEE80211_T_FH,         /* frequency hopping */
	IEEE80211_T_OFDM,       /* frequency division multiplexing */
	IEEE80211_T_TURBO,      /* high rate DS */
	IEEE80211_T_HT,         /* HT - full GI */
	IEEE80211_T_MAX
};
#define IEEE80211_T_CCK IEEE80211_T_DS  /* more common nomenclatur */
#endif /* _NET_IF_IEEE80211_H_ */

/* NB: these are defined privately until XR support is announced */
enum {
	ATHEROS_T_XR    = IEEE80211_T_MAX,  /* extended range */
};

struct ath_hal_private {
	struct ath_hal h;

	a_uint32_t ah_macVersion;
	a_uint16_t ah_macRev;
	a_uint16_t ah_phyRev;

	HAL_CAPABILITIES ah_caps;       /* device capabilities */
	HAL_CHANNEL_INTERNAL *ah_curchan;   /* current channel */
};

#define AH_PRIVATE(_ah) ((struct ath_hal_private *)(_ah))

#define IS_CHAN_A(_c)   ((((_c)->channelFlags & CHANNEL_A) == CHANNEL_A) || \
             (((_c)->channelFlags & CHANNEL_A_HT20) == CHANNEL_A_HT20))
#define IS_CHAN_B(_c)   (((_c)->channelFlags & CHANNEL_B) == CHANNEL_B)
#define IS_CHAN_G(_c)   ((((_c)->channelFlags & (CHANNEL_108G|CHANNEL_G)) == CHANNEL_G) || \
             (((_c)->channelFlags & CHANNEL_G_HT20) == CHANNEL_G_HT20))
#define IS_CHAN_108G(_c)(((_c)->channelFlags & CHANNEL_108G) == CHANNEL_108G)
#define IS_CHAN_T(_c)   (((_c)->channelFlags & CHANNEL_T) == CHANNEL_T)
#define IS_CHAN_X(_c)   (((_c)->channelFlags & CHANNEL_X) == CHANNEL_X)
#define IS_CHAN_PUREG(_c) \
	(((_c)->channelFlags & CHANNEL_PUREG) == CHANNEL_PUREG)
#define IS_CHAN_NA(_c)  (((_c)->channelFlags & CHANNEL_A_HT20) == CHANNEL_A_HT20)
#define IS_CHAN_NG(_c)  (((_c)->channelFlags & CHANNEL_G_HT20) == CHANNEL_G_HT20)

#define IS_CHAN_TURBO(_c)   (((_c)->channelFlags & CHANNEL_TURBO) != 0)
#define IS_CHAN_CCK(_c)     (((_c)->channelFlags & CHANNEL_CCK) != 0)
#define IS_CHAN_OFDM(_c)    (((_c)->channelFlags & CHANNEL_OFDM) != 0)
#define IS_CHAN_XR(_c)      (((_c)->channelFlags & CHANNEL_XR) != 0)
#define IS_CHAN_5GHZ(_c)    (((_c)->channelFlags & CHANNEL_5GHZ) != 0)
#define IS_CHAN_2GHZ(_c)    (((_c)->channelFlags & CHANNEL_2GHZ) != 0)
#define IS_CHAN_PASSIVE(_c) (((_c)->channelFlags & CHANNEL_PASSIVE) != 0)
#define IS_CHAN_HALF_RATE(_c)   (((_c)->channelFlags & CHANNEL_HALF) != 0)
#define IS_CHAN_QUARTER_RATE(_c) (((_c)->channelFlags & CHANNEL_QUARTER) != 0)
#define IS_CHAN_HT(_c)      (((_c)->channelFlags & CHANNEL_HT20) != 0)
#define IS_CHAN_HT20(_c)    (((_c)->channelFlags & CHANNEL_HT20) != 0)
#define IS_CHAN_HT40(_c)    (((_c)->channelFlags & CHANNEL_HT40) != 0)

#define IS_CHAN_IN_PUBLIC_SAFETY_BAND(_c) ((_c) > 4940 && (_c) < 4990)

/*
 * Register manipulation macros that expect bit field defines
 * to follow the convention that an _S suffix is appended for
 * a shift count, while the field mask has no suffix.
 */
#define SM(_v, _f)  (((_v) << _f##_S) & _f)
#define MS(_v, _f)  (((_v) & _f) >> _f##_S)
#define OS_REG_RMW_FIELD(_a, _r, _f, _v)				\
	iowrite32_mac(_r,						\
		     (ioread32_mac(_r) & ~_f)		\
		      | (((_v) << _f##_S) & _f))
#define OS_REG_RMW(_a, _r, _set, _clr)					\
	iowrite32_mac(_r,						\
		     (ioread32_mac(_r) & ~(_clr)) | (_set))
#define OS_REG_SET_BIT(_a, _r, _f)			\
	iowrite32_mac(_r, ioread32_mac(_r) | _f)
#define OS_REG_CLR_BIT(_a, _r, _f)			\
	iowrite32_mac(_r, ioread32_mac(_r) & ~_f)


/* wait for the register contents to have the specified value */
extern HAL_BOOL ath_hal_wait(struct ath_hal *, a_uint32_t reg,
			     a_uint32_t mask, a_uint32_t val);

/* allocate and free memory */
extern void *ath_hal_malloc(size_t);
extern void ath_hal_free(void *);

/*
 * Generic get/set capability support.  Each chip overrides
 * this routine to support chip-specific capabilities.
 */
extern HAL_STATUS ath_hal_getcapability(struct ath_hal *ah,
		HAL_CAPABILITY_TYPE type);
extern HAL_BOOL ath_hal_setcapability(struct ath_hal *ah,
	      HAL_CAPABILITY_TYPE type, a_uint32_t capability,
	      a_uint32_t setting, HAL_STATUS *status);

#endif /* _ATH_AH_INTERAL_H_ */
