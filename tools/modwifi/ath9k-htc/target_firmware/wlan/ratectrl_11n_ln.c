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

#include <adf_os_types.h>
#include <adf_os_dma.h>
#include <adf_os_timer.h>
#include <adf_os_lock.h>
#include <adf_os_io.h>
#include <adf_os_mem.h>
#include <adf_os_module.h>
#include <adf_os_pci.h>
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>

#include <ieee80211_var.h>

#include <if_athvar.h>
#include "ah_desc.h"

#include "ratectrl.h"
#include "ratectrl11n.h"

static void ath_rate_newassoc_11n(struct ath_softc_tgt *sc, struct ath_node_target *an, int isnew, 
				  unsigned int capflag, struct ieee80211_rate *rs);


static void ath_rate_tx_complete_11n(struct ath_softc_tgt *sc, struct ath_node_target *an, 
                                     struct ath_tx_desc *ds,
                                     struct ath_rc_series rcs[], int nframes, 
                                     int nbad);

static void ath_rate_findrate_11n(struct ath_softc_tgt *sc,
				  struct ath_node_target *an,
				  size_t frameLen,
				  int numTries,
				  int numRates,
				  int stepDnInc,
				  unsigned int rcflag,
				  struct ath_rc_series series[],
				  int *isProbe);

static void
rcSortValidRates(const RATE_TABLE_11N *pRateTable, TX_RATE_CTRL *pRc)
{
	A_UINT8 i,j;

	for (i=pRc->maxValidRate-1; i > 0; i--) {
		for (j=0; j <= i-1; j++) {
#ifdef MAGPIE_MERLIN      
			if (pRateTable->info[pRc->validRateIndex[j]].rateKbps >
			    pRateTable->info[pRc->validRateIndex[j+1]].rateKbps)
#else
				// K2
				if (pRateTable->info[pRc->validRateIndex[j]].userRateKbps >
				    pRateTable->info[pRc->validRateIndex[j+1]].userRateKbps)
#endif
				{
					A_UINT8 tmp=0;
					tmp = pRc->validRateIndex[j];
					pRc->validRateIndex[j] = pRc->validRateIndex[j+1];
					pRc->validRateIndex[j+1] = tmp;
				}
		}
	}
}

/* Access functions for validTxRateMask */

static void
rcInitValidTxMask(TX_RATE_CTRL *pRc)
{
	A_UINT8 i;

	for (i = 0; i < pRc->rateTableSize; i++) {
		pRc->validRateIndex[i] = FALSE;
	}
}

static INLINE void
rcSetValidTxMask(TX_RATE_CTRL *pRc, A_UINT8 index, A_BOOL validTxRate)
{
	ASSERT(index < pRc->rateTableSize);
	pRc->validRateIndex[index] = validTxRate ? TRUE : FALSE;

}

/* Iterators for validTxRateMask */
static INLINE A_BOOL
rcGetNextValidTxRate(const RATE_TABLE_11N *pRateTable, TX_RATE_CTRL *pRc, 
                     A_UINT8 curValidTxRate, A_UINT8 *pNextIndex)
{
	A_UINT8 i;

	for (i = 0; i < pRc->maxValidRate-1; i++) {
		if (pRc->validRateIndex[i] == curValidTxRate) {
			*pNextIndex = pRc->validRateIndex[i+1];
			return TRUE;
		}
	}

	/* No more valid rates */
	*pNextIndex = 0;
    
	return FALSE;
}

static INLINE A_BOOL
rcGetNextLowerValidTxRate(const RATE_TABLE_11N *pRateTable, TX_RATE_CTRL *pRc,  
                          A_UINT8 curValidTxRate, A_UINT8 *pNextIndex)
{
	A_INT8 i;

	for (i = 1; i < pRc->maxValidRate ; i++) {
		if (pRc->validRateIndex[i] == curValidTxRate) {
			*pNextIndex = pRc->validRateIndex[i-1];
			return TRUE;
		}
	}

	return FALSE;
}

/* Return true only for single stream */

static A_BOOL
rcIsValidPhyRate(A_UINT32 phy, A_UINT32 capflag, A_BOOL ignoreCW)
{
	if (WLAN_RC_PHY_HT(phy) && !(capflag & WLAN_RC_HT_FLAG)) {
		return FALSE;
	}

	if (WLAN_RC_PHY_DS(phy) && !(capflag & WLAN_RC_DS_FLAG))  {
		return FALSE;
	}
	if (WLAN_RC_PHY_SGI(phy) && !(capflag & WLAN_RC_HT40_SGI_FLAG)) {
		return FALSE;
	}

	if (!ignoreCW && WLAN_RC_PHY_HT(phy)) {
		if (WLAN_RC_PHY_40(phy) && !(capflag & WLAN_RC_40_FLAG)) {
			return FALSE;
		}

		if (!WLAN_RC_PHY_40(phy) && (capflag & WLAN_RC_40_FLAG)) {
			return FALSE;
		}
	}
    
	return TRUE;
}

/* 
 * Initialize the Valid Rate Index from valid entries in Rate Table 
 */
