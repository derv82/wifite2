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
#include "ar5416.h"
#include "ar5416reg.h"
#include "ar5416desc.h"

#define N(a) (sizeof(a)/sizeof(a[0]))
#define AR_INTR_SPURIOUS 0xffffffff
#define ar5416_desc ar5416_desc_20
#define AR5416_ABORT_LOOPS 1000
#define AR5416_ABORT_WAIT  5
#define AR5416DESC         AR5416DESC_20
#define AR5416DESC_CONST   AR5416DESC_CONST_20

/*****************/
/* Attach/Detach */
/*****************/

static const struct ath_hal_private ar5416hal_10 = {{
		.ah_getRateTable        = ar5416GetRateTable,
		.ah_detach              = ar5416Detach,

		/* Transmit functions */
		.ah_updateTxTrigLevel   = ar5416UpdateTxTrigLevel,
		.ah_setTxDP             = ar5416SetTxDP,
		.ah_numTxPending        = ar5416NumTxPending,    
		.ah_startTxDma          = ar5416StartTxDma,
		.ah_stopTxDma           = ar5416StopTxDma,

		.ah_abortTxDma          = ar5416AbortTxDma,

		/* Misc Functions */
		.ah_getTsf64            = ar5416GetTsf64,
		.ah_setRxFilter         = ar5416SetRxFilter,

		/* RX Functions */
		.ah_setRxDP             = ar5416SetRxDP,
		.ah_stopDmaReceive      = ar5416StopDmaReceive,
		.ah_enableReceive       = ar5416EnableReceive,
		.ah_stopPcuReceive      = ar5416StopPcuReceive,

		/* Interrupt Functions */
		.ah_isInterruptPending   = ar5416IsInterruptPending,
		.ah_getPendingInterrupts = ar5416GetPendingInterrupts,
		.ah_setInterrupts        = ar5416SetInterrupts,
	},
};

void ar5416Detach(struct ath_hal *ah)
{
	HALASSERT(ah != AH_NULL);
	ath_hal_free(ah);
}

struct ath_hal *
ar5416Attach(HAL_SOFTC sc, adf_os_device_t dev, HAL_STATUS *status)
{
	struct ath_hal_5416 *ahp;
	struct ath_hal *ah;

	ahp = ath_hal_malloc(sizeof (struct ath_hal_5416));
	if (ahp == AH_NULL) {
		*status = HAL_ENOMEM;
		return AH_NULL;
	}
	ah = &ahp->ah_priv.h;

	OS_MEMCPY(&ahp->ah_priv, &ar5416hal_10, sizeof(struct ath_hal_private));

	ah->ah_dev = dev;
	ah->ah_sc = sc;

	ah->ah_set11nTxDesc        = ar5416Set11nTxDesc_20;
	ah->ah_set11nRateScenario  = ar5416Set11nRateScenario_20;
	ah->ah_set11nAggrFirst     = ar5416Set11nAggrFirst_20;
	ah->ah_set11nAggrMiddle    = ar5416Set11nAggrMiddle_20;
	ah->ah_set11nAggrLast      = ar5416Set11nAggrLast_20;
	ah->ah_clr11nAggr          = ar5416Clr11nAggr_20;
	ah->ah_set11nBurstDuration = ar5416Set11nBurstDuration_20;
	ah->ah_setupRxDesc         = ar5416SetupRxDesc_20;
	ah->ah_procRxDescFast      = ar5416ProcRxDescFast_20;
	ah->ah_setupTxDesc         = ar5416SetupTxDesc_20;
	ah->ah_fillTxDesc          = ar5416FillTxDesc_20;
	ah->ah_fillKeyTxDesc       = ar5416FillKeyTxDesc_20;
	ah->ah_procTxDesc          = ar5416ProcTxDesc_20;
	ah->ah_set11nVirtualMoreFrag = ar5416Set11nVirtualMoreFrag_20;

	return ah;
}

/**********************/
/* Interrupt Handling */
/**********************/

HAL_BOOL ar5416IsInterruptPending(struct ath_hal *ah)
{
	a_uint32_t host_isr =
		ioread32_mac(AR_INTR_ASYNC_CAUSE);
	/*
	 * Some platforms trigger our ISR before applying power to
	 * the card, so make sure.
	 */
	return ((host_isr != AR_INTR_SPURIOUS) && (host_isr & AR_INTR_MAC_IRQ));
}

