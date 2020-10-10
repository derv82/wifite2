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

#include "ah.h"
#include "ah_internal.h"
#include <asf_bitmap.h>

extern struct ath_hal *ar5416Attach(HAL_SOFTC sc, adf_os_device_t dev,
									HAL_STATUS *status);

struct ath_hal*
ath_hal_attach_tgt(a_uint32_t devid,HAL_SOFTC sc,
		   adf_os_device_t dev,
		   a_uint32_t flags, HAL_STATUS *error)
{
	struct ath_hal *ah = AH_NULL;

	ah = ar5416Attach(sc, dev, error);

	return ah;
}

HAL_STATUS
ath_hal_getcapability(struct ath_hal *ah, HAL_CAPABILITY_TYPE type)
{
	const HAL_CAPABILITIES *pCap = &AH_PRIVATE(ah)->ah_caps;
	switch (type) {
	case HAL_CAP_TSF_ADJUST:
		return HAL_ENOTSUPP;
	case HAL_CAP_BSSIDMASK:
		return pCap->halBssIdMaskSupport ? HAL_OK : HAL_ENOTSUPP;
	case HAL_CAP_VEOL:
		return pCap->halVEOLSupport ? HAL_OK : HAL_ENOTSUPP;
	default:
		return HAL_EINVAL;
	}
}

#define CCK_SIFS_TIME        10
#define CCK_PREAMBLE_BITS   144
#define CCK_PLCP_BITS        48

#define OFDM_SIFS_TIME        16
#define OFDM_PREAMBLE_TIME    20
#define OFDM_PLCP_BITS        22
#define OFDM_SYMBOL_TIME       4

#define OFDM_SIFS_TIME_HALF     32
#define OFDM_PREAMBLE_TIME_HALF 40
#define OFDM_PLCP_BITS_HALF     22
#define OFDM_SYMBOL_TIME_HALF   8

#define OFDM_SIFS_TIME_QUARTER      64
#define OFDM_PREAMBLE_TIME_QUARTER  80
#define OFDM_PLCP_BITS_QUARTER      22
#define OFDM_SYMBOL_TIME_QUARTER    16

a_uint16_t
ath_hal_computetxtime(struct ath_hal *ah,
		      const HAL_RATE_TABLE *rates, a_uint32_t frameLen, a_uint16_t rateix,
		      HAL_BOOL shortPreamble)
{
	a_uint32_t bitsPerSymbol, numBits, numSymbols, phyTime, txTime;
	a_uint32_t kbps;

	kbps = rates->info[rateix].rateKbps;

	/*
	 * index can be invalid duting dynamic Turbo transitions.
	 */
	if(kbps == 0) return 0;
	switch (rates->info[rateix].phy) {

	case IEEE80211_T_CCK:
		phyTime = CCK_PREAMBLE_BITS + CCK_PLCP_BITS;
		if (shortPreamble && rates->info[rateix].shortPreamble)
			phyTime >>= 1;
		numBits = frameLen << 3;
		txTime = phyTime + ((numBits * 1000)/kbps);
		/* TODO: make sure the same value of txTime can use in all device */
		if (ath_hal_getcapability(ah, HAL_CAP_HT) != HAL_OK)
			txTime = txTime + CCK_SIFS_TIME;
		break;
	case IEEE80211_T_OFDM:
		/* full rate channel */
		bitsPerSymbol   = (kbps * OFDM_SYMBOL_TIME) / 1000;
		HALASSERT(bitsPerSymbol != 0);

		numBits = OFDM_PLCP_BITS + (frameLen << 3);
		numSymbols = asf_howmany(numBits, bitsPerSymbol);
		txTime = OFDM_PREAMBLE_TIME + (numSymbols * OFDM_SYMBOL_TIME);
		/* TODO: make sure the same value of txTime can use in all device */
		if (ath_hal_getcapability(ah, HAL_CAP_HT) != HAL_OK)
			txTime = txTime + OFDM_SIFS_TIME;
		break;
	default:
		txTime = 0;
		break;
	}
	return txTime;
}

#undef CCK_SIFS_TIME
#undef CCK_PREAMBLE_BITS
#undef CCK_PLCP_BITS

#undef OFDM_SIFS_TIME
#undef OFDM_PREAMBLE_TIME
#undef OFDM_PLCP_BITS
#undef OFDM_SYMBOL_TIME

#ifdef MAGPIE_MERLIN
a_uint32_t 
ath_hal_get_curmode(struct ath_hal *ah, HAL_CHANNEL_INTERNAL *chan)
{
	if (!chan)
		return HAL_MODE_11NG;

	if (IS_CHAN_NA(chan))
		return HAL_MODE_11NA; 

	if (IS_CHAN_A(chan))
		return HAL_MODE_11A;

	if (IS_CHAN_NG(chan))
		return HAL_MODE_11NG;

	if (IS_CHAN_G(chan))
		return HAL_MODE_11G;

	if (IS_CHAN_B(chan))
		return HAL_MODE_11B;

	HALASSERT(0);
	return HAL_MODE_11NG;
}

#endif

HAL_BOOL
ath_hal_wait(struct ath_hal *ah, a_uint32_t reg, a_uint32_t mask, a_uint32_t val)
{
#define AH_TIMEOUT_11N 100000
#define AH_TIMEOUT_11G  1000

	a_int32_t i;

	if (ath_hal_getcapability(ah, HAL_CAP_HT) == HAL_OK) {
		for (i = 0; i < AH_TIMEOUT_11N; i++) {
			if ((ioread32_mac(reg) & mask) == val)
				return AH_TRUE;
			OS_DELAY(10);
		}
	} else {
		for (i = 0; i < AH_TIMEOUT_11G; i++) {
			if ((ioread32_mac(reg) & mask) == val)
				return AH_TRUE;
			OS_DELAY(10);
		}
	}
	return AH_FALSE;

#undef AH_TIMEOUT_11N
#undef AH_TIMEOUT_11G
}