static A_UINT8 rcSibInitValidRates(const RATE_TABLE_11N *pRateTable,
				   TX_RATE_CTRL *pRc,
				   A_UINT32 capflag,
				   PHY_STATE_CTRL *pPhyStateCtrl)
{
	A_UINT8 i, hi = 0;
	A_UINT8 singleStream = (capflag & WLAN_RC_DS_FLAG) ? 0 : 1;
	A_UINT8 valid;
    
	for (i = 0; i < pRateTable->rateCount; i++) {
		if (singleStream) {
			valid = pRateTable->info[i].validSingleStream;
		} else {
			valid = pRateTable->info[i].valid;
		}
            
		if (valid == TRUE) {
			A_UINT32 phy = pRateTable->info[i].phy;

			if (!rcIsValidPhyRate(phy, capflag, FALSE)) 
				continue;

			pPhyStateCtrl->validPhyRateIndex[phy][pPhyStateCtrl->validPhyRateCount[phy]] = i;
			pPhyStateCtrl->validPhyRateCount[phy] += 1;

			rcSetValidTxMask(pRc, i, TRUE);

			hi = A_MAX(hi, i);
		}
	} 
    
	return hi;
}

/* 
 * Initialize the Valid Rate Index from Rate Set 
 */
static A_UINT8
rcSibSetValidRates(const RATE_TABLE_11N *pRateTable,
		   TX_RATE_CTRL *pRc, 
                   struct ieee80211_rateset *pRateSet,
		   A_UINT32 capflag,
		   struct ath_node_target *an,
		   PHY_STATE_CTRL *pPhyStateCtrl)
{
	A_UINT8 i, j, hi = 0;
	A_UINT8 singleStream = (capflag & WLAN_RC_DS_FLAG) ? 0 : 1;
	A_UINT32 valid;
       
	/* Use intersection of working rates and valid rates */
	for (i = 0; i < pRateSet->rs_nrates; i++) {
		for (j = 0; j < pRateTable->rateCount; j++) {
			A_UINT32 phy = pRateTable->info[j].phy;
#ifdef MAGPIE_MERLIN
			struct atheros_node *pSib = ATH_NODE_ATHEROS(an);

			if (pSib->stbc) {
				valid = pRateTable->info[j].validSTBC;
			} else if (singleStream) {
#else
			if (singleStream) {
#endif            
				valid = pRateTable->info[j].validSingleStream;
			} else {
				valid = pRateTable->info[j].valid;
			}
        
			/*
			 * We allow a rate only if its valid and the capflag matches one of
			 * the validity (TRUE/TRUE_20/TRUE_40) flags
			 */

			if (((pRateSet->rs_rates[i] & 0x7F) == 
			     (pRateTable->info[j].dot11Rate & 0x7F))
			    && ((valid & WLAN_RC_CAP_MODE(capflag)) == 
				WLAN_RC_CAP_MODE(capflag)) && !WLAN_RC_PHY_HT(phy)) {
				if (!rcIsValidPhyRate(phy, capflag, FALSE)) 
					continue;

				pPhyStateCtrl->validPhyRateIndex[phy][pPhyStateCtrl->validPhyRateCount[phy]] = j;
				pPhyStateCtrl->validPhyRateCount[phy] += 1;

				rcSetValidTxMask(pRc, j, TRUE);
				hi = A_MAX(hi, j);
			}
		}
	}
  
	return hi;
}

static A_UINT8
rcSibSetValidHtRates(const RATE_TABLE_11N *pRateTable,
		     TX_RATE_CTRL *pRc, 
                     A_UINT8 *pMcsSet,
		     A_UINT32 capflag,
		     struct ath_node_target *an,
		     PHY_STATE_CTRL *pPhyStateCtrl)
{
	A_UINT8 i, j, hi = 0;
	A_UINT8 singleStream = (capflag & WLAN_RC_DS_FLAG) ? 0 : 1;
	A_UINT8 valid;
    
	/* Use intersection of working rates and valid rates */
	for (i = 0; i <  ((struct ieee80211_rateset *)pMcsSet)->rs_nrates; i++) {
		for (j = 0; j < pRateTable->rateCount; j++) {
			A_UINT32 phy = pRateTable->info[j].phy;
#ifdef MAGPIE_MERLIN
			struct atheros_node *pSib = ATH_NODE_ATHEROS(an);

			if (pSib->stbc) {
				valid = pRateTable->info[j].validSTBC;
			} else if (singleStream) {
#else
			if (singleStream) {
#endif
				valid = pRateTable->info[j].validSingleStream;
			} else {
				valid = pRateTable->info[j].valid;
			}
                           
			if (((((struct ieee80211_rateset *)pMcsSet)->rs_rates[i] & 0x7F) 
			     != (pRateTable->info[j].dot11Rate & 0x7F)) 
			    || !WLAN_RC_PHY_HT(phy) 
			    || !WLAN_RC_PHY_HT_VALID(valid, capflag)
			    || ((pRateTable->info[j].dot11Rate == 15) && 
				(valid & TRUE_20) && 
				(capflag & WLAN_RC_WEP_TKIP_FLAG)) )
			{
				continue;
			}
    
			if (!rcIsValidPhyRate(phy, capflag, FALSE)) 
				continue;
    
			pPhyStateCtrl->validPhyRateIndex[phy][pPhyStateCtrl->validPhyRateCount[phy]] = j;
			pPhyStateCtrl->validPhyRateCount[phy] += 1;

			rcSetValidTxMask(pRc, j, TRUE);
			hi = A_MAX(hi, j);
		}
	}

	return hi;
}

/*
 *  Update the SIB's rate control information
 *
 *  This should be called when the supported rates change
 *  (e.g. SME operation, wireless mode change)
 *
 *  It will determine which rates are valid for use.
 */
static void
rcSibUpdate_ht(struct ath_softc_tgt *sc, struct ath_node_target *an,
	       A_UINT32 capflag, A_BOOL keepState, struct ieee80211_rate  *pRateSet)
{
	RATE_TABLE_11N *pRateTable = 0;
	struct atheros_node *pSib = ATH_NODE_ATHEROS(an);
	struct atheros_softc *asc = (struct atheros_softc*)sc->sc_rc;
	A_UINT8 *phtMcs = (A_UINT8*)&pRateSet->htrates;
	TX_RATE_CTRL *pRc = (TX_RATE_CTRL *)(pSib);
	PHY_STATE_CTRL mPhyCtrlState;  

	A_UINT8 i, j, k, hi = 0, htHi = 0;

	pRateTable = (RATE_TABLE_11N*)asc->hwRateTable[sc->sc_curmode];

	/* Initial rate table size. Will change depending on the working rate set */
	pRc->rateTableSize = MAX_TX_RATE_TBL;

	/* Initialize thresholds according to the global rate table */
	for (i = 0 ; (i < pRc->rateTableSize) && (!keepState); i++) {
		pRc->state[i].per       = 0;
	}

	/* Determine the valid rates */
	rcInitValidTxMask(pRc);

	for (i = 0; i < WLAN_RC_PHY_MAX; i++) {
		for (j = 0; j < MAX_TX_RATE_TBL; j++) {
			mPhyCtrlState.validPhyRateIndex[i][j] = 0;
		}   
		mPhyCtrlState.validPhyRateCount[i] = 0;
	}

	pRc->rcPhyMode = (capflag & WLAN_RC_40_FLAG);

	if (pRateSet == NULL || !pRateSet->rates.rs_nrates) {
		/* No working rate, just initialize valid rates */
		hi = rcSibInitValidRates(pRateTable, pRc, capflag, &mPhyCtrlState);
	} else {
		/* Use intersection of working rates and valid rates */
		hi = rcSibSetValidRates(pRateTable, pRc, &(pRateSet->rates),
					capflag, an, &mPhyCtrlState);

		if (capflag & WLAN_RC_HT_FLAG) {
			htHi = rcSibSetValidHtRates(pRateTable, pRc, phtMcs,
						    capflag, an, &mPhyCtrlState);
		}

		hi = A_MAX(hi, htHi);
	}

	pRc->rateTableSize = hi + 1;
	pRc->rateMaxPhy    = 0;
    
	ASSERT(pRc->rateTableSize <= MAX_TX_RATE_TBL);

	for (i = 0, k = 0; i < WLAN_RC_PHY_MAX; i++) {
		for (j = 0; j < mPhyCtrlState.validPhyRateCount[i]; j++) {
			pRc->validRateIndex[k++] = mPhyCtrlState.validPhyRateIndex[i][j];
		}   

		if (!rcIsValidPhyRate(i, pRateTable->initialRateMax, TRUE) ||
		    !mPhyCtrlState.validPhyRateCount[i]) 
			continue;

		pRc->rateMaxPhy = mPhyCtrlState.validPhyRateIndex[i][j-1];	
	}
    
	ASSERT(pRc->rateTableSize <= MAX_TX_RATE_TBL);
	ASSERT(k <= MAX_TX_RATE_TBL);

	pRc->rateMaxPhy = pRc->validRateIndex[k-4];
	pRc->maxValidRate = k;

	rcSortValidRates(pRateTable, pRc);
}

static A_UINT8
rcRateFind_ht(struct ath_softc_tgt *sc, struct atheros_node *pSib,
	      const RATE_TABLE_11N *pRateTable, A_BOOL probeAllowed, A_BOOL *isProbing)
{
	A_UINT32             dt;
	A_UINT32             bestThruput, thisThruput;
	A_UINT32             nowMsec;
	A_UINT8              rate, nextRate, bestRate;
	A_UINT8              maxIndex, minIndex;
	A_INT8               index;
	TX_RATE_CTRL         *pRc = NULL;

	pRc = (TX_RATE_CTRL *)(pSib ? (pSib) : NULL);

	*isProbing = FALSE;

	/*
	 * Age (reduce) last ack rssi based on how old it is.
	 * The bizarre numbers are so the delta is 160msec,
	 * meaning we divide by 16.
	 *   0msec   <= dt <= 25msec:   don't derate
	 *   25msec  <= dt <= 185msec:  derate linearly from 0 to 10dB
	 *   185msec <= dt:             derate by 10dB
	 */

	nowMsec = A_MS_TICKGET();
	dt = nowMsec - pRc->rssiTime;

	/*
	 * Now look up the rate in the rssi table and return it.
	 * If no rates match then we return 0 (lowest rate)
	 */

	bestThruput = 0;
	maxIndex = pRc->maxValidRate-1;

	minIndex = 0;
	bestRate = minIndex;
    
	/*
	 * Try the higher rate first. It will reduce memory moving time
	 * if we have very good channel characteristics.
	 */
	for (index = maxIndex; index >= minIndex ; index--) {
		A_UINT8 perThres;
    
		rate = pRc->validRateIndex[index];
		if (rate > pRc->rateMaxPhy) {
			continue;
		}

		/* if the best throughput is already larger than the userRateKbps..
		 * then we could skip of rest of calculation.. 
		 */
		if( bestThruput >= pRateTable->info[rate].userRateKbps)
			break;

		/*
		 * For TCP the average collision rate is around 11%,
		 * so we ignore PERs less than this.  This is to
		 * prevent the rate we are currently using (whose
		 * PER might be in the 10-15 range because of TCP
		 * collisions) looking worse than the next lower
		 * rate whose PER has decayed close to 0.  If we
		 * used to next lower rate, its PER would grow to
		 * 10-15 and we would be worse off then staying
		 * at the current rate.
		 */
		perThres = pRc->state[rate].per;
		if ( perThres < 12 ) {
			perThres = 12;
		}

		thisThruput = pRateTable->info[rate].userRateKbps * (100 - perThres);
		if (bestThruput <= thisThruput) {
			bestThruput = thisThruput;
			bestRate    = rate;
		}
	}

	rate = bestRate;

	/*
	 * Must check the actual rate (rateKbps) to account for non-monoticity of
	 * 11g's rate table
	 */

	if (rate >= pRc->rateMaxPhy && probeAllowed) {
		rate = pRc->rateMaxPhy;

		/* Probe the next allowed phy state */
		/* FIXME: Check to make sure ratMax is checked properly */
		if (rcGetNextValidTxRate( pRateTable, pRc, rate, &nextRate) && 
		    (nowMsec - pRc->probeTime > pRateTable->probeInterval) &&
		    (pRc->hwMaxRetryPktCnt >= 1))
		{
			rate                  = nextRate;
			pRc->probeRate        = rate;
			pRc->probeTime        = nowMsec;
			pRc->hwMaxRetryPktCnt = 0;
			*isProbing            = TRUE;

		}
	}

	/*
	 * Make sure rate is not higher than the allowed maximum.
	 * We should also enforce the min, but I suspect the min is
	 * normally 1 rather than 0 because of the rate 9 vs 6 issue
	 * in the old code.
	 */
	if (rate > (pRc->rateTableSize - 1)) {
		rate = pRc->rateTableSize - 1;
	}

	/* record selected rate, which is used to decide if we want to do fast frame */
	if (!(*isProbing) && pSib) {
		pSib->lastRateKbps = pRateTable->info[rate].rateKbps;
		((struct atheros_softc*)sc->sc_rc)->currentTxRateKbps = pSib->lastRateKbps;
		((struct atheros_softc*)sc->sc_rc)->currentTxRateIndex = rate;
	}

	return rate;
}

static void
rcRateSetseries(const RATE_TABLE_11N *pRateTable ,
                struct ath_rc_series *series,
		A_UINT8 tries, A_UINT8 rix,
		A_BOOL rtsctsenable, A_UINT32 chainmask,int stbc)
{
	series->tries = tries;
	series->flags = (rtsctsenable? ATH_RC_RTSCTS_FLAG : 0) | 
		(WLAN_RC_PHY_DS(pRateTable->info[rix].phy) ? ATH_RC_DS_FLAG : 0) | 
		(WLAN_RC_PHY_40(pRateTable->info[rix].phy) ? ATH_RC_CW40_FLAG : 0) | 
		(WLAN_RC_PHY_SGI(pRateTable->info[rix].phy) ? ATH_RC_HT40_SGI_FLAG : 0);
#ifdef MAGPIE_MERLIN
	if (stbc) {
		/* For now, only single stream STBC is supported */
		if (pRateTable->info[rix].rateCode >= 0x80 && 
		    pRateTable->info[rix].rateCode <= 0x87)
		{
			series->flags |= ATH_RC_TX_STBC_FLAG;
		}
	}
#endif
	series->rix = pRateTable->info[rix].baseIndex;
	series->max4msframelen = pRateTable->info[rix].max4msframelen;
	series->txrateKbps = pRateTable->info[rix].rateKbps;

	/* If the hardware is capable of multiple transmit chains (chainmask is 3, 5 or 7), 
	 * then choose the number of transmit chains dynamically based on entries in the rate table.
	 */
#ifndef ATH_ENABLE_WLAN_FOR_K2
	if(chainmask == 7)
		series->tx_chainmask = pRateTable->info[rix].txChainMask_3ch;
	else if(chainmask == 1) 
		series->tx_chainmask = 1;
	else 
		series->tx_chainmask = pRateTable->info[rix].txChainMask_2ch;  /*Chainmask is 3 or 5*/
#else
	series->tx_chainmask = 1;
#endif
}

static A_UINT8 
rcRateGetIndex(struct ath_softc_tgt *sc, struct ath_node_target *an,        
               const RATE_TABLE_11N *pRateTable , 
               A_UINT8 rix, A_UINT16 stepDown, A_UINT16 minRate)
{
	A_UINT32                j;
	A_UINT8                 nextIndex;
	struct atheros_node     *pSib = ATH_NODE_ATHEROS(an);
	TX_RATE_CTRL            *pRc = (TX_RATE_CTRL *)(pSib);
    
	if (minRate) {
		for (j = RATE_TABLE_11N_SIZE; j > 0; j-- ) {
			if (rcGetNextLowerValidTxRate(pRateTable, pRc, rix, &nextIndex)) {
				rix = nextIndex;
			} else {
				break;
			}
		}
	} else {
		for (j = stepDown; j > 0; j-- ) {
			if (rcGetNextLowerValidTxRate(pRateTable, pRc, rix, &nextIndex)) {
				rix = nextIndex;
			} else {
				break;
			}
		}
	}

	return rix;
}

void rcForceAggrRate(struct ath_softc_tgt *sc, struct ath_node_target *an, struct ath_rc_series series[])
{
	struct atheros_softc *asc = (struct atheros_softc*)sc->sc_rc;
	RATE_TABLE_11N *pRateTable = (RATE_TABLE_11N *)asc->hwRateTable[sc->sc_curmode];
	struct atheros_node *asn = ATH_NODE_ATHEROS(an);
	A_UINT8 nrix, tries;

	// Only enable one rate, and send that frame once
	series[1].tries = series[2].tries = series[3].tries = 0;

	tries = 1; // ATH_TXMAXTRY - 1 seemed to cause unneeded retransmissions.
	nrix = 0xd; // lowest HT rate control. See ar5416Phy.c rate table.
	rcRateSetseries(pRateTable, &series[0], tries, nrix,
			FALSE, asc->tx_chainmask, asn->stbc);
}

void rcRateFind_11n(struct ath_softc_tgt *sc, struct ath_node_target *an, 
		    int numTries, int numRates, int stepDnInc,
		    unsigned int rcflag, struct ath_rc_series series[], int *isProbe)
{
	A_UINT8 i = 0; 
	A_UINT8 tryPerRate  = 0;
	struct atheros_softc *asc = (struct atheros_softc*)sc->sc_rc;
	RATE_TABLE_11N *pRateTable = (RATE_TABLE_11N *)asc->hwRateTable[sc->sc_curmode];
	struct atheros_node *asn = ATH_NODE_ATHEROS(an);
	A_UINT8 rix, nrix;
	A_UINT8 dot11Rate;
	WLAN_PHY phy;

	rix = rcRateFind_ht(sc, asn, pRateTable, (rcflag & ATH_RC_PROBE_ALLOWED) ? 1 : 0, 
			    isProbe);
	nrix = rix;

	if ((rcflag & ATH_RC_PROBE_ALLOWED) && (*isProbe)) {
		/* set one try for probe rates. For the probes don't enable rts */
		rcRateSetseries(pRateTable, &series[i++], 1, nrix,
				FALSE, asc->tx_chainmask, asn->stbc);
          
		/*
		 * Get the next tried/allowed rate. No RTS for the next series
		 * after the probe rate
		 */
		nrix = rcRateGetIndex( sc, an, pRateTable, nrix, 1, FALSE);
	}

	tryPerRate = (numTries/numRates);

	/* Set the choosen rate. No RTS for first series entry. */
	rcRateSetseries(pRateTable, &series[i++], tryPerRate,
			nrix, FALSE, asc->tx_chainmask, asn->stbc);

	/* Fill in the other rates for multirate retry */
	for (; i < numRates; i++) {
		A_UINT8 tryNum;
		A_UINT8 minRate;

		tryNum  = ((i + 1) == numRates) ? numTries - (tryPerRate * i) : tryPerRate ;
		minRate = (((i + 1) == numRates) && (rcflag & ATH_RC_MINRATE_LASTRATE)) ? 1 : 0;

		nrix = rcRateGetIndex(sc, an, pRateTable, nrix, stepDnInc, minRate);

		/* All other rates in the series have RTS enabled */
		rcRateSetseries(pRateTable, &series[i], tryNum,
				nrix, TRUE, asc->tx_chainmask, asn->stbc);
	}

	/*
	 * BUG 26545:
	 * Change rate series to enable aggregation when operating at lower MCS rates. 
	 * When first rate in series is MCS2 in HT40 @ 2.4GHz, series should look like:
	 *    {MCS2, MCS1, MCS0, MCS0}.
	 * When first rate in series is MCS3 in HT20 @ 2.4GHz, series should look like:
	 *    {MCS3, MCS2, MCS1, MCS1}
	 * So, set fourth rate in series to be same as third one for above conditions.
	 */
	if (sc->sc_curmode == IEEE80211_MODE_11NG) {
		dot11Rate = pRateTable->info[rix].dot11Rate;
		phy = pRateTable->info[rix].phy;
		if (i == 4 &&
		    ((dot11Rate == 2 && phy == WLAN_RC_PHY_HT_40_SS) || 
		     (dot11Rate == 3 && phy == WLAN_RC_PHY_HT_20_SS))) 
		{
			series[3].rix = series[2].rix;
			series[3].flags = series[2].flags;
			series[3].max4msframelen = series[2].max4msframelen;
		}
	}

	/*
	 * 2009/02/06
	 * AP91 Kite: NetGear OTA location-4 downlink.
	 *            Enable RTS/CTS at MCS 3-0 for downlink throughput.
	 */
	if (sc->sc_curmode == IEEE80211_MODE_11NG) {
		dot11Rate = pRateTable->info[rix].dot11Rate;
		if (dot11Rate <= 3 ) {
			series[0].flags |= ATH_RC_RTSCTS_FLAG;         
		}
	}
}

static void
rcUpdate_ht(struct ath_softc_tgt *sc, struct ath_node_target *an, int txRate, 
            A_BOOL Xretries, int retries, A_UINT8 curTxAnt, 
            A_UINT16 nFrames, A_UINT16 nBad)
{
	TX_RATE_CTRL *pRc;
	A_UINT32 nowMsec = A_MS_TICKGET();
	A_UINT8 lastPer;
	int rate,count;
	struct atheros_node *pSib = ATH_NODE_ATHEROS(an);
	struct atheros_softc *asc = (struct atheros_softc*)sc->sc_rc;
	RATE_TABLE_11N *pRateTable = (RATE_TABLE_11N *)asc->hwRateTable[sc->sc_curmode];

	static A_UINT32 nRetry2PerLookup[10] = {
		100 * 0 / 1,    // 0
		100 * 1 / 4,    // 25
		100 * 1 / 2,    // 50
		100 * 3 / 4,    // 75
		100 * 4 / 5,    // 80
		100 * 5 / 6,    // 83.3
		100 * 6 / 7,    // 85.7
		100 * 7 / 8,    // 87.5
		100 * 8 / 9,    // 88.8
		100 * 9 / 10    // 90
	};

	if (!pSib)
		return;

	pRc = (TX_RATE_CTRL *)(pSib);

	ASSERT(retries >= 0 && retries < MAX_TX_RETRIES);
	ASSERT(txRate >= 0);
    
	if (txRate < 0) {
		return;
	}

	lastPer = pRc->state[txRate].per;

	if (Xretries) {
		/* Update the PER. */
		if (Xretries == 1) {
			pRc->state[txRate].per += 30;
			if (pRc->state[txRate].per > 100) {
				pRc->state[txRate].per = 100;
			}
		} else {
			/* Xretries == 2 */

			count = sizeof(nRetry2PerLookup) / sizeof(nRetry2PerLookup[0]);
			if (retries >= count) {
				retries = count - 1;
			}

			/* new_PER = 7/8*old_PER + 1/8*(currentPER) */
			pRc->state[txRate].per = (A_UINT8)(pRc->state[txRate].per - 
						   (pRc->state[txRate].per / 8) + ((100) / 8));
		}

		/* Xretries == 1 or 2 */

		if (pRc->probeRate == txRate)
			pRc->probeRate = 0;
	} else {
		/* Xretries == 0 */

		/*
		 * Update the PER.  Make sure it doesn't index out of array's bounds.
		 */
		count = sizeof(nRetry2PerLookup) / sizeof(nRetry2PerLookup[0]);
		if (retries >= count) {
			retries = count - 1;
		}

		if (nBad) {
			/* new_PER = 7/8*old_PER + 1/8*(currentPER)  */
			/*
			 * Assuming that nFrames is not 0.  The current PER
			 * from the retries is 100 * retries / (retries+1),
			 * since the first retries attempts failed, and the
			 * next one worked.  For the one that worked, nBad
			 * subframes out of nFrames wored, so the PER for
			 * that part is 100 * nBad / nFrames, and it contributes
			 * 100 * nBad / (nFrames * (retries+1)) to the above
			 * PER.  The expression below is a simplified version
			 * of the sum of these two terms.
			 */
			if (nFrames > 0)
				pRc->state[txRate].per = (A_UINT8)(pRc->state[txRate].per - 
					   (pRc->state[txRate].per / 8) + 
					   ((100*(retries*nFrames + nBad)/(nFrames*(retries+1))) / 8));
		} else {
			/* new_PER = 7/8*old_PER + 1/8*(currentPER) */

			pRc->state[txRate].per = (A_UINT8)(pRc->state[txRate].per - 
				   (pRc->state[txRate].per / 8) + (nRetry2PerLookup[retries] / 8));
		}

		/*
		 * If we got at most one retry then increase the max rate if
		 * this was a probe.  Otherwise, ignore the probe.
		 */

		if (pRc->probeRate && pRc->probeRate == txRate) {
			if (retries > 0 || 2 * nBad > nFrames) {
				/*
				 * Since we probed with just a single attempt,
				 * any retries means the probe failed.  Also,
				 * if the attempt worked, but more than half
				 * the subframes were bad then also consider
				 * the probe a failure.
				 */
				pRc->probeRate = 0;
			} else {
				pRc->rateMaxPhy = pRc->probeRate;

				if (pRc->state[pRc->probeRate].per > 30) {
					pRc->state[pRc->probeRate].per = 20;
				}

				pRc->probeRate = 0;

				/*
				 * Since this probe succeeded, we allow the next probe
				 * twice as soon.  This allows the maxRate to move up
				 * faster if the probes are succesful.
				 */
				pRc->probeTime = nowMsec - pRateTable->probeInterval / 2;
			}
		}

		if (retries > 0) {
			/*
			 * Don't update anything.  We don't know if this was because
			 * of collisions or poor signal.
			 *
			 * Later: if rssiAck is close to pRc->state[txRate].rssiThres
			 * and we see lots of retries, then we could increase
			 * pRc->state[txRate].rssiThres.
			 */
			pRc->hwMaxRetryPktCnt = 0;
		} else {
			/*
			 * It worked with no retries.  First ignore bogus (small)
			 * rssiAck values.
			 */
			if (txRate == pRc->rateMaxPhy && pRc->hwMaxRetryPktCnt < 255) {
				pRc->hwMaxRetryPktCnt++;
			}

		}
	}

	/* For all cases */

	ASSERT((pRc->rateMaxPhy >= 0 && pRc->rateMaxPhy <= pRc->rateTableSize && 
		pRc->rateMaxPhy != INVALID_RATE_MAX));
    
	/*
	 * If this rate looks bad (high PER) then stop using it for
	 * a while (except if we are probing).
	 */
	if (pRc->state[txRate].per >= 55 && txRate > 0 &&
	    pRateTable->info[txRate].rateKbps <= 
            pRateTable->info[pRc->rateMaxPhy].rateKbps)
	{
		rcGetNextLowerValidTxRate(pRateTable, pRc, (A_UINT8) txRate, 
					  &pRc->rateMaxPhy);

		/* Don't probe for a little while. */
		pRc->probeTime = nowMsec;
	}

	/* Make sure the rates below this have lower PER */
	/* Monotonicity is kept only for rates below the current rate. */
	if (pRc->state[txRate].per < lastPer) {
		for (rate = txRate - 1; rate >= 0; rate--) {
			if (pRateTable->info[rate].phy != pRateTable->info[txRate].phy) {
				break;
			}

			if (pRc->state[rate].per > pRc->state[rate+1].per) {
				pRc->state[rate].per = pRc->state[rate+1].per;
			}
		}
	}

	/* Maintain monotonicity for rates above the current rate*/
	for (rate = txRate; rate < pRc->rateTableSize - 1; rate++) {
		if (pRc->state[rate+1].per < pRc->state[rate].per) {
			pRc->state[rate+1].per = pRc->state[rate].per;
		}
	}

	/* Every so often, we reduce the thresholds and PER (different for CCK and OFDM). */
	if (nowMsec - pRc->perDownTime >= pRateTable->rssiReduceInterval) {
		for (rate = 0; rate < pRc->rateTableSize; rate++) {
			pRc->state[rate].per = 7*pRc->state[rate].per/8;
		}

		pRc->perDownTime = nowMsec;
	}
}

/*
 * This routine is called by the Tx interrupt service routine to give
 * the status of previous frames.
 */
void rcUpdate_11n(struct ath_softc_tgt *sc, struct ath_node_target *an,
		  A_UINT8 curTxAnt, 
		  int finalTSIdx, int Xretries,
		  struct ath_rc_series rcs[], int nFrames, 
		  int nBad, int long_retry)
{
	A_UINT32 series = 0;
	A_UINT32 rix;
	struct atheros_softc *asc = (struct atheros_softc*)sc->sc_rc;
	RATE_TABLE_11N *pRateTable = (RATE_TABLE_11N *)asc->hwRateTable[sc->sc_curmode];
	struct atheros_node *pSib = ATH_NODE_ATHEROS(an);
	TX_RATE_CTRL *pRc = (TX_RATE_CTRL *)(pSib);
	A_UINT8 flags;

	if (!an) {
		adf_os_assert(0);
		return;
	}

	ASSERT (rcs[0].tries != 0);

	/*
	 * If the first rate is not the final index, there are intermediate rate failures
	 * to be processed.
	 */
	if (finalTSIdx != 0) {

		/* Process intermediate rates that failed.*/
		for (series = 0; series < finalTSIdx ; series++) {
			if (rcs[series].tries != 0) {
				flags = rcs[series].flags;
				/* If HT40 and we have switched mode from 40 to 20 => don't update */
				if ((flags & ATH_RC_CW40_FLAG) && 
				    (pRc->rcPhyMode != (flags & ATH_RC_CW40_FLAG))) {
					return;
				}
				if ((flags & ATH_RC_CW40_FLAG) && (flags & ATH_RC_HT40_SGI_FLAG)) {
					rix = pRateTable->info[rcs[series].rix].htIndex;
				} else if (flags & ATH_RC_HT40_SGI_FLAG) {
					rix = pRateTable->info[rcs[series].rix].sgiIndex;
				} else if (flags & ATH_RC_CW40_FLAG) {
					rix = pRateTable->info[rcs[series].rix].cw40Index;
				} else {
					rix = pRateTable->info[rcs[series].rix].baseIndex;
				}

				/* FIXME:XXXX, too many args! */
				rcUpdate_ht(sc, an, rix, Xretries? 1 : 2, rcs[series].tries, 
					    curTxAnt, nFrames, nFrames);
			}
		}
	} else {
		/*
		 * Handle the special case of MIMO PS burst, where the second aggregate is sent
		 *  out with only one rate and one try. Treating it as an excessive retry penalizes
		 * the rate inordinately.
		 */
		if (rcs[0].tries == 1 && Xretries == 1) {
			Xretries = 2;
		}
	}

	flags = rcs[series].flags;
	/* If HT40 and we have switched mode from 40 to 20 => don't update */
	if ((flags & ATH_RC_CW40_FLAG) && 
	    (pRc->rcPhyMode != (flags & ATH_RC_CW40_FLAG))) {
		return;
	}
	if ((flags & ATH_RC_CW40_FLAG) && (flags & ATH_RC_HT40_SGI_FLAG)) {
		rix = pRateTable->info[rcs[series].rix].htIndex;
	} else if (flags & ATH_RC_HT40_SGI_FLAG) {
		rix = pRateTable->info[rcs[series].rix].sgiIndex;
	} else if (flags & ATH_RC_CW40_FLAG) {
		rix = pRateTable->info[rcs[series].rix].cw40Index;
	} else {
		rix = pRateTable->info[rcs[series].rix].baseIndex;
	}

	/* FIXME:XXXX, too many args! */
	rcUpdate_ht(sc, an, rix, Xretries, long_retry, curTxAnt, 
		    nFrames, nBad);
}

void ath_tx_status_update_rate(struct ath_softc_tgt *sc,
			       struct ath_rc_series rcs[],
			       int series,
			       WMI_TXSTATUS_EVENT *txs)
{
	struct atheros_softc *asc = (struct atheros_softc*)sc->sc_rc;
	RATE_TABLE_11N *pRateTable = (RATE_TABLE_11N *)asc->hwRateTable[sc->sc_curmode];

	/* HT Rate */
	if (pRateTable->info[rcs[series].rix].rateCode & 0x80) {
		txs->txstatus[txs->cnt].ts_rate |= SM(pRateTable->info[rcs[series].rix].dot11Rate,
								       ATH9K_HTC_TXSTAT_RATE);
		txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_MCS;

		if (rcs[series].flags & ATH_RC_CW40_FLAG)
			txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_CW40;

		if (rcs[series].flags & ATH_RC_HT40_SGI_FLAG)
			txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_SGI;

	} else {
		txs->txstatus[txs->cnt].ts_rate |= SM(rcs[series].rix, ATH9K_HTC_TXSTAT_RATE);
	}

	if (rcs[series].flags & ATH_RC_RTSCTS_FLAG)
		txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_RTC_CTS;

}

struct ath_ratectrl *
ath_rate_attach(struct ath_softc_tgt *sc)
{
	struct atheros_softc *asc;

	asc = adf_os_mem_alloc(sizeof(struct atheros_softc));
	if (asc == NULL)
		return NULL;

	adf_os_mem_set(asc, 0, sizeof(struct atheros_softc));
	asc->arc.arc_space = sizeof(struct atheros_node);

	ar5416AttachRateTables(asc);

	asc->tx_chainmask = 1;
    
	return &asc->arc;
}

void
ath_rate_findrate(struct ath_softc_tgt *sc,
                  struct ath_node_target *an,
                  int shortPreamble,
                  size_t frameLen,
                  int numTries,
                  int numRates,
                  int stepDnInc,
                  unsigned int rcflag,
                  struct ath_rc_series series[],
                  int *isProbe)
{
	*isProbe = 0;

	if (!numRates || !numTries) {
		return;
	}

	ath_rate_findrate_11n(sc, an, frameLen, numTries, numRates, stepDnInc,
			      rcflag, series, isProbe);
}

#define MS(_v, _f)  (((_v) & _f) >> _f##_S)

void
ath_rate_tx_complete(struct ath_softc_tgt *sc,
		     struct ath_node_target *an,
		     struct ath_tx_desc *ds,
		     struct ath_rc_series rcs[], 
		     int nframes, int nbad)
{
	ath_rate_tx_complete_11n(sc, an, ds, rcs, nframes, nbad);
}

void
ath_rate_newassoc(struct ath_softc_tgt *sc, struct ath_node_target *an, int isnew, 
		  unsigned int capflag, struct ieee80211_rate *rs)
{
	ath_rate_newassoc_11n(sc, an, isnew, capflag, rs);
}

void ath_rate_node_update(struct ath_softc_tgt *sc,
			  struct ath_node_target *an,
			  a_int32_t isnew,
			  a_uint32_t capflag,
			  struct ieee80211_rate *rs)
{
	struct ieee80211_node_target *ni = &an->ni;

	ath_rate_newassoc(sc, ATH_NODE_TARGET(ni), isnew, capflag, rs); 
}

static int init_ath_rate_atheros(void);
static void exit_ath_rate_atheros(void);

void
ath_rate_newstate(struct ath_softc_tgt *sc,
		  struct ieee80211vap_target *vap,
		  enum ieee80211_state state,
		  a_uint32_t capflag,
		  struct ieee80211_rate *rs)
{
	struct ieee80211_node_target *ni = vap->iv_bss;
	struct atheros_softc *asc = (struct atheros_softc *) sc->sc_rc;

	asc->tx_chainmask = sc->sc_ic.ic_tx_chainmask;
	ath_rate_newassoc(sc, ATH_NODE_TARGET(ni), 1, capflag, rs);
}

static void
ath_rate_findrate_11n(struct ath_softc_tgt *sc,
		      struct ath_node_target *an,
		      size_t frameLen,
		      int numTries,
		      int numRates,
		      int stepDnInc,
		      unsigned int rcflag,
		      struct ath_rc_series series[],
		      int *isProbe)
{
	*isProbe = 0;
	if (!numRates || !numTries) {
		return;
	}

	rcRateFind_11n(sc, an, numTries, numRates, stepDnInc, rcflag, series, isProbe);
}

static void
ath_rate_tx_complete_11n(struct ath_softc_tgt *sc,
			 struct ath_node_target *an,
			 struct ath_tx_desc *ds,
			 struct ath_rc_series rcs[], 
			 int nframes, int nbad)
{
	int finalTSIdx = ds->ds_txstat.ts_rate;
	int tx_status = 0;

	if ((ds->ds_txstat.ts_status & HAL_TXERR_XRETRY) ||
	    (ds->ds_txstat.ts_status & HAL_TXERR_FIFO) || 
	    (ds->ds_txstat.ts_flags & HAL_TX_DATA_UNDERRUN) ||
	    (ds->ds_txstat.ts_flags & HAL_TX_DELIM_UNDERRUN)) {
		tx_status = 1;
	}

	rcUpdate_11n(sc, an,
		     ds->ds_txstat.ts_antenna, finalTSIdx,
		     tx_status, rcs, nframes , nbad,
		     ds->ds_txstat.ts_longretry);
}

static void
ath_rate_newassoc_11n(struct ath_softc_tgt *sc, struct ath_node_target *an, int isnew, 
		      unsigned int capflag, struct ieee80211_rate *rs)
{
	if (isnew) {
#ifdef MAGPIE_MERLIN
		struct atheros_node *oan = ATH_NODE_ATHEROS(an);
		/* Only MERLIN can send STBC */
		oan->stbc = (capflag & ATH_RC_TX_STBC_FLAG) ? 1 : 0;
#endif
		rcSibUpdate_ht(sc, an, capflag, 0, rs);
	}
}