HAL_BOOL ar5416GetPendingInterrupts(struct ath_hal *ah, HAL_INT *masked)
{
	a_uint32_t isr;
#ifndef AR9100
	HAL_BOOL fatal_int = AH_FALSE;
	a_uint32_t sync_cause;

	if (ioread32_mac(AR_INTR_ASYNC_CAUSE)
			& AR_INTR_MAC_IRQ) {
		if ((ioread32_mac(AR_RTC_STATUS)
				& AR_RTC_STATUS_M) != AR_RTC_STATUS_ON) {
			*masked = 0;
			return AH_FALSE;
		}
	} else {
		*masked = 0;
		return AH_FALSE;
	}
#endif
	isr = ioread32_mac(AR_ISR_RAC);
	if (isr == 0xffffffff) {
		*masked = 0;
		return AH_FALSE;
	}

	*masked = isr & HAL_INT_COMMON;

#ifdef AR5416_INT_MITIGATION
	if (isr & (AR_ISR_RXMINTR | AR_ISR_RXINTM)) {
		*masked |= HAL_INT_RX;
	}
	if (isr & (AR_ISR_TXMINTR | AR_ISR_TXINTM)) {
		*masked |= HAL_INT_TX;
	}
#endif

	if (isr & AR_ISR_BCNMISC) {
		a_uint32_t s2_s;

		s2_s = ioread32_mac(AR_ISR_S2_S);

		if (s2_s & AR_ISR_S2_GTT) {
			*masked |= HAL_INT_GTT;
		}

		if (s2_s & AR_ISR_S2_CST) {
			*masked |= HAL_INT_CST;
		}
	}

	if (isr & (AR_ISR_RXOK | AR_ISR_RXERR))
		*masked |= HAL_INT_RX;
	if (isr & (AR_ISR_TXOK | AR_ISR_TXDESC | AR_ISR_TXERR | AR_ISR_TXEOL)) {
		struct ath_hal_5416 *ahp = AH5416(ah);
		a_uint32_t           s0_s, s1_s;

		*masked |= HAL_INT_TX;
		s0_s = ioread32_mac(AR_ISR_S0_S);
		s1_s = ioread32_mac(AR_ISR_S1_S);
		ahp->ah_intrTxqs |= MS(s0_s, AR_ISR_S0_QCU_TXOK);
		ahp->ah_intrTxqs |= MS(s0_s, AR_ISR_S0_QCU_TXDESC);
		ahp->ah_intrTxqs |= MS(s1_s, AR_ISR_S1_QCU_TXERR);
		ahp->ah_intrTxqs |= MS(s1_s, AR_ISR_S1_QCU_TXEOL);
	}

#ifndef AR9100
	sync_cause = ioread32_mac(AR_INTR_SYNC_CAUSE);
	fatal_int = ((sync_cause != AR_INTR_SPURIOUS) &&
		     (sync_cause & (AR_INTR_SYNC_HOST1_FATAL
		      | AR_INTR_SYNC_HOST1_PERR))) ? AH_TRUE : AH_FALSE;

	if (AH_TRUE == fatal_int) {
		iowrite32_mac(AR_INTR_SYNC_CAUSE_CLR, sync_cause);
		(void) ioread32_mac(AR_INTR_SYNC_CAUSE_CLR);
	}
#endif
	return AH_TRUE;
}

HAL_INT
ar5416SetInterrupts(struct ath_hal *ah, HAL_INT ints)
{
	struct ath_hal_5416 *ahp = AH5416(ah);
	a_uint32_t omask = ahp->ah_maskReg;
	a_uint32_t mask;

	if (omask & HAL_INT_GLOBAL) {
		iowrite32_mac(AR_IER, AR_IER_DISABLE);
		(void) ioread32_mac(AR_IER);
	}

	mask = ints & HAL_INT_COMMON;
	if (ints & HAL_INT_TX) {
#ifdef AR5416_INT_MITIGATION
		mask |= AR_IMR_TXMINTR | AR_IMR_TXINTM;
#else
		mask |= AR_IMR_TXOK;
		mask |= AR_IMR_TXDESC;
#endif
		mask |= AR_IMR_TXERR;
		mask |= AR_IMR_TXEOL;
	}
	if (ints & HAL_INT_RX) {
		mask |= AR_IMR_RXERR;
#ifdef AR5416_INT_MITIGATION
		mask |=  AR_IMR_RXMINTR | AR_IMR_RXINTM;
#else
		mask |= AR_IMR_RXOK | AR_IMR_RXDESC;
#endif
	}

	if (ints & (HAL_INT_GTT | HAL_INT_CST)) {
		mask |= AR_IMR_BCNMISC;
	}

	iowrite32_mac(AR_IMR, mask);
	(void) ioread32_mac(AR_IMR);
	ahp->ah_maskReg = ints;

	/* Re-enable interrupts if they were enabled before. */
	if (ints & HAL_INT_GLOBAL) {
		iowrite32_mac(AR_IER, AR_IER_ENABLE);
		/* See explanation above... */
		(void) ioread32_mac(AR_IER);
	}

	iowrite32_mac(AR_INTR_ASYNC_ENABLE, AR_INTR_MAC_IRQ);
	iowrite32_mac(AR_INTR_ASYNC_MASK, AR_INTR_MAC_IRQ);
	iowrite32_mac(AR_INTR_SYNC_ENABLE, AR_INTR_SYNC_ALL);

	return omask;
}

/****************/
/* TSF Handling */
/****************/

#define ATH9K_HTC_MAX_TSF_READ 3

