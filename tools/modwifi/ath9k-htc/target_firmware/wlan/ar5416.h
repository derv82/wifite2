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

#include <ar5416desc.h>

extern  HAL_STATUS ar5416GetCapability(struct ath_hal *, HAL_CAPABILITY_TYPE,
        a_uint32_t, a_uint32_t *);
extern  const HAL_RATE_TABLE *ar5416GetRateTable(struct ath_hal *, a_uint32_t mode);
extern  HAL_BOOL ar5416IsInterruptPending(struct ath_hal *ah);
extern  HAL_BOOL ar5416GetPendingInterrupts(struct ath_hal *ah, HAL_INT *);
extern  HAL_INT ar5416GetInterrupts(struct ath_hal *ah);
extern  HAL_INT ar5416SetInterrupts(struct ath_hal *ah, HAL_INT ints);
extern  a_uint32_t ar5416Get11nExtBusy(struct ath_hal *ah);
extern  HAL_HT_RXCLEAR ar5416Get11nRxClear(struct ath_hal *ah);
extern  void ar5416Set11nRxClear(struct ath_hal *ah, HAL_HT_RXCLEAR rxclear);
extern  a_uint32_t ar5416GetTsf32(struct ath_hal *ah);
extern  u_int64_t ar5416GetTsf64(struct ath_hal *ah);
extern  void ar5416ResetTsf(struct ath_hal *ah);
extern  void ar5416Detach(struct ath_hal *ah);

typedef enum Ar5416_Rates {
    rate6mb,  rate9mb,  rate12mb, rate18mb,
    rate24mb, rate36mb, rate48mb, rate54mb,
    rate1l,   rate2l,   rate2s,   rate5_5l,
    rate5_5s, rate11l,  rate11s,  rateXr,
    rateHt20_0, rateHt20_1, rateHt20_2, rateHt20_3,
    rateHt20_4, rateHt20_5, rateHt20_6, rateHt20_7,
    rateHt40_0, rateHt40_1, rateHt40_2, rateHt40_3,
    rateHt40_4, rateHt40_5, rateHt40_6, rateHt40_7,
    rateDupCck, rateDupOfdm, rateExtCck, rateExtOfdm,
    Ar5416RateSize
} AR5416_RATES;

#ifdef MAGPIE_MERLIN
#define AR_SREV_HOWL(ah) ((AH_PRIVATE(ah)->ah_macVersion) == AR_SREV_VERSION_HOWL)
#define IS_5416_HOWL AR_SREV_HOWL

#define AR5416_RATES_OFDM_OFFSET    0
#define AR5416_RATES_CCK_OFFSET     8
#define AR5416_RATES_HT20_OFFSET    16
#define AR5416_RATES_HT40_OFFSET    24

/* Delta from which to start power to pdadc table */

#define AR5416_PWR_TABLE_OFFSET  -5
#define AR5416_LEGACY_CHAINMASK		1
#define AR5416_1_CHAINMASK		1
#define AR5416_2LOHI_CHAINMASK          5	
#define AR5416_2LOMID_CHAINMASK         3	
#define AR5416_3_CHAINMASK		7

#define AH5416(_ah) ((struct ath_hal_5416 *)(_ah))

#else // For Owl

#endif // MAGPIE_MERLIN

#define AR5416_LEGACY_CHAINMASK		1

#define AH5416(_ah) ((struct ath_hal_5416 *)(_ah))

/*
 * Various fifo fill before Tx start, in 64-byte units
 * i.e. put the frame in the air while still DMAing
 */
#define MIN_TX_FIFO_THRESHOLD   0x1
#define MAX_TX_FIFO_THRESHOLD   (( 4096 / 64) - 1)
#define INIT_TX_FIFO_THRESHOLD  MIN_TX_FIFO_THRESHOLD

struct ath_hal_5416
{
	struct ath_hal_private  ah_priv;    /* base class */
	a_uint16_t   ah_antennaSwitchSwap;       /* Controls mapping of OID request */
	a_uint32_t   ah_maskReg; 	/* copy of AR_IMR */
           
	a_uint32_t   ah_slottime;        /* user-specified slot time */
	a_int16_t    ah_txPowerIndexOffset;
           
	a_uint32_t   ah_intrTxqs;
	void         *ah_cal_mem;
	a_uint16_t   ah_ratesArray[Ar5416RateSize];
#ifdef MAGPIE_MERLIN
	/* HT CWM state */
	HAL_HT_CWM   ah_htcwm;
#endif
};