u_int64_t ar5416GetTsf64(struct ath_hal *ah)
{
	a_uint32_t tsf_lower, tsf_upper1, tsf_upper2;
	a_int32_t i;

	tsf_upper1 = ioread32_mac(AR_TSF_U32);
	for (i = 0; i < ATH9K_HTC_MAX_TSF_READ; i++) {
		tsf_lower = ioread32_mac(AR_TSF_L32);
		tsf_upper2 = ioread32_mac(AR_TSF_U32);
		if (tsf_upper2 == tsf_upper1)
			break;
		tsf_upper1 = tsf_upper2;
	}

	return (((u_int64_t)tsf_upper2 << 32) | tsf_lower);
}

/******/
/* RX */
/******/
a_uint32_t ar5416GetRxDP(struct ath_hal *ath)
{
	return ioread32_mac(AR_RXDP);
}

void ar5416SetRxDP(struct ath_hal *ah, a_uint32_t rxdp)
{
	iowrite32_mac(AR_RXDP, rxdp);
	HALASSERT(ioread32_mac(AR_RXDP) == rxdp);
}

HAL_BOOL ar5416StopDmaReceive(struct ath_hal *ah)
{
	iowrite32_mac(AR_CR, AR_CR_RXD); /* Set receive disable bit */
	if (!ath_hal_wait(ah, AR_CR, AR_CR_RXE, 0)) {
		return AH_FALSE;
	} else {
		return AH_TRUE;
	}
}

void ar5416SetRxFilter(struct ath_hal *ah, a_uint32_t bits)
{
	a_uint32_t phybits;
    
	iowrite32_mac(AR_RX_FILTER, (bits & 0xff) | AR_RX_COMPR_BAR);
	phybits = 0;
	if (bits & HAL_RX_FILTER_PHYRADAR)
		phybits |= AR_PHY_ERR_RADAR;
	if (bits & HAL_RX_FILTER_PHYERR)
		phybits |= AR_PHY_ERR_OFDM_TIMING | AR_PHY_ERR_CCK_TIMING;
	iowrite32_mac(AR_PHY_ERR, phybits);
	if (phybits) {
		iowrite32_mac(AR_RXCFG,
			     ioread32_mac(AR_RXCFG)
			     | AR_RXCFG_ZLFDMA);
	} else {
		iowrite32_mac(AR_RXCFG,
			     ioread32_mac(AR_RXCFG)
			     & ~AR_RXCFG_ZLFDMA);
	}
}

void ar5416EnableReceive(struct ath_hal *ah)
{
	iowrite32_mac(AR_CR, AR_CR_RXE);
}

void ar5416StopPcuReceive(struct ath_hal *ah)
{
	OS_REG_SET_BIT(ah, AR_DIAG_SW, AR_DIAG_RX_DIS);
}

HAL_BOOL ar5416SetupRxDesc_20(struct ath_rx_desc *ds,
			      a_uint32_t size, a_uint32_t flags)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	HALASSERT((size &~ AR_BufLen) == 0);

	ads->ds_ctl1 = size & AR_BufLen;
	if (flags & HAL_RXDESC_INTREQ)
		ads->ds_ctl1 |= AR_RxIntrReq;

	/* this should be enough */
	ads->ds_rxstatus8 &= ~AR_RxDone;

	return AH_TRUE;
}

HAL_STATUS ar5416ProcRxDescFast_20(struct ath_hal *ah, struct ath_rx_desc *ds,
				   a_uint32_t pa, struct ath_desc *nds,
				   struct ath_rx_status *rx_stats)
{
	struct ar5416_desc ads;
	struct ar5416_desc *adsp = AR5416DESC(ds);
	struct ar5416_desc *ands = AR5416DESC(nds);

	if ((adsp->ds_rxstatus8 & AR_RxDone) == 0)
		return HAL_EINPROGRESS;
	/*
	 * Given the use of a self-linked tail be very sure that the hw is
	 * done with this descriptor; the hw may have done this descriptor
	 * once and picked it up again...make sure the hw has moved on.
	 */
	if ((ands->ds_rxstatus8 & AR_RxDone) == 0
	    && ioread32_mac(AR_RXDP) == pa) {
#ifdef DEBUG_RXQUEUE
		printk("!");
#endif
		return HAL_EINPROGRESS;
	}

	/*
	 * Now we need to get the stats from the descriptor. Since desc are 
	 * uncached, lets make a copy of the stats first. Note that, since we
	 * touch most of the rx stats, a memcpy would always be more efficient
	 *
	 * Next we fill in all values in a caller passed stack variable.
	 * This reduces the number of uncached accesses.
	 * Do this copy here, after the check so that when the checks fail, we
	 * dont end up copying the entire stats uselessly.
	 */
	ads.u.rx = adsp->u.rx;

	rx_stats->rs_status = 0;
	rx_stats->rs_flags = 0;

	rx_stats->rs_datalen = ads.ds_rxstatus1 & AR_DataLen;
	rx_stats->rs_tstamp =  ads.AR_RcvTimestamp;

	/* XXX what about KeyCacheMiss? */
	rx_stats->rs_rssi_combined = 
		MS(ads.ds_rxstatus4, AR_RxRSSICombined);
	rx_stats->rs_rssi_ctl0 = MS(ads.ds_rxstatus0, AR_RxRSSIAnt00);
	rx_stats->rs_rssi_ctl1 = MS(ads.ds_rxstatus0, AR_RxRSSIAnt01);
	rx_stats->rs_rssi_ctl2 = MS(ads.ds_rxstatus0, AR_RxRSSIAnt02);
	rx_stats->rs_rssi_ext0 = MS(ads.ds_rxstatus4, AR_RxRSSIAnt10);
	rx_stats->rs_rssi_ext1 = MS(ads.ds_rxstatus4, AR_RxRSSIAnt11);
	rx_stats->rs_rssi_ext2 = MS(ads.ds_rxstatus4, AR_RxRSSIAnt12);
	if (ads.ds_rxstatus8 & AR_RxKeyIdxValid)
		rx_stats->rs_keyix = MS(ads.ds_rxstatus8, AR_KeyIdx);
	else
		rx_stats->rs_keyix = HAL_RXKEYIX_INVALID;
	/* NB: caller expected to do rate table mapping */
	rx_stats->rs_rate = RXSTATUS_RATE(ah, (&ads));
	rx_stats->rs_more = (ads.ds_rxstatus1 & AR_RxMore) ? 1 : 0;

	rx_stats->rs_isaggr = (ads.ds_rxstatus8 & AR_RxAggr) ? 1 : 0;
	rx_stats->rs_moreaggr = (ads.ds_rxstatus8 & AR_RxMoreAggr) ? 1 : 0;
	rx_stats->rs_flags  |= (ads.ds_rxstatus3 & AR_GI) ? HAL_RX_GI : 0;
	rx_stats->rs_flags  |= (ads.ds_rxstatus3 & AR_2040) ? HAL_RX_2040 : 0;

	if (ads.ds_rxstatus8 & AR_PreDelimCRCErr)
		rx_stats->rs_flags |= HAL_RX_DELIM_CRC_PRE;
	if (ads.ds_rxstatus8 & AR_PostDelimCRCErr)
		rx_stats->rs_flags |= HAL_RX_DELIM_CRC_POST;
	if (ads.ds_rxstatus8 & AR_DecryptBusyErr)
		rx_stats->rs_flags |= HAL_RX_DECRYPT_BUSY;

	if ((ads.ds_rxstatus8 & AR_RxFrameOK) == 0) {
		/*
		 * These four bits should not be set together.  The
		 * 5416 spec states a Michael error can only occur if
		 * DecryptCRCErr not set (and TKIP is used).  Experience
		 * indicates however that you can also get Michael errors
		 * when a CRC error is detected, but these are specious.
		 * Consequently we filter them out here so we don't
		 * confuse and/or complicate drivers.
		 */
		if (ads.ds_rxstatus8 & AR_CRCErr)
			rx_stats->rs_status |= HAL_RXERR_CRC;
		else if (ads.ds_rxstatus8 & AR_PHYErr) {
			a_uint32_t phyerr;

			rx_stats->rs_status |= HAL_RXERR_PHY;
			phyerr = MS(ads.ds_rxstatus8, AR_PHYErrCode);
			rx_stats->rs_phyerr = phyerr;
		} else if (ads.ds_rxstatus8 & AR_DecryptCRCErr)
			rx_stats->rs_status |= HAL_RXERR_DECRYPT;
		else if (ads.ds_rxstatus8 & AR_MichaelErr)
			rx_stats->rs_status |= HAL_RXERR_MIC;
	}
	rx_stats->evm0=ads.AR_RxEVM0;
	rx_stats->evm1=ads.AR_RxEVM1;
	rx_stats->evm2=ads.AR_RxEVM2;

	return HAL_OK;
}

/******/
/* TX */
/******/

HAL_BOOL ar5416UpdateTxTrigLevel(struct ath_hal *ah, HAL_BOOL bIncTrigLevel)
{
        struct ath_hal_5416 *ahp = AH5416(ah);
        a_uint32_t txcfg, curLevel, newLevel;
        HAL_INT omask;

        /*
         * Disable interrupts while futzing with the fifo level.
         */
        omask = ar5416SetInterrupts(ah, ahp->ah_maskReg &~ HAL_INT_GLOBAL);

	txcfg = ioread32_mac(AR_TXCFG);
        curLevel = MS(txcfg, AR_FTRIG);
        newLevel = curLevel;

        if (bIncTrigLevel)  {
		if (curLevel < MAX_TX_FIFO_THRESHOLD)
			newLevel ++;
        } else if (curLevel > MIN_TX_FIFO_THRESHOLD)
                newLevel--;
        if (newLevel != curLevel)
		iowrite32_mac(AR_TXCFG,
			     (txcfg & ~AR_FTRIG) | SM(newLevel, AR_FTRIG));

        /* re-enable chip interrupts */
        ar5416SetInterrupts(ah, omask);

        return (newLevel != curLevel);
}

a_uint32_t ar5416GetTxDP(struct ath_hal *ah, a_uint32_t q)
{
        HALASSERT(q < AH_PRIVATE(ah)->ah_caps.halTotalQueues);
        return ioread32_mac(AR_QTXDP(q));
}

HAL_BOOL ar5416SetTxDP(struct ath_hal *ah, a_uint32_t q, a_uint32_t txdp)
{
        HALASSERT(q < AH_PRIVATE(ah)->ah_caps.halTotalQueues);
        HALASSERT(AH5416(ah)->ah_txq[q].tqi_type != HAL_TX_QUEUE_INACTIVE);

        /*
         * Make sure that TXE is deasserted before setting the TXDP.  If TXE
         * is still asserted, setting TXDP will have no effect.
         */
	HALASSERT((ioread32_mac(AR_Q_TXE) & (1 << q)) == 0);

	iowrite32_mac(AR_QTXDP(q), txdp);

        return AH_TRUE;
}

HAL_BOOL ar5416StartTxDma(struct ath_hal *ah, a_uint32_t q)
{
        HALASSERT(q < AH_PRIVATE(ah)->ah_caps.halTotalQueues);
        HALASSERT(AH5416(ah)->ah_txq[q].tqi_type != HAL_TX_QUEUE_INACTIVE);

        /* Check to be sure we're not enabling a q that has its TXD bit set. */
	HALASSERT((ioread32_mac(AR_Q_TXD) & (1 << q)) == 0);

	iowrite32_mac(AR_Q_TXE, 1 << q);

        return AH_TRUE;
}

a_uint32_t ar5416NumTxPending(struct ath_hal *ah, a_uint32_t q)
{
        a_uint32_t npend;

        HALASSERT(q < AH_PRIVATE(ah)->ah_caps.halTotalQueues);
        HALASSERT(AH5416(ah)->ah_txq[q].tqi_type != HAL_TX_QUEUE_INACTIVE);

	npend = ioread32_mac(AR_QSTS(q))
		& AR_Q_STS_PEND_FR_CNT;
        if (npend == 0) {
                /*
                 * Pending frame count (PFC) can momentarily go to zero
                 * while TXE remains asserted.  In other words a PFC of
                 * zero is not sufficient to say that the queue has stopped.
                 */
		if (ioread32_mac(AR_Q_TXE) & (1 << q))
                        npend = 1;
        }
#ifdef DEBUG
        if (npend && (AH5416(ah)->ah_txq[q].tqi_type == HAL_TX_QUEUE_CAB)) {
		if (ioread32_mac(AR_Q_RDYTIMESHDN)
				& (1 << q)) {
                        isrPrintf("RTSD on CAB queue\n");
                        /* Clear the ReadyTime shutdown status bits */
			iowrite32_mac(AR_Q_RDYTIMESHDN, 1 << q);
                }
        }
#endif
        return npend;
}

HAL_BOOL ar5416AbortTxDma(struct ath_hal *ah)
{
    	a_int32_t i, q;

	/*
	 * set txd on all queues
	 */
	iowrite32_mac(AR_Q_TXD, AR_Q_TXD_M);

	/*
	 * set tx abort bits
	 */
	OS_REG_SET_BIT(ah, AR_PCU_MISC, (AR_PCU_FORCE_QUIET_COLL | AR_PCU_CLEAR_VMF));
	OS_REG_SET_BIT(ah, AR_DIAG_SW, AR_DIAG_FORCE_CH_IDLE_HIGH);
	OS_REG_SET_BIT(ah, AR_D_GBL_IFS_MISC, AR_D_GBL_IFS_MISC_IGNORE_BACKOFF);

	/*
	 * wait on all tx queues
	 */
	for (q = 0; q < AR_NUM_QCU; q++) {
		for (i = 0; i < AR5416_ABORT_LOOPS; i++) {
			if (!ar5416NumTxPending(ah, q))
				break;

			OS_DELAY(AR5416_ABORT_WAIT);
		}
		if (i == AR5416_ABORT_LOOPS) {
			return AH_FALSE;
		}
	}

	/*
	 * clear tx abort bits
	 */
	OS_REG_CLR_BIT(ah, AR_PCU_MISC, (AR_PCU_FORCE_QUIET_COLL | AR_PCU_CLEAR_VMF));
	OS_REG_CLR_BIT(ah, AR_DIAG_SW, AR_DIAG_FORCE_CH_IDLE_HIGH);
	OS_REG_CLR_BIT(ah, AR_D_GBL_IFS_MISC, AR_D_GBL_IFS_MISC_IGNORE_BACKOFF);

	/*
	 * clear txd
	 */
	iowrite32_mac(AR_Q_TXD, 0);

	return AH_TRUE;
}

HAL_BOOL ar5416StopTxDma(struct ath_hal*ah, a_uint32_t q)
{
	a_uint32_t i;
	
        HALASSERT(q < AH_PRIVATE(ah)->ah_caps.halTotalQueues);

        HALASSERT(AH5416(ah)->ah_txq[q].tqi_type != HAL_TX_QUEUE_INACTIVE);

	iowrite32_mac(AR_Q_TXD, 1 << q);
        for (i = 1000; i != 0; i--) {
                if (ar5416NumTxPending(ah, q) == 0)
                        break;
                OS_DELAY(100);        /* XXX get actual value */
        }

	iowrite32_mac(AR_Q_TXD, 0);
        return (i != 0);
}

HAL_BOOL ar5416SetupTxDesc_20(struct ath_tx_desc *ds,
			      a_uint32_t pktLen,
			      a_uint32_t hdrLen,
			      HAL_PKT_TYPE type,
			      a_uint32_t txPower,
			      a_uint32_t txRate0, a_uint32_t txTries0,
			      a_uint32_t keyIx,
			      a_uint32_t flags,
			      a_uint32_t rtsctsRate,
			      a_uint32_t rtsctsDuration)
{
#define RTSCTS  (HAL_TXDESC_RTSENA|HAL_TXDESC_CTSENA)

        struct ar5416_desc *ads = AR5416DESC(ds);

        (void) hdrLen;

        ads->ds_txstatus9 &= ~AR_TxDone;

        HALASSERT(txTries0 != 0);
        HALASSERT(isValidPktType(type));
        HALASSERT(isValidTxRate(txRate0));
        HALASSERT((flags & RTSCTS) != RTSCTS);

        if (txPower > 63)
		txPower=63;

        ads->ds_ctl0 = (pktLen & AR_FrameLen)
		| (txPower << AR_XmitPower_S)
		| (flags & HAL_TXDESC_VEOL ? AR_VEOL : 0)
		| (flags & HAL_TXDESC_CLRDMASK ? AR_ClrDestMask : 0)
		| (flags & HAL_TXDESC_INTREQ ? AR_TxIntrReq : 0);

        ads->ds_ctl1 = (type << AR_FrameType_S)
		| (flags & HAL_TXDESC_NOACK ? AR_NoAck : 0);
        ads->ds_ctl2 = SM(txTries0, AR_XmitDataTries0);
        ads->ds_ctl3 = (txRate0 << AR_XmitRate0_S);

        ads->ds_ctl7 = SM(AR5416_LEGACY_CHAINMASK, AR_ChainSel0) 
		| SM(AR5416_LEGACY_CHAINMASK, AR_ChainSel1)
		| SM(AR5416_LEGACY_CHAINMASK, AR_ChainSel2) 
		| SM(AR5416_LEGACY_CHAINMASK, AR_ChainSel3);

        if (keyIx != HAL_TXKEYIX_INVALID) {
                /* XXX validate key index */
                ads->ds_ctl1 |= SM(keyIx, AR_DestIdx);
                ads->ds_ctl0 |= AR_DestIdxValid;
        }

        if (flags & RTSCTS) {
                if (!isValidTxRate(rtsctsRate)) {
                        return AH_FALSE;
                }
                /* XXX validate rtsctsDuration */
                ads->ds_ctl0 |= (flags & HAL_TXDESC_CTSENA ? AR_CTSEnable : 0)
			| (flags & HAL_TXDESC_RTSENA ? AR_RTSEnable : 0);
                ads->ds_ctl2 |= SM(rtsctsDuration, AR_BurstDur);
                ads->ds_ctl3 |= (rtsctsRate << AR_RTSCTSRate_S);
        }
        return AH_TRUE;

#undef RTSCTS
}

HAL_BOOL ar5416FillTxDesc_20(struct ath_tx_desc *ds,
			     a_uint32_t segLen, HAL_BOOL firstSeg, HAL_BOOL lastSeg,
			     const struct ath_tx_desc *ds0)
{
        struct ar5416_desc *ads = AR5416DESC(ds);

        HALASSERT((segLen &~ AR_BufLen) == 0);

        if (firstSeg) {
                /*
                 * First descriptor, don't clobber xmit control data
                 * setup by ar5416SetupTxDesc.
                 */
                ads->ds_ctl1 |= segLen | (lastSeg ? 0 : AR_TxMore);
        } else if (lastSeg) {
                /*
                 * Last descriptor in a multi-descriptor frame,
                 * copy the multi-rate transmit parameters from
                 * the first frame for processing on completion.
                 */
                ads->ds_ctl0 = 0;
                ads->ds_ctl1 = segLen;
                ads->ds_ctl2 = AR5416DESC_CONST(ds0)->ds_ctl2;
                ads->ds_ctl3 = AR5416DESC_CONST(ds0)->ds_ctl3;
        } else {
                /*
                 * Intermediate descriptor in a multi-descriptor frame.
                 */
                ads->ds_ctl0 = 0;
                ads->ds_ctl1 = segLen | AR_TxMore;
                ads->ds_ctl2 = 0;
                ads->ds_ctl3 = 0;
        }
        ads->ds_txstatus0 = ads->ds_txstatus1 = 0;

        return AH_TRUE;
}

HAL_BOOL ar5416FillKeyTxDesc_20(struct ath_tx_desc *ds,
				HAL_KEY_TYPE keyType)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	ads->ds_ctl6 = SM(keyType, AR_EncrType);
	return AH_TRUE;
}

HAL_STATUS ar5416ProcTxDesc_20(struct ath_hal *ah, struct ath_tx_desc *gds)
{
        struct ar5416_desc *ads = AR5416DESC(gds);
        struct ath_tx_desc *ds = (struct ath_tx_desc *)gds;
        
        if ((ads->ds_txstatus9 & AR_TxDone) == 0)
                return HAL_EINPROGRESS;

        ads->ds_txstatus9 &= ~AR_TxDone;

        /* Update software copies of the HW status */
        ds->ds_txstat.ts_seqnum = MS(ads->ds_txstatus9, AR_SeqNum);
        ds->ds_txstat.ts_tstamp = ads->AR_SendTimestamp;
        ds->ds_txstat.ts_status = 0;
        ds->ds_txstat.ts_flags  = 0;

        if (ads->ds_txstatus1 & AR_ExcessiveRetries)
                ds->ds_txstat.ts_status |= HAL_TXERR_XRETRY;
        if (ads->ds_txstatus1 & AR_Filtered)
                ds->ds_txstat.ts_status |= HAL_TXERR_FILT;
        if (ads->ds_txstatus1 & AR_FIFOUnderrun)
                ds->ds_txstat.ts_status |= HAL_TXERR_FIFO;
        if (ads->ds_txstatus9 & AR_TxOpExceeded)
		ds->ds_txstat.ts_status |= HAL_TXERR_XTXOP;
        if (ads->ds_txstatus1 & AR_TxTimerExpired)
		ds->ds_txstat.ts_status |= HAL_TXERR_TIMER_EXPIRED;

        if (ads->ds_txstatus1 & AR_DescCfgErr)
		ds->ds_txstat.ts_flags |= HAL_TX_DESC_CFG_ERR;
        if (ads->ds_txstatus1 & AR_TxDataUnderrun) {
		ds->ds_txstat.ts_flags |= HAL_TX_DATA_UNDERRUN;
		ar5416UpdateTxTrigLevel(ah, AH_TRUE);
	}
        if (ads->ds_txstatus1 & AR_TxDelimUnderrun) {
		ds->ds_txstat.ts_flags |= HAL_TX_DELIM_UNDERRUN;
		ar5416UpdateTxTrigLevel(ah, AH_TRUE);
	}
        if (ads->ds_txstatus0 & AR_TxBaStatus) {
		ds->ds_txstat.ts_flags |= HAL_TX_BA;
		ds->ds_txstat.ba_low = ads->AR_BaBitmapLow;
		ds->ds_txstat.ba_high = ads->AR_BaBitmapHigh;
        }

        /*
         * Extract the transmit rate used and mark the rate as
         * ``alternate'' if it wasn't the series 0 rate.
         */
        ds->ds_txstat.ts_rate = MS(ads->ds_txstatus9, AR_FinalTxIdx);
        ds->ds_txstat.ts_rssi_combined = 
		MS(ads->ds_txstatus5, AR_TxRSSICombined);
        ds->ds_txstat.ts_rssi_ctl0 = MS(ads->ds_txstatus0, AR_TxRSSIAnt00);
        ds->ds_txstat.ts_rssi_ctl1 = MS(ads->ds_txstatus0, AR_TxRSSIAnt01);
        ds->ds_txstat.ts_rssi_ctl2 = MS(ads->ds_txstatus0, AR_TxRSSIAnt02);
        ds->ds_txstat.ts_rssi_ext0 = MS(ads->ds_txstatus5, AR_TxRSSIAnt10);
        ds->ds_txstat.ts_rssi_ext1 = MS(ads->ds_txstatus5, AR_TxRSSIAnt11);
        ds->ds_txstat.ts_rssi_ext2 = MS(ads->ds_txstatus5, AR_TxRSSIAnt12);
        ds->ds_txstat.evm0 = ads->AR_TxEVM0;
        ds->ds_txstat.evm1 = ads->AR_TxEVM1;
        ds->ds_txstat.evm2 = ads->AR_TxEVM2;
        ds->ds_txstat.ts_shortretry = MS(ads->ds_txstatus1, AR_RTSFailCnt);
        ds->ds_txstat.ts_longretry = MS(ads->ds_txstatus1, AR_DataFailCnt);
        ds->ds_txstat.ts_virtcol = MS(ads->ds_txstatus1, AR_VirtRetryCnt);
        ds->ds_txstat.ts_antenna = 0;		/* ignored for owl */

        return HAL_OK;
}

void ar5416Set11nTxDesc_20(struct ath_tx_desc *ds,
			   a_uint32_t pktLen, HAL_PKT_TYPE type, a_uint32_t txPower,
			   a_uint32_t keyIx, HAL_KEY_TYPE keyType,
			   a_uint32_t flags)
{
        struct ar5416_desc *ads = AR5416DESC(ds);

        HALASSERT(isValidPktType(type));
        HALASSERT(isValidKeyType(keyType));

	if (txPower > 63)
                txPower = 63;

        ads->ds_ctl0 = (pktLen & AR_FrameLen)
		| (flags & HAL_TXDESC_VMF ? AR_VirtMoreFrag : 0)
		| SM(txPower, AR_XmitPower)
		| (flags & HAL_TXDESC_RTSENA ? AR_RTSEnable : 0)
		| (flags & HAL_TXDESC_VEOL ? AR_VEOL : 0)
		| (flags & HAL_TXDESC_CLRDMASK ? AR_ClrDestMask : 0)
		| (flags & HAL_TXDESC_INTREQ ? AR_TxIntrReq : 0)
		| (keyIx != HAL_TXKEYIX_INVALID ? AR_DestIdxValid : 0)
		| (flags & HAL_TXDESC_CTSENA ? AR_CTSEnable : 0);

        ads->ds_ctl1 = (keyIx != HAL_TXKEYIX_INVALID ? SM(keyIx, AR_DestIdx) : 0)
		| SM(type, AR_FrameType)
		| (flags & HAL_TXDESC_NOACK ? AR_NoAck : 0)
		| (flags & HAL_TXDESC_EXT_ONLY ? AR_ExtOnly : 0)
		| (flags & HAL_TXDESC_EXT_AND_CTL ? AR_ExtAndCtl : 0);

        ads->ds_ctl6 = SM(keyType, AR_EncrType);
}

void ar5416Set11nRateScenario_20(struct ath_tx_desc *ds,
				 a_uint32_t durUpdateEn, a_uint32_t rtsctsRate,
				 HAL_11N_RATE_SERIES series[], a_uint32_t nseries,
				 a_uint32_t flags)
{
	struct ar5416_desc *ads = AR5416DESC(ds);
	a_uint32_t ds_ctl0;

	HALASSERT(nseries == 4);
	(void)nseries;

	/*
	* Rate control settings override
	*/
	ds_ctl0 = ads->ds_ctl0;

	if (flags & (HAL_TXDESC_RTSENA | HAL_TXDESC_CTSENA)) {
		if (flags & HAL_TXDESC_RTSENA) {
			ds_ctl0 &= ~AR_CTSEnable;
			ds_ctl0 |= AR_RTSEnable;
		} else {
			ds_ctl0 &= ~AR_RTSEnable;
			ds_ctl0 |= AR_CTSEnable;
		}
	} else {
		/* this line is only difference between merlin and k2
		 * Current one is for merlin */
		ds_ctl0 = (ds_ctl0 & ~(AR_RTSEnable | AR_CTSEnable));
	}

	ads->ds_ctl0 = ds_ctl0;

	ads->ds_ctl2 = set11nTries(series, 0)
				   | set11nTries(series, 1)
				   | set11nTries(series, 2)
				   | set11nTries(series, 3)
				   | (durUpdateEn ? AR_DurUpdateEn : 0);

	ads->ds_ctl3 = set11nRate(series, 0)
				   | set11nRate(series, 1)
				   | set11nRate(series, 2)
				   | set11nRate(series, 3);

	ads->ds_ctl4 = set11nPktDurRTSCTS(series, 0)
				   | set11nPktDurRTSCTS(series, 1);

	ads->ds_ctl5 = set11nPktDurRTSCTS(series, 2)
				   | set11nPktDurRTSCTS(series, 3);

	ads->ds_ctl7 = set11nRateFlags(series, 0)
				   | set11nRateFlags(series, 1)
				   | set11nRateFlags(series, 2)
				   | set11nRateFlags(series, 3)
				   | SM(rtsctsRate, AR_RTSCTSRate);
}

void ar5416Set11nAggrFirst_20(struct ath_tx_desc *ds, a_uint32_t aggrLen,
			      a_uint32_t numDelims)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	ads->ds_ctl1 |= (AR_IsAggr | AR_MoreAggr);

	ads->ds_ctl6 &= ~(AR_AggrLen | AR_PadDelim);
	ads->ds_ctl6 |= SM(aggrLen, AR_AggrLen) |
		SM(numDelims, AR_PadDelim);
}

void ar5416Set11nAggrMiddle_20(struct ath_tx_desc *ds, a_uint32_t numDelims)
{
	struct ar5416_desc *ads = AR5416DESC(ds);
	a_uint32_t ctl6;

	ads->ds_ctl1 |= (AR_IsAggr | AR_MoreAggr);

	/*
	 * We use a stack variable to manipulate ctl6 to reduce uncached 
	 * read modify, modfiy, write.
	 */
	ctl6 = ads->ds_ctl6;
	ctl6 &= ~AR_PadDelim;
	ctl6 |= SM(numDelims, AR_PadDelim);
	ads->ds_ctl6 = ctl6;
}

void ar5416Set11nAggrLast_20(struct ath_tx_desc *ds)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	ads->ds_ctl1 |= AR_IsAggr;
	ads->ds_ctl1 &= ~AR_MoreAggr;
	ads->ds_ctl6 &= ~AR_PadDelim;
}

void ar5416Clr11nAggr_20(struct ath_tx_desc *ds)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	ads->ds_ctl1 &= (~AR_IsAggr & ~AR_MoreAggr);
}

void ar5416Set11nBurstDuration_20(struct ath_tx_desc *ds,
				  a_uint32_t burstDuration)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	ads->ds_ctl2 &= ~AR_BurstDur;
	ads->ds_ctl2 |= SM(burstDuration, AR_BurstDur);
}

void ar5416Set11nVirtualMoreFrag_20(struct ath_tx_desc *ds,
				    a_uint32_t vmf)
{
	struct ar5416_desc *ads = AR5416DESC(ds);

	if (vmf) {
		ads->ds_ctl0 |= AR_VirtMoreFrag;
	} else {
		ads->ds_ctl0 &= ~AR_VirtMoreFrag;
	}
}
