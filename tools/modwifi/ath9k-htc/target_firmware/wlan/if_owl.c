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
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>
#include <adf_net_wcmd.h>

#include "if_llc.h"

#ifdef USE_HEADERLEN_RESV
#include <if_llc.h>
#endif

#include <ieee80211_var.h>
#include "if_athrate.h"
#include "if_athvar.h"
#include "ah_desc.h"

#include "modwifi.h"

#define ath_tgt_free_skb  adf_nbuf_free

#define OFDM_PLCP_BITS          22
#define HT_RC_2_MCS(_rc)        ((_rc) & 0x0f)
#define HT_RC_2_STREAMS(_rc)    ((((_rc) & 0x78) >> 3) + 1)
#define L_STF                   8
#define L_LTF                   8
#define L_SIG                   4
#define HT_SIG                  8
#define HT_STF                  4
#define HT_LTF(_ns)             (4 * (_ns))
#define SYMBOL_TIME(_ns)        ((_ns) << 2)            // ns * 4 us
#define SYMBOL_TIME_HALFGI(_ns) (((_ns) * 18 + 4) / 5)  // ns * 3.6 us

static a_uint16_t bits_per_symbol[][2] = {
	/* 20MHz 40MHz */
	{    26,   54 },     //  0: BPSK
	{    52,  108 },     //  1: QPSK 1/2
	{    78,  162 },     //  2: QPSK 3/4
	{   104,  216 },     //  3: 16-QAM 1/2
	{   156,  324 },     //  4: 16-QAM 3/4
	{   208,  432 },     //  5: 64-QAM 2/3
	{   234,  486 },     //  6: 64-QAM 3/4
	{   260,  540 },     //  7: 64-QAM 5/6
	{    52,  108 },     //  8: BPSK
	{   104,  216 },     //  9: QPSK 1/2
	{   156,  324 },     // 10: QPSK 3/4
	{   208,  432 },     // 11: 16-QAM 1/2
	{   312,  648 },     // 12: 16-QAM 3/4
	{   416,  864 },     // 13: 64-QAM 2/3
	{   468,  972 },     // 14: 64-QAM 3/4
	{   520, 1080 },     // 15: 64-QAM 5/6
};

void owltgt_tx_processq(struct ath_softc_tgt *sc, struct ath_txq *txq,
			owl_txq_state_t txqstate);
static void ath_tgt_txqaddbuf(struct ath_softc_tgt *sc, struct ath_txq *txq,
			      struct ath_tx_buf *bf,  struct ath_tx_desc *lastds);
void ath_rate_findrate_11n_Hardcoded(struct ath_softc_tgt *sc,
				     struct ath_rc_series series[]);
void ath_buf_set_rate_Hardcoded(struct ath_softc_tgt *sc,
				struct ath_tx_buf *bf) ;
static a_int32_t ath_tgt_txbuf_setup(struct ath_softc_tgt *sc,
				     struct ath_tx_buf *bf, ath_data_hdr_t *dh);
static void ath_tx_freebuf(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
static void ath_tx_uc_comp(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
static void ath_update_stats(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
void adf_print_buf(adf_nbuf_t buf);
static void ath_tgt_tx_enqueue(struct ath_txq *txq, struct ath_atx_tid  *tid);

void ath_tgt_tx_comp_aggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
struct ieee80211_frame *ATH_SKB_2_WH(adf_nbuf_t skb);

void ath_tgt_tx_send_normal(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);

static void ath_tgt_tx_sched_normal(struct ath_softc_tgt *sc, ath_atx_tid_t *tid);
static void ath_tgt_tx_sched_aggr(struct ath_softc_tgt *sc, ath_atx_tid_t *tid);

extern a_int32_t ath_chainmask_sel_logic(void *);
static a_int32_t ath_get_pktlen(struct ath_tx_buf *bf, a_int32_t hdrlen);
static void ath_tgt_txq_schedule(struct ath_softc_tgt *sc, struct ath_txq *txq);

typedef void (*ath_ft_set_atype_t)(struct ath_softc_tgt *sc, struct ath_buf *bf);

static void
ath_tx_set_retry(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);

static void
ath_bar_tx(struct ath_softc_tgt *sc, ath_atx_tid_t *tid, struct ath_tx_buf *bf);
static void
ath_tx_update_baw(ath_atx_tid_t *tid, int seqno);
static  void
ath_tx_retry_subframe(struct ath_softc_tgt *sc, struct ath_tx_buf *bf,
		      ath_tx_bufhead *bf_q, struct ath_tx_buf **bar);

static void
ath_tx_comp_aggr_error(struct ath_softc_tgt *sc, struct ath_tx_buf *bf, ath_atx_tid_t *tid);

void ath_tx_addto_baw(ath_atx_tid_t *tid, struct ath_tx_buf *bf);
static inline void ath_tx_retry_unaggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
static void ath_tx_comp_unaggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
static void ath_update_aggr_stats(struct ath_softc_tgt *sc, struct ath_tx_desc *ds,
				  int nframes, int nbad);
static inline void ath_aggr_resume_tid(struct ath_softc_tgt *sc, ath_atx_tid_t *tid);
static void ath_tx_comp_cleanup(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);

int ath_tgt_tx_add_to_aggr(struct ath_softc_tgt *sc,
			   struct ath_buf *bf,int datatype,
			   ath_atx_tid_t *tid, int is_burst);

struct ieee80211_frame *ATH_SKB_2_WH(adf_nbuf_t skb)
{
	a_uint8_t *anbdata;
	a_uint32_t anblen;

	adf_nbuf_peek_header(skb, &anbdata, &anblen);

	return((struct ieee80211_frame *)anbdata);
}

#undef adf_os_cpu_to_le16

static a_uint16_t adf_os_cpu_to_le16(a_uint16_t x)
{
	return ((((x) & 0xff00) >> 8) |   (((x) & 0x00ff) << 8));
}

static inline void
ath_aggr_resume_tid(struct ath_softc_tgt *sc, ath_atx_tid_t *tid)
{
	struct ath_txq *txq;

	txq = TID_TO_ACTXQ(tid->tidno);
	tid->paused = 0;

	if (asf_tailq_empty(&tid->buf_q))
		return;

	ath_tgt_tx_enqueue(txq, tid);
	ath_tgt_txq_schedule(sc, txq);
}

static inline void
ath_aggr_pause_tid(struct ath_softc_tgt *sc, ath_atx_tid_t *tid)
{
	tid->paused =1;
}

static a_uint32_t ath_pkt_duration(struct ath_softc_tgt *sc,
				   a_uint8_t rix, struct ath_tx_buf *bf,
				   a_int32_t width, a_int32_t half_gi)
{
	const HAL_RATE_TABLE *rt = sc->sc_currates;
	a_uint32_t nbits, nsymbits, duration, nsymbols;
	a_uint8_t rc;
	a_int32_t streams;
	a_int32_t pktlen;

	pktlen = bf->bf_isaggr ? bf->bf_al : bf->bf_pktlen;
	rc = rt->info[rix].rateCode;

	if (!IS_HT_RATE(rc))
		return ath_hal_computetxtime(sc->sc_ah, rt, pktlen, rix,
					     bf->bf_shpream);

	nbits = (pktlen << 3) + OFDM_PLCP_BITS;
	nsymbits = bits_per_symbol[HT_RC_2_MCS(rc)][width];
	nsymbols = (nbits + nsymbits - 1) / nsymbits;

	if (!half_gi)
		duration = SYMBOL_TIME(nsymbols);
	else
		duration = SYMBOL_TIME_HALFGI(nsymbols);

	streams = HT_RC_2_STREAMS(rc);
	duration += L_STF + L_LTF + L_SIG + HT_SIG + HT_STF + HT_LTF(streams);

	return duration;
}

static void ath_dma_map(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	adf_nbuf_t skb = bf->bf_skb;

	skb = adf_nbuf_queue_first(&bf->bf_skbhead);
	adf_nbuf_map(sc->sc_dev, bf->bf_dmamap, skb, ADF_OS_DMA_TO_DEVICE);
}

void ath_dma_unmap(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	adf_nbuf_t skb = bf->bf_skb;

	skb = adf_nbuf_queue_first(&bf->bf_skbhead);
	adf_nbuf_unmap( sc->sc_dev, bf->bf_dmamap, ADF_OS_DMA_TO_DEVICE);
}

void ath_filltxdesc(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_tx_desc *ds0, *ds = bf->bf_desc;
	struct ath_hal *ah = sc->sc_ah;
	a_uint8_t i;

	ds0 = ds;
	adf_nbuf_dmamap_info(bf->bf_dmamap, &bf->bf_dmamap_info);

	for (i = 0; i < bf->bf_dmamap_info.nsegs; i++, ds++) {

		ds->ds_data = bf->bf_dmamap_info.dma_segs[i].paddr;

		if (i == (bf->bf_dmamap_info.nsegs - 1)) {
			ds->ds_link = 0;
			bf->bf_lastds = ds;
		} else
			ds->ds_link = ATH_BUF_GET_DESC_PHY_ADDR_WITH_IDX(bf, i+1);

		ah->ah_fillTxDesc(ds
				   , bf->bf_dmamap_info.dma_segs[i].len
				   , i == 0
				   , i == (bf->bf_dmamap_info.nsegs - 1)
				   , ds0);
	}
}

static void ath_tx_tgt_setds(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_tx_desc *ds = bf->bf_desc;
	struct ath_hal *ah = sc->sc_ah;

	switch (bf->bf_protmode) {
    	case IEEE80211_PROT_RTSCTS:
		bf->bf_flags |= HAL_TXDESC_RTSENA;
		break;
    	case IEEE80211_PROT_CTSONLY:
		bf->bf_flags |= HAL_TXDESC_CTSENA;
		break;
    	default:
		break;
	}

	ah->ah_set11nTxDesc(ds
			      , bf->bf_pktlen
			      , bf->bf_atype
			      , 60
			      , bf->bf_keyix
			      , bf->bf_keytype
			      , bf->bf_flags | HAL_TXDESC_INTREQ);

	ath_filltxdesc(sc, bf);
}

static struct ath_tx_buf *ath_buf_toggle(struct ath_softc_tgt *sc,
				      struct ath_tx_buf *bf,
				      a_uint8_t retry)
{
	struct ath_tx_buf *tmp = NULL;
	adf_nbuf_t buf = NULL;

	adf_os_assert(sc->sc_txbuf_held != NULL);

	tmp = sc->sc_txbuf_held;

	if (retry) {
		ath_dma_unmap(sc, bf);
		adf_nbuf_queue_init(&tmp->bf_skbhead);
		buf = adf_nbuf_queue_remove(&bf->bf_skbhead);
		adf_os_assert(buf);
		adf_nbuf_queue_add(&tmp->bf_skbhead, buf);

		adf_os_assert(adf_nbuf_queue_len(&bf->bf_skbhead) == 0);

		tmp->bf_next = bf->bf_next;
		tmp->bf_endpt = bf->bf_endpt;
		tmp->bf_tidno = bf->bf_tidno;
		tmp->bf_skb = bf->bf_skb;
		tmp->bf_node = bf->bf_node;
		tmp->bf_isaggr = bf->bf_isaggr;
		tmp->bf_flags = bf->bf_flags;
		tmp->bf_state = bf->bf_state;
		tmp->bf_retries = bf->bf_retries;
		tmp->bf_comp = bf->bf_comp;
		tmp->bf_nframes = bf->bf_nframes;
		tmp->bf_cookie = bf->bf_cookie;

		bf->bf_isaggr = 0;
		bf->bf_next = NULL;
		bf->bf_skb = NULL;
		bf->bf_node = NULL;
		bf->bf_flags = 0;
		bf->bf_comp = NULL;

		bf->bf_retries = 0;
		bf->bf_nframes = 0;

		ath_dma_map(sc, tmp);
		ath_tx_tgt_setds(sc, tmp);
	}

	sc->sc_txbuf_held = bf;

	return tmp;
}

static void ath_tgt_skb_free(struct ath_softc_tgt *sc,
			     adf_nbuf_queue_t *head,
			     HTC_ENDPOINT_ID endpt)
{
	adf_nbuf_t tskb;

	while (adf_nbuf_queue_len(head) != 0) {
		tskb = adf_nbuf_queue_remove(head);
		ath_free_tx_skb(sc->tgt_htc_handle,endpt,tskb);
	}
}

static void ath_buf_comp(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	ath_dma_unmap(sc, bf);
	ath_tgt_skb_free(sc, &bf->bf_skbhead,bf->bf_endpt);
	bf->bf_skb = NULL;
	bf->bf_node = NULL;
	bf = ath_buf_toggle(sc, bf, 0);
	if (bf != NULL) {
		asf_tailq_insert_tail(&sc->sc_txbuf, bf, bf_list);
	}
}

static void ath_buf_set_rate(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
    struct ath_hal *ah = sc->sc_ah;
    const HAL_RATE_TABLE *rt;
    struct ath_tx_desc *ds = bf->bf_desc;
    HAL_11N_RATE_SERIES series[4];
    a_int32_t i, flags;
    a_uint8_t rix, cix, rtsctsrate;
    a_int32_t prot_mode = AH_FALSE;

    rt = sc->sc_currates;
    rix = bf->bf_rcs[0].rix;
    flags = (bf->bf_flags & (HAL_TXDESC_RTSENA | HAL_TXDESC_CTSENA));
    cix = rt->info[sc->sc_protrix].controlRate;

    if (bf->bf_protmode != IEEE80211_PROT_NONE &&
	(rt->info[rix].phy == IEEE80211_T_OFDM ||
	 rt->info[rix].phy == IEEE80211_T_HT) &&
	(bf->bf_flags & HAL_TXDESC_NOACK) == 0) {
	    cix = rt->info[sc->sc_protrix].controlRate;
	    prot_mode = AH_TRUE;
    } else {
	    if (ath_hal_getcapability(ah, HAL_CAP_HT) && (!bf->bf_ismcast))
		    flags = HAL_TXDESC_RTSENA;

	    for (i = 4; i--;) {
		    if (bf->bf_rcs[i].tries) {
			    cix = rt->info[bf->bf_rcs[i].rix].controlRate;
			    break;
		    }

	    }
    }

    adf_os_mem_set(series, 0, sizeof(HAL_11N_RATE_SERIES) * 4);

    for (i = 0; i < 4; i++) {
	    if (!bf->bf_rcs[i].tries)
		    continue;

	    rix = bf->bf_rcs[i].rix;

	    series[i].Rate = rt->info[rix].rateCode |
		    (bf->bf_shpream ? rt->info[rix].shortPreamble : 0);

	    series[i].Tries = bf->bf_rcs[i].tries;
#ifdef MAGPIE_MERLIN
	    series[i].RateFlags = ((bf->bf_rcs[i].flags & ATH_RC_RTSCTS_FLAG) ?
				   HAL_RATESERIES_RTS_CTS : 0 ) |
		    ((bf->bf_rcs[i].flags & ATH_RC_CW40_FLAG) ?
		     HAL_RATESERIES_2040 : 0 ) |
		    ((bf->bf_rcs[i].flags & ATH_RC_HT40_SGI_FLAG) ?
		     HAL_RATESERIES_HALFGI : 0 ) |
		    ((bf->bf_rcs[i].flags & ATH_RC_TX_STBC_FLAG) ?
		     HAL_RATESERIES_STBC: 0);
#else
	    series[i].RateFlags = ((bf->bf_rcs[i].flags & ATH_RC_RTSCTS_FLAG) ?
				   HAL_RATESERIES_RTS_CTS : 0 ) |
		    ((bf->bf_rcs[i].flags & ATH_RC_CW40_FLAG) ?
		     HAL_RATESERIES_2040 : 0 ) |
		    ((bf->bf_rcs[i].flags & ATH_RC_HT40_SGI_FLAG) ?
		     HAL_RATESERIES_HALFGI : 0 );
#endif
	    series[i].PktDuration = ath_pkt_duration(sc, rix, bf,
				     (bf->bf_rcs[i].flags & ATH_RC_CW40_FLAG) != 0,
				     (bf->bf_rcs[i].flags & ATH_RC_HT40_SGI_FLAG));

	    series[i].ChSel = sc->sc_ic.ic_tx_chainmask;

	    if (prot_mode)
		    series[i].RateFlags |= HAL_RATESERIES_RTS_CTS;

	    if (bf->bf_rcs[i].flags & ATH_RC_DS_FLAG)
		    series[i].RateFlags |= HAL_RATESERIES_RTS_CTS;
    }

    rtsctsrate = rt->info[cix].rateCode |
	    (bf->bf_shpream ? rt->info[cix].shortPreamble : 0);

    ah->ah_set11nRateScenario(ds, 1,
				rtsctsrate,
				series, 4,
				flags);
}

static void ath_tgt_rate_findrate(struct ath_softc_tgt *sc,
				  struct ath_node_target *an,
				  a_int32_t shortPreamble,
				  size_t frameLen,
				  a_int32_t numTries,
				  a_int32_t numRates,
				  a_int32_t stepDnInc,
				  a_uint32_t rcflag,
				  struct ath_rc_series series[],
				  a_int32_t *isProbe)
{
	ath_rate_findrate(sc, an, 1, frameLen, 10, 4, 1,
			  ATH_RC_PROBE_ALLOWED, series, isProbe);
}

static void owl_tgt_tid_init(struct ath_atx_tid *tid)
{
	int i;

	tid->seq_start  = tid->seq_next = 0;
	tid->baw_size   = WME_MAX_BA;
	tid->baw_head   = tid->baw_tail = 0;
	tid->paused     = 0;
	tid->flag       = 0;
	tid->sched      = AH_FALSE;

	asf_tailq_init(&tid->buf_q);

	for (i = 0; i < ATH_TID_MAX_BUFS; i++) {
		TX_BUF_BITMAP_CLR(tid->tx_buf_bitmap, i);
	}
}

static void owl_tgt_tid_cleanup(struct ath_softc_tgt *sc,
				struct ath_atx_tid *tid)
{
	tid->incomp--;
	if (tid->incomp) {
		return;
	}

	tid->flag &= ~TID_CLEANUP_INPROGRES;

	if (tid->flag & TID_REINITIALIZE) {
		adf_os_print("TID REINIT DONE for tid %p\n", tid);
		tid->flag  &= ~TID_REINITIALIZE;
		owl_tgt_tid_init(tid);
	} else {
		ath_aggr_resume_tid(sc, tid);
	}
}

void owl_tgt_node_init(struct ath_node_target * an)
{
	struct ath_atx_tid *tid;
	int tidno;

	for (tidno = 0, tid = &an->tid[tidno]; tidno < WME_NUM_TID;tidno++, tid++) {
		tid->tidno = tidno;
		tid->an = an;

		if ( tid->flag & TID_CLEANUP_INPROGRES ) {
			tid->flag |= TID_REINITIALIZE;
			adf_os_print("tid[%p]->incomp is not 0: %d\n",
				     tid, tid->incomp);
		} else {
			owl_tgt_tid_init(tid);
		}
	}
}

void ath_tx_status_clear(struct ath_softc_tgt *sc)
{
	int i;

	for (i = 0; i < 2; i++) {
		sc->tx_status[i].cnt = 0;
	}
}

static WMI_TXSTATUS_EVENT *ath_tx_status_get(struct ath_softc_tgt *sc)
{
	WMI_TXSTATUS_EVENT *txs = NULL;
	int i;

	for (i = 0; i < 2; i++) {
		if (sc->tx_status[i].cnt < HTC_MAX_TX_STATUS) {
			txs = &sc->tx_status[i];
			break;
		}
	}

	return txs;
}

void ath_tx_status_update(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_tx_desc *ds = bf->bf_lastds;
	WMI_TXSTATUS_EVENT *txs;

	if (sc->sc_tx_draining)
		return;

	txs = ath_tx_status_get(sc);
	if (txs == NULL)
		return;

	txs->txstatus[txs->cnt].ts_flags = 0;

	txs->txstatus[txs->cnt].cookie = bf->bf_cookie;
	txs->txstatus[txs->cnt].ts_rate = SM(bf->bf_endpt, ATH9K_HTC_TXSTAT_EPID);

	if (ds->ds_txstat.ts_status & HAL_TXERR_FILT)
		txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_FILT;

	if (!(ds->ds_txstat.ts_status & HAL_TXERR_XRETRY) &&
	    !(ds->ds_txstat.ts_status & HAL_TXERR_FIFO) &&
	    !(ds->ds_txstat.ts_status & HAL_TXERR_TIMER_EXPIRED) &&
	    !(ds->ds_txstat.ts_status & HAL_TXERR_FILT))
		txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_ACK;

	ath_tx_status_update_rate(sc, bf->bf_rcs, ds->ds_txstat.ts_rate, txs);

	txs->cnt++;
}

void ath_tx_status_update_aggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf,
			       struct ath_tx_desc *ds, struct ath_rc_series rcs[],
			       int txok)
{
	WMI_TXSTATUS_EVENT *txs;

	if (sc->sc_tx_draining)
		return;

	txs = ath_tx_status_get(sc);
	if (txs == NULL)
		return;

	txs->txstatus[txs->cnt].cookie = bf->bf_cookie;
	txs->txstatus[txs->cnt].ts_rate = SM(bf->bf_endpt, ATH9K_HTC_TXSTAT_EPID);

	if (txok)
		txs->txstatus[txs->cnt].ts_flags |= ATH9K_HTC_TXSTAT_ACK;

	if (rcs)
		ath_tx_status_update_rate(sc, rcs, ds->ds_txstat.ts_rate, txs);

	txs->cnt++;
}

void ath_tx_status_send(struct ath_softc_tgt *sc)
{
	int i;

	if (sc->sc_tx_draining)
		return;

	for (i = 0; i < 2; i++) {
		if (sc->tx_status[i].cnt) {
			wmi_event(sc->tgt_wmi_handle, WMI_TXSTATUS_EVENTID,
				  &sc->tx_status[i], sizeof(WMI_TXSTATUS_EVENT));
			/* FIXME: Handle failures. */
			sc->tx_status[i].cnt = 0;
		}
	}
}

static void owltgt_tx_process_cabq(struct ath_softc_tgt *sc, struct ath_txq *txq)
{
	struct ath_hal *ah = sc->sc_ah;
	ah->ah_setInterrupts(ah, sc->sc_imask & ~HAL_INT_SWBA);
	owltgt_tx_processq(sc, txq, OWL_TXQ_ACTIVE);
	ah->ah_setInterrupts(ah, sc->sc_imask);
}

void owl_tgt_tx_tasklet(TQUEUE_ARG data)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)data;
	a_int32_t i;
	struct ath_txq *txq;

	ath_tx_status_clear(sc);

	for (i = 0; i < (HAL_NUM_TX_QUEUES - 6); i++) {
		txq = ATH_TXQ(sc, i);

		if (ATH_TXQ_SETUP(sc, i)) {
			if (txq == sc->sc_cabq)
				owltgt_tx_process_cabq(sc, txq);
			else
				owltgt_tx_processq(sc, txq, OWL_TXQ_ACTIVE);
		}
	}

	ath_tx_status_send(sc);
}

void owltgt_tx_processq(struct ath_softc_tgt *sc, struct ath_txq *txq,
			owl_txq_state_t txqstate)
{
	struct ath_tx_buf *bf;
	struct ath_tx_desc *ds;
	struct ath_hal *ah = sc->sc_ah;
	HAL_STATUS status;

	for (;;) {
		if (asf_tailq_empty(&txq->axq_q)) {
			txq->axq_link = NULL;
			txq->axq_linkbuf = NULL;
			break;
		}

		bf = asf_tailq_first(&txq->axq_q);

		ds = bf->bf_lastds;
		status = ah->ah_procTxDesc(ah, ds);

		if (status == HAL_EINPROGRESS) {
			if (txqstate == OWL_TXQ_ACTIVE)
				break;
			else if (txqstate == OWL_TXQ_STOPPED) {
				__stats(sc, tx_stopfiltered);
				ds->ds_txstat.ts_flags  = 0;
				ds->ds_txstat.ts_status = HAL_OK;
			} else {
				ds->ds_txstat.ts_flags  = HAL_TX_SW_FILTERED;
			}
		}

		ATH_TXQ_REMOVE_HEAD(txq, bf, bf_list);
		if ((asf_tailq_empty(&txq->axq_q))) {
			__stats(sc, tx_qnull);
			txq->axq_link = NULL;
			txq->axq_linkbuf = NULL;
		}

		if (bf->bf_comp) {
			bf->bf_comp(sc, bf);
		} else {
			ath_tx_status_update(sc, bf);
			ath_buf_comp(sc, bf);
		}

		if (txqstate == OWL_TXQ_ACTIVE) {
			ath_tgt_txq_schedule(sc, txq);
		}
	}
}

static struct ieee80211_frame* ATH_SKB2_WH(adf_nbuf_t skb)
{
	a_uint8_t *anbdata;
	a_uint32_t anblen;

	adf_nbuf_peek_header(skb, &anbdata, &anblen);
	return((struct ieee80211_frame *)anbdata);
}

void
ath_tgt_tid_drain(struct ath_softc_tgt *sc, struct ath_atx_tid *tid)
{
	struct ath_tx_buf *bf;

	while (!asf_tailq_empty(&tid->buf_q)) {
		TAILQ_DEQ(&tid->buf_q, bf, bf_list);
		ath_tx_freebuf(sc, bf);
	}

	tid->seq_next = tid->seq_start;
	tid->baw_tail = tid->baw_head;
}

static void ath_tgt_tx_comp_normal(struct ath_softc_tgt *sc,
				   struct ath_tx_buf *bf)
{
	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);

	if (tid->flag & TID_CLEANUP_INPROGRES) {
		owl_tgt_tid_cleanup(sc, tid);
	}

	if (bf->bf_node) {
		ath_tx_uc_comp(sc, bf);
	}

	ath_tx_freebuf(sc, bf);
}

static struct ieee80211_node_target * ath_tgt_find_node(struct ath_softc_tgt *sc,
							a_int32_t node_index)
{
	struct ath_node_target *an;
	struct ieee80211_node_target *ni;

	if (node_index > TARGET_NODE_MAX)
	  	return NULL;

	an = &sc->sc_sta[node_index];
	ni = &an->ni;

	if (an->an_valid) {
		if (ni->ni_vap == NULL) {
			return NULL;
		}
		return  ni;
      	}

	return NULL;
}

static struct ath_tx_buf* ath_tx_buf_alloc(struct ath_softc_tgt *sc)
{
	struct ath_tx_buf *bf = NULL;

	bf = asf_tailq_first(&sc->sc_txbuf);
	if (bf !=  NULL) {
		adf_os_mem_set(&bf->bf_state, 0, sizeof(struct ath_buf_state));
		asf_tailq_remove(&sc->sc_txbuf, bf, bf_list);
	} else {
		adf_os_assert(0);
	}

	return  bf;
}

struct ath_tx_buf* ath_tgt_tx_prepare(struct ath_softc_tgt *sc,
				   adf_nbuf_t skb, ath_data_hdr_t *dh)
{
	struct ath_tx_buf *bf;
	struct ieee80211_node_target *ni;
	struct ath_atx_tid *tid;

	ni = ath_tgt_find_node(sc, dh->ni_index);
	if (ni == NULL)
		return NULL;

	tid = ATH_AN_2_TID(ATH_NODE_TARGET(ni), dh->tidno);
	if (tid->flag & TID_REINITIALIZE) {
		adf_os_print("drop frame due to TID reinit\n");
		return NULL;
	}

	bf = ath_tx_buf_alloc(sc);
	if (!bf) {
		__stats(sc, tx_nobufs);
		return NULL;
	}

	bf->bf_tidno = dh->tidno;
	bf->bf_txq = TID_TO_ACTXQ(bf->bf_tidno);
	bf->bf_keytype = dh->keytype;
	bf->bf_keyix = dh->keyix;
	bf->bf_protmode = dh->flags & (IEEE80211_PROT_RTSCTS | IEEE80211_PROT_CTSONLY);
	bf->bf_node = ni;

	adf_nbuf_queue_add(&bf->bf_skbhead, skb);
	skb = adf_nbuf_queue_first(&(bf->bf_skbhead));

	if (adf_nbuf_queue_len(&(bf->bf_skbhead)) == 0) {
		__stats(sc, tx_noskbs);
		return NULL;
	}

	adf_os_assert(skb);

	bf->bf_skb = skb;

	ath_tgt_txbuf_setup(sc, bf, dh);
	ath_dma_map(sc, bf);
	ath_tx_tgt_setds(sc, bf);

	return bf;
}

static void ath_tgt_tx_seqno_normal(struct ath_tx_buf *bf)
{
	struct ieee80211_node_target *ni = bf->bf_node;
	struct ath_node_target *an = ATH_NODE_TARGET(ni);
	struct ieee80211_frame *wh = ATH_SKB_2_WH(bf->bf_skb);
	struct ath_atx_tid *tid = ATH_AN_2_TID(an, bf->bf_tidno);

	u_int8_t fragno = (wh->i_seq[0] & 0xf);

	INCR(ni->ni_txseqmgmt, IEEE80211_SEQ_MAX);

	bf->bf_seqno = (tid->seq_next << IEEE80211_SEQ_SEQ_SHIFT);

	*(u_int16_t *)wh->i_seq = adf_os_cpu_to_le16(bf->bf_seqno);
	wh->i_seq[0] |= fragno;

	if (!(wh->i_fc[1] & IEEE80211_FC1_MORE_FRAG))
		INCR(tid->seq_next, IEEE80211_SEQ_MAX);
}

static a_int32_t ath_key_setup(struct ieee80211_node_target *ni,
			       struct ath_tx_buf *bf)
{
	struct ieee80211_frame *wh = ATH_SKB_2_WH(bf->bf_skb);

	if (!(wh->i_fc[1] & IEEE80211_FC1_WEP)) {
		bf->bf_keytype = HAL_KEY_TYPE_CLEAR;
		bf->bf_keyix = HAL_TXKEYIX_INVALID;
		return 0;
	}

	switch (bf->bf_keytype) {
	case HAL_KEY_TYPE_WEP:
		bf->bf_pktlen += IEEE80211_WEP_ICVLEN;
		break;
	case HAL_KEY_TYPE_AES:
		bf->bf_pktlen += IEEE80211_WEP_MICLEN;
		break;
	case HAL_KEY_TYPE_TKIP:
		bf->bf_pktlen += IEEE80211_WEP_ICVLEN;
		break;
	default:
		break;
	}

	if (bf->bf_keytype == HAL_KEY_TYPE_AES ||
	    bf->bf_keytype == HAL_KEY_TYPE_TKIP)
		ieee80211_tgt_crypto_encap(wh, ni, bf->bf_keytype);

	return 0;
}

static void ath_tgt_txq_add_ucast(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_hal *ah = sc->sc_ah;
	struct ath_txq *txq;
	HAL_STATUS status;
	volatile a_int32_t txe_val;

	adf_os_assert(bf);

	txq = bf->bf_txq;

	status = ah->ah_procTxDesc(ah, bf->bf_lastds);

	ATH_TXQ_INSERT_TAIL(txq, bf, bf_list);

	if (txq->axq_link == NULL) {
		ah->ah_setTxDP(ah, txq->axq_qnum, ATH_BUF_GET_DESC_PHY_ADDR(bf));
	} else {
		*txq->axq_link = ATH_BUF_GET_DESC_PHY_ADDR(bf);

		txe_val = ioread32_mac(0x0840);
		if (!(txe_val & (1<< txq->axq_qnum)))
			ah->ah_setTxDP(ah, txq->axq_qnum, ATH_BUF_GET_DESC_PHY_ADDR(bf));
	}

	txq->axq_link = &bf->bf_lastds->ds_link;
	ah->ah_startTxDma(ah, txq->axq_qnum);
}

static a_int32_t ath_tgt_txbuf_setup(struct ath_softc_tgt *sc,
				     struct ath_tx_buf *bf,
				     ath_data_hdr_t *dh)

{
	struct ieee80211_frame *wh = ATH_SKB2_WH(bf->bf_skb);
	a_int32_t retval;
	a_uint32_t flags = adf_os_ntohl(dh->flags);

	ath_tgt_tx_seqno_normal(bf);

	bf->bf_txq_add  = ath_tgt_txq_add_ucast;
	bf->bf_hdrlen   = ieee80211_anyhdrsize(wh);
	bf->bf_pktlen   = ath_get_pktlen(bf, bf->bf_hdrlen);
	bf->bf_ismcast  = IEEE80211_IS_MULTICAST(wh->i_addr1);

	if ((retval = ath_key_setup(bf->bf_node, bf)) < 0)
		return retval;

	if (flags & ATH_SHORT_PREAMBLE)
		bf->bf_shpream = AH_TRUE;
	else
		bf->bf_shpream = AH_FALSE;

	if (flags & ATH_HTC_TX_NO_ACK) {
		printk("NoAck1\n");
		bf->bf_flags |= HAL_TXDESC_NOACK;
	}


	bf->bf_flags = HAL_TXDESC_CLRDMASK;
	bf->bf_atype = HAL_PKT_TYPE_NORMAL;

	return 0;
}

static a_int32_t
ath_get_pktlen(struct ath_tx_buf *bf, a_int32_t hdrlen)
{
	adf_nbuf_t skb = bf->bf_skb;
	a_int32_t pktlen;

	skb = adf_nbuf_queue_first(&bf->bf_skbhead);
	pktlen = adf_nbuf_len(skb);

	pktlen -= (hdrlen & 3);
	pktlen += IEEE80211_CRC_LEN;

	return pktlen;
}

void
ath_tgt_tx_send_normal(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	struct ath_rc_series rcs[4];
	struct ath_rc_series mrcs[4];
	a_int32_t shortPreamble = 0;
	a_int32_t isProbe = 0;

	adf_os_mem_set(rcs, 0, sizeof(struct ath_rc_series)*4 );
	adf_os_mem_set(mrcs, 0, sizeof(struct ath_rc_series)*4 );

	if (!bf->bf_ismcast) {
		ath_tgt_rate_findrate(sc, an, shortPreamble,
				      0, 0, 0, 0, 0,
				      rcs, &isProbe);
		ath_hal_memcpy(bf->bf_rcs, rcs, sizeof(rcs));
	} else {
		mrcs[1].tries = mrcs[2].tries = mrcs[3].tries = 0;
		mrcs[1].rix = mrcs[2].rix = mrcs[3].rix = 0;
		mrcs[0].rix   = 0;
		mrcs[0].tries = 1;
		mrcs[0].flags = 0;
		ath_hal_memcpy(bf->bf_rcs, mrcs, sizeof(mrcs));
	}

	ath_buf_set_rate(sc, bf);
	bf->bf_txq_add(sc, bf);
}

void ath_tx_freedesc(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	bf->bf_skb = NULL;
	bf->bf_comp = NULL;
	bf->bf_node = NULL;
	bf->bf_next = NULL;
	bf = ath_buf_toggle(sc, bf, 0);
	bf->bf_retries = 0;
	bf->bf_isretried = 0;

	if (bf != NULL)
		asf_tailq_insert_tail(&sc->sc_txbuf, bf, bf_list);
}

static void ath_tx_freebuf(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	a_int32_t i ;
	struct ath_tx_desc *bfd = NULL;
	struct ath_hal *ah = sc->sc_ah;

	for (bfd = bf->bf_desc, i = 0; i < bf->bf_dmamap_info.nsegs; bfd++, i++) {
		ah->ah_clr11nAggr(bfd);
		ah->ah_set11nBurstDuration(bfd, 0);
		ah->ah_set11nVirtualMoreFrag(bfd, 0);
	}

	ath_dma_unmap(sc, bf);
	ath_tgt_skb_free(sc, &bf->bf_skbhead,bf->bf_endpt);
	ath_tx_freedesc(sc, bf);
}

static void
ath_tx_uc_comp(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	ath_tx_status_update(sc, bf);
	ath_update_stats(sc, bf);
	ath_rate_tx_complete(sc, ATH_NODE_TARGET(bf->bf_node),
			     bf->bf_lastds, bf->bf_rcs, 1, 0);
}

static void
ath_update_stats(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_tx_desc *ds = bf->bf_desc;
	u_int32_t sr, lr;

	if (ds->ds_txstat.ts_status == 0) {
		if (ds->ds_txstat.ts_rate & HAL_TXSTAT_ALTRATE)
			sc->sc_tx_stats.ast_tx_altrate++;
	} else {
		if (ds->ds_txstat.ts_status & HAL_TXERR_XRETRY)
			sc->sc_tx_stats.ast_tx_xretries++;
		if (ds->ds_txstat.ts_status & HAL_TXERR_FIFO)
			sc->sc_tx_stats.ast_tx_fifoerr++;
		if (ds->ds_txstat.ts_status & HAL_TXERR_FILT)
			sc->sc_tx_stats.ast_tx_filtered++;
		if (ds->ds_txstat.ts_status & HAL_TXERR_TIMER_EXPIRED)
			sc->sc_tx_stats.ast_tx_timer_exp++;
	}
	sr = ds->ds_txstat.ts_shortretry;
	lr = ds->ds_txstat.ts_longretry;
	sc->sc_tx_stats.ast_tx_shortretry += sr;
	sc->sc_tx_stats.ast_tx_longretry += lr;
}

void
ath_tgt_send_mgt(struct ath_softc_tgt *sc,adf_nbuf_t hdr_buf, adf_nbuf_t skb,
		 HTC_ENDPOINT_ID endpt)
{
	struct ieee80211_node_target *ni;
	struct ieee80211vap_target *vap;
	struct ath_vap_target *avp;
	struct ath_hal *ah = sc->sc_ah;
	a_uint8_t rix, txrate, ctsrate, cix = 0xff, *data;
	a_uint32_t subtype, flags, ctsduration;
	a_int32_t i, iswep, ismcast, hdrlen, pktlen, try0, len;
	struct ath_tx_desc *ds=NULL;
	struct ath_txq *txq=NULL;
	struct ath_tx_buf *bf;
	HAL_PKT_TYPE atype;
	const HAL_RATE_TABLE *rt;
	HAL_BOOL shortPreamble;
	struct ieee80211_frame *wh;
	struct ath_rc_series rcs[4];
	HAL_11N_RATE_SERIES series[4];
	ath_mgt_hdr_t *mh;
	a_int8_t keyix;

	if (!hdr_buf) {
		adf_nbuf_peek_header(skb, &data, &len);
		adf_nbuf_pull_head(skb, sizeof(ath_mgt_hdr_t));
	} else {
		adf_nbuf_peek_header(hdr_buf, &data, &len);
	}

	adf_os_assert(len >= sizeof(ath_mgt_hdr_t));

	mh = (ath_mgt_hdr_t *)data;
	adf_nbuf_peek_header(skb, &data, &len);
	wh = (struct ieee80211_frame *)data;

	adf_os_mem_set(rcs, 0, sizeof(struct ath_rc_series)*4);
	adf_os_mem_set(series, 0, sizeof(HAL_11N_RATE_SERIES)*4);

	bf = asf_tailq_first(&sc->sc_txbuf);
	if (!bf)
		goto fail;

	asf_tailq_remove(&sc->sc_txbuf, bf, bf_list);

	ni = ath_tgt_find_node(sc, mh->ni_index);
	if (!ni)
		goto fail;

	bf->bf_endpt = endpt;
	bf->bf_cookie = mh->cookie;
	bf->bf_protmode = mh->flags & (IEEE80211_PROT_RTSCTS | IEEE80211_PROT_CTSONLY);
	txq = &sc->sc_txq[1];
	iswep = wh->i_fc[1] & IEEE80211_FC1_WEP;
	ismcast = IEEE80211_IS_MULTICAST(wh->i_addr1);
	hdrlen = ieee80211_anyhdrsize(wh);
	pktlen = len;
	keyix = HAL_TXKEYIX_INVALID;
	pktlen -= (hdrlen & 3);
	pktlen += IEEE80211_CRC_LEN;

	if (iswep)
		keyix = mh->keyix;

	adf_nbuf_map(sc->sc_dev, bf->bf_dmamap, skb, ADF_OS_DMA_TO_DEVICE);

	bf->bf_skb = skb;
	adf_nbuf_queue_add(&bf->bf_skbhead, skb);

	ds = bf->bf_desc;
	rt = sc->sc_currates;
	adf_os_assert(rt != NULL);

	if (mh->flags == ATH_SHORT_PREAMBLE)
		shortPreamble = AH_TRUE;
	else
		shortPreamble = AH_FALSE;

	flags = HAL_TXDESC_CLRDMASK;
	if (mh->flags & ATH_HTC_TX_NO_ACK) {
		printk("NoAck2\n");
		flags |= HAL_TXDESC_NOACK;
	}

	switch (wh->i_fc[0] & IEEE80211_FC0_TYPE_MASK) {
	case IEEE80211_FC0_TYPE_MGT:
		subtype = wh->i_fc[0] & IEEE80211_FC0_SUBTYPE_MASK;

		if (subtype == IEEE80211_FC0_SUBTYPE_PROBE_RESP)
			atype = HAL_PKT_TYPE_PROBE_RESP;
		else if (subtype == IEEE80211_FC0_SUBTYPE_ATIM)
			atype = HAL_PKT_TYPE_ATIM;
		else
			atype = HAL_PKT_TYPE_NORMAL;

		break;
	default:
		atype = HAL_PKT_TYPE_NORMAL;
		break;
	}

	avp = &sc->sc_vap[mh->vap_index];

	rcs[0].rix = ath_get_minrateidx(sc, avp);
	rcs[0].tries = ATH_TXMAXTRY;
	rcs[0].flags = 0;

	adf_os_mem_copy(bf->bf_rcs, rcs, sizeof(rcs));
	rix = rcs[0].rix;
	try0 = rcs[0].tries;
	txrate = rt->info[rix].rateCode;

	if (shortPreamble){
		txrate |= rt->info[rix].shortPreamble;
	}

	vap = ni->ni_vap;
	bf->bf_node = ni;

	if (ismcast) {
		flags |= HAL_TXDESC_NOACK;
		try0 = 1;
	} else if (pktlen > vap->iv_rtsthreshold) {
		flags |= HAL_TXDESC_RTSENA;
		cix = rt->info[rix].controlRate;
	}

	if ((bf->bf_protmode != IEEE80211_PROT_NONE) &&
	    rt->info[rix].phy == IEEE80211_T_OFDM &&
	    (flags & HAL_TXDESC_NOACK) == 0) {
		cix = rt->info[sc->sc_protrix].controlRate;
		sc->sc_tx_stats.ast_tx_protect++;
	}

	if (mh->flags & ATH_HTC_TX_ASSIGN_SEQ)
	{
		*(a_uint16_t *)&wh->i_seq[0] =  adf_os_cpu_to_le16(ni->ni_txseqmgmt <<
							   IEEE80211_SEQ_SEQ_SHIFT);
		INCR(ni->ni_txseqmgmt, IEEE80211_SEQ_MAX);
	}
	else
	{
		// PS-Poll frames don't have sequence numbers, so WiFi chip won't touch them
		atype = HAL_PKT_TYPE_PSPOLL;
	}

	ctsduration = 0;
	if (flags & (HAL_TXDESC_RTSENA|HAL_TXDESC_CTSENA)) {
		adf_os_assert(cix != 0xff);
		ctsrate = rt->info[cix].rateCode;
		if (shortPreamble) {
			ctsrate |= rt->info[cix].shortPreamble;
			if (flags & HAL_TXDESC_RTSENA)      /* SIFS + CTS */
				ctsduration += rt->info[cix].spAckDuration;
			if ((flags & HAL_TXDESC_NOACK) == 0)    /* SIFS + ACK */
				ctsduration += rt->info[cix].spAckDuration;
		} else {
			if (flags & HAL_TXDESC_RTSENA)      /* SIFS + CTS */
				ctsduration += rt->info[cix].lpAckDuration;
			if ((flags & HAL_TXDESC_NOACK) == 0)    /* SIFS + ACK */
				ctsduration += rt->info[cix].lpAckDuration;
		}
		ctsduration += ath_hal_computetxtime(ah,
						     rt, pktlen, rix, shortPreamble);
		try0 = 1;
	} else
		ctsrate = 0;

	flags |= HAL_TXDESC_INTREQ;

	ah->ah_setupTxDesc(ds
			    , pktlen
			    , hdrlen
			    , atype
			    , 60
			    , txrate, try0
			    , keyix
			    , flags
			    , ctsrate
			    , ctsduration);

	bf->bf_flags = flags;

	/*
	 * Set key type in tx desc while sending the encrypted challenge to AP
	 * in Auth frame 3 of Shared Authentication, owl needs this.
	 */
	if (iswep && (keyix != HAL_TXKEYIX_INVALID) &&
			(wh->i_fc[0] & IEEE80211_FC0_SUBTYPE_MASK) == IEEE80211_FC0_SUBTYPE_AUTH)
		ah->ah_fillKeyTxDesc(ds, mh->keytype);

	ath_filltxdesc(sc, bf);

	for (i=0; i<4; i++) {
		series[i].Tries = 2;
		series[i].Rate = txrate;
		series[i].ChSel = sc->sc_ic.ic_tx_chainmask;
		series[i].RateFlags = 0;
	}
	ah->ah_set11nRateScenario(ds, 0, ctsrate, series, 4, 0);
	ath_tgt_txqaddbuf(sc, txq, bf, bf->bf_lastds);

	return;
fail:
	HTC_ReturnBuffers(sc->tgt_htc_handle, endpt, skb);
	return;
}

static void
ath_tgt_txqaddbuf(struct ath_softc_tgt *sc,
		  struct ath_txq *txq, struct ath_tx_buf *bf,
		  struct ath_tx_desc *lastds)
{
	struct ath_hal *ah = sc->sc_ah;

	ATH_TXQ_INSERT_TAIL(txq, bf, bf_list);

	if (txq->axq_link == NULL) {
		ah->ah_setTxDP(ah, txq->axq_qnum, ATH_BUF_GET_DESC_PHY_ADDR(bf));
	} else {
		*txq->axq_link = ATH_BUF_GET_DESC_PHY_ADDR(bf);
	}

	txq->axq_link = &lastds->ds_link;
	ah->ah_startTxDma(ah, txq->axq_qnum);
}

void ath_tgt_handle_normal(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	ath_atx_tid_t *tid;
	struct ath_node_target *an;

	an = (struct ath_node_target *)bf->bf_node;
	adf_os_assert(an);

	tid = &an->tid[bf->bf_tidno];
	adf_os_assert(tid);

	bf->bf_comp = ath_tgt_tx_comp_normal;
	INCR(tid->seq_start, IEEE80211_SEQ_MAX);
	ath_tgt_tx_send_normal(sc, bf);
}

static void
ath_tgt_tx_enqueue(struct ath_txq *txq, struct ath_atx_tid  *tid)
{
	if (tid->paused)
		return;

	if (tid->sched)
		return;

	tid->sched = AH_TRUE;
	asf_tailq_insert_tail(&txq->axq_tidq, tid, tid_qelem);
}

static void
ath_tgt_txq_schedule(struct ath_softc_tgt *sc, struct ath_txq *txq)
{
	struct ath_atx_tid  *tid;
	struct ath_tx_buf *bf;
	u_int8_t bdone;

	bdone = AH_FALSE;

	do {
		TAILQ_DEQ(&txq->axq_tidq, tid, tid_qelem);

		if (tid == NULL)
			return;

		PRINTK_AMPDU("txq_s aggr=");
		PRINTK_AMPDU(itox(!!(tid->flag & TID_AGGR_ENABLED)));
		PRINTK_AMPDU("\n");

		tid->sched = AH_FALSE;

		if (tid->paused)
			continue;

		bf = asf_tailq_first(&tid->buf_q);

		if (!(tid->flag & TID_AGGR_ENABLED) && !modwifi_txampdu_check(bf->bf_skb, NULL))
			ath_tgt_tx_sched_normal(sc,tid);
		else
			ath_tgt_tx_sched_aggr(sc,tid);

		bdone = AH_TRUE;

		if (!asf_tailq_empty(&tid->buf_q)) {
			ath_tgt_tx_enqueue(txq, tid);
		}

	} while (!asf_tailq_empty(&txq->axq_tidq) && !bdone);
}

void
ath_tgt_handle_aggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	ath_atx_tid_t *tid;
	struct ath_node_target *an;
	struct ath_txq *txq = bf->bf_txq;
	a_bool_t queue_frame, within_baw;

	an = (struct ath_node_target *)bf->bf_node;
	adf_os_assert(an);

	tid = &an->tid[bf->bf_tidno];
	adf_os_assert(tid);

	bf->bf_comp = ath_tgt_tx_comp_aggr;

	within_baw = BAW_WITHIN(tid->seq_start, tid->baw_size,
				SEQNO_FROM_BF_SEQNO(bf->bf_seqno));

	queue_frame = ( (txq->axq_depth >= ATH_AGGR_MIN_QDEPTH) ||
			(!asf_tailq_empty(&tid->buf_q)) ||
			(tid->paused) || (!within_baw) );

	// If the next frame is marked to be injected as A-MPDU,
	// then we force queueing it so it's later send as A-MPDU.
	if (modwifi_txampdu_check(bf->bf_skb, NULL)) {
		queue_frame = 1;
		PRINTK_AMPDU("handle_aggr: force\n");
	}

	if (queue_frame) {
		asf_tailq_insert_tail(&tid->buf_q, bf, bf_list);
		ath_tgt_tx_enqueue(txq, tid);
	} else {
		PRINTK_AMPDU("handle_aggr: send normal\n");
		ath_tx_addto_baw(tid, bf);
		__stats(sc, txaggr_nframes);
		ath_tgt_tx_send_normal(sc, bf);
	}

	// Only start if all the frames are here
	if (modwifi_txampdu_check(bf->bf_skb, NULL))
		ath_aggr_resume_tid(sc, tid);
}

static void
ath_tgt_tx_sched_normal(struct ath_softc_tgt *sc, ath_atx_tid_t *tid)
{
	struct ath_tx_buf *bf;
	struct ath_txq *txq =TID_TO_ACTXQ(tid->tidno);;

	do {
		if (asf_tailq_empty(&tid->buf_q))
			break;

		bf = asf_tailq_first(&tid->buf_q);
		if (modwifi_txampdu_check(bf->bf_skb, NULL))
			break;

		asf_tailq_remove(&tid->buf_q, bf, bf_list);
		ath_tgt_tx_send_normal(sc, bf);

	} while (txq->axq_depth < ATH_AGGR_MIN_QDEPTH);
}

static void
ath_tgt_tx_sched_aggr(struct ath_softc_tgt *sc, ath_atx_tid_t *tid)
{
	struct ath_tx_buf  *bf, *bf_last;
	ATH_AGGR_STATUS status;
	ath_tx_bufhead bf_q;
	struct ath_txq *txq = TID_TO_ACTXQ(tid->tidno);
	struct ath_tx_desc *ds = NULL;
	struct ath_hal *ah = sc->sc_ah;
	u_int8_t first_is_ampdu = 0;
	int i = 0;

#ifdef DEBUG_INJECT_AMPDU
	asf_tailq_foreach(bf, &tid->buf_q, bf_list) {
		i++;
	}
	printk("sched_aggr pending=");
	printk(itox(i));
	printk("\n");
#endif

	if (asf_tailq_empty(&tid->buf_q))
		return;

	do {
		if (asf_tailq_empty(&tid->buf_q))
			break;

		bf = asf_tailq_first(&tid->buf_q);
		/**
		 * Are all frames that we are supposed to aggregate in the queue?
		 * That is, is the ending frame in the queue?
		 */
		if (!modwifi_ampdu_ready(bf, &first_is_ampdu)) {
			PRINTK_AMPDU("sched_aggr !ready\n");
			return;
		}

		asf_tailq_init(&bf_q);

		/**
		 * NetBSD also first check if it's within the Block Ack window.
		 */
		status = ath_tgt_tx_form_aggr(sc, tid, &bf_q);

		if (asf_tailq_empty(&bf_q))
			break;

		bf = asf_tailq_first(&bf_q);
		bf_last = asf_tailq_last(&bf_q, ath_tx_bufhead_s);

		// If it's a single frame send as a non-aggregate
		if (bf->bf_nframes == 1 && !first_is_ampdu) {
			PRINTK_AMPDU(" tx_non-aggr");

			if(bf->bf_retries == 0)
				__stats(sc, txaggr_single);
			bf->bf_isaggr = 0;
			bf->bf_lastds = &(bf->bf_descarr[bf->bf_dmamap_info.nsegs -1]);
			bf->bf_lastds->ds_link = 0;
			bf->bf_next = NULL;

			for(ds = bf->bf_desc; ds <= bf->bf_lastds; ds++)
				ah->ah_clr11nAggr(ds);

			ath_buf_set_rate(sc, bf);
			bf->bf_txq_add(sc, bf);

			continue;
		}

		PRINTK_AMPDU("  tx aggr num=");
		PRINTK_AMPDU(itox(bf->bf_nframes));
		PRINTK_AMPDU("\n");

		bf_last->bf_next = NULL;
		bf_last->bf_lastds->ds_link = 0;
		bf_last->bf_ndelim = 0;

		bf->bf_isaggr  = 1;
		ath_buf_set_rate(sc, bf);
		ah->ah_set11nAggrFirst(bf->bf_desc, bf->bf_al,
					  bf->bf_ndelim);
		bf->bf_lastds = bf_last->bf_lastds;

		for (i = 0; i < bf_last->bf_dmamap_info.nsegs; i++)
			ah->ah_set11nAggrLast(&bf_last->bf_descarr[i]);

		if (status == ATH_AGGR_8K_LIMITED) {
			adf_os_assert(0);
			break;
		}

		bf->bf_txq_add(sc, bf);
	} while (txq->axq_depth < ATH_AGGR_MIN_QDEPTH &&
		 status != ATH_TGT_AGGR_BAW_CLOSED);
}

static u_int32_t ath_lookup_rate(struct ath_softc_tgt *sc,
				 struct ath_node_target *an,
				 struct ath_tx_buf *bf)
{
	int i, prate;
	u_int32_t max4msframelen, frame_length;
	u_int16_t aggr_limit, legacy=0;
	const HAL_RATE_TABLE  *rt = sc->sc_currates;
	struct ieee80211_node_target *ieee_node = (struct ieee80211_node_target *)an;

	if (bf->bf_ismcast) {
		bf->bf_rcs[1].tries = bf->bf_rcs[2].tries = bf->bf_rcs[3].tries = 0;
		bf->bf_rcs[0].rix   = 0xb;
		bf->bf_rcs[0].tries = ATH_TXMAXTRY - 1;
		bf->bf_rcs[0].flags = 0;
	} else {
		// This eventually goes to `rcRateFind_11n`. This fills in bf->bf_rcs.
		ath_tgt_rate_findrate(sc, an, AH_TRUE, 0, ATH_TXMAXTRY-1, 4, 1,
				      ATH_RC_PROBE_ALLOWED, bf->bf_rcs, &prate);
	}

	if (modwifi_txampdu_check(bf->bf_skb, NULL)) {
		// We must set a HT rate, because only those are aggregated.
		PRINTK_AMPDU("    force HT rate\n");
		rcForceAggrRate(sc, an, bf->bf_rcs);
		prate = 0;
	}

	max4msframelen = IEEE80211_AMPDU_LIMIT_MAX;

	for (i = 0; i < 4; i++) {
		if (bf->bf_rcs[i].tries) {
			frame_length = bf->bf_rcs[i].max4msframelen;

			if (rt->info[bf->bf_rcs[i].rix].phy != IEEE80211_T_HT) {
				legacy = 1;
				break;
			}

			max4msframelen = ATH_MIN(max4msframelen, frame_length);
		}
	}

	if (prate || legacy)
		return 0;

	if (sc->sc_ic.ic_enable_coex)
		aggr_limit = ATH_MIN((max4msframelen*3)/8, sc->sc_ic.ic_ampdu_limit);
	else
		aggr_limit = ATH_MIN(max4msframelen, sc->sc_ic.ic_ampdu_limit);

	if (ieee_node->ni_maxampdu)
		aggr_limit = ATH_MIN(aggr_limit, ieee_node->ni_maxampdu);

	return aggr_limit;
}

int modwifi_txampdu_check(adf_nbuf_t skb, u_int8_t *last_frag)
{
	a_uint8_t *data, *magic_end;
	a_int32_t len;

	adf_nbuf_peek_header(skb, &data, &len);
	if (len < 5) return 0;

	magic_end = data + len - 4;
	if (magic_end[0] != 'A' ||
	    magic_end[1] != 'G' ||
	    magic_end[2] != 'G' ||
	    magic_end[3] != 'R')
		return 0;

	if (last_frag != NULL)
		*last_frag = magic_end[-1];

	return 1;
}

int modwifi_ampdu_strip(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	adf_nbuf_trim_tail(bf->bf_skb, 5);
	bf->bf_pktlen -= 5;

	ath_tx_tgt_setds(sc, bf);
}

int modwifi_ampdu_ready(struct ath_tx_buf *bf, u_int8_t *first_is_ampdu)
{
	// All other frames are considered ready
	if (!modwifi_txampdu_check(bf->bf_skb, NULL)) {
		if (first_is_ampdu)
			*first_is_ampdu = 0;
		return 1;
	}

	if (first_is_ampdu)
		*first_is_ampdu = 1;

	// If we find an ending frame, which may be the first and only
	// frame, we are ready.
	while (bf != NULL) {
		u_int8_t last_frag = 0;

		if (!modwifi_txampdu_check(bf->bf_skb, &last_frag))
			return 1;
		if (last_frag)
			return 1;

		bf = asf_tailq_next(bf, bf_list);
	}

	// Otherwise we are not ready
	return 0;
}

int ath_tgt_tx_form_aggr(struct ath_softc_tgt *sc, ath_atx_tid_t *tid,
			 ath_tx_bufhead *bf_q)
{
	struct ath_tx_buf *bf_first ,*bf_prev = NULL;
	int nframes = 0, rl = 0;;
	struct ath_tx_desc *ds = NULL;
	struct ath_tx_buf *bf;
	struct ath_hal *ah = sc->sc_ah;
	u_int16_t aggr_limit =  (64*1024 -1), al = 0, bpad = 0, al_delta;
	u_int16_t h_baw = tid->baw_size/2, prev_al = 0, prev_frames = 0;
	u_int8_t txampdu_first = 0, txampdu_last_frag = 0, txampdu = 0, txampdu_done = 0;

	bf_first = asf_tailq_first(&tid->buf_q);
	txampdu_first = modwifi_txampdu_check(bf_first->bf_skb, NULL);

#ifdef DEBUG_INJECT_AMPDU
	if (txampdu_first)
		printk("   AGGR_FIRST\n");
#endif

	do {
		bf = asf_tailq_first(&tid->buf_q);
		adf_os_assert(bf);

		if (!BAW_WITHIN(tid->seq_start, tid->baw_size,
				SEQNO_FROM_BF_SEQNO(bf->bf_seqno))) {
			PRINTK_AMPDU("  BAW_CLOSED\n");
			bf_first->bf_al= al;
			bf_first->bf_nframes = nframes;
			return ATH_TGT_AGGR_BAW_CLOSED;
		}

		/**
		 * From FreeBSD: "Do a rate control lookup on the first frame in the
		 * list. The rate control code needs that to occur before it can
		 * determine whether to TX. It's inaccurate because the rate control
		 * code doesn't really "do" aggregate lookups, so it only considers
		 * the size of the first frame."
		 */
		if (!rl) {
			aggr_limit = ath_lookup_rate(sc, tid->an, bf);
			rl = 1;
			PRINTK_AMPDU("   aggr_limit=");
			PRINTK_AMPDU(itox(aggr_limit));
			PRINTK_AMPDU("\n");
		}

		// Handle force A-MPDU flags
		txampdu = modwifi_txampdu_check(bf->bf_skb, &txampdu_last_frag);
		if ( (!txampdu_first && txampdu) ||  // next frame is start of requested A-AMPDU
		     (txampdu_first && !txampdu) ) { // next frame is unexpected normal frame
			PRINTK_AMPDU("   AGGR_NEXT|UNEXP\n");
			bf_first->bf_al= al;
			bf_first->bf_nframes = nframes;
			return ATH_TGT_AGGR_LIMITED;
		} else if (txampdu_first && txampdu_last_frag) {
			// Include last subframe into the A-AMPDU, and then stop
			txampdu_done = 1;
		}

		// Strip the extra tailer of requested A-MPDU frames, and don't
		// try to retransmit these individual subframes.
		if (txampdu) {
			bf->bf_retries = OWLMAX_RETRIES;
			modwifi_ampdu_strip(sc, bf);
		}

		al_delta = ATH_AGGR_DELIM_SZ + bf->bf_pktlen;

		if (nframes && (aggr_limit < (al + bpad + al_delta + prev_al))) {
			PRINTK_AMPDU("  AGGR_LIMIT1\n");
			bf_first->bf_al= al;
			bf_first->bf_nframes = nframes;
			return ATH_TGT_AGGR_LIMITED;
		}

#ifdef PROJECT_K2
		if ((nframes + prev_frames) >= ATH_MIN((h_baw), 17)) {
#else
		if ((nframes + prev_frames) >= ATH_MIN((h_baw), 22)) {
#endif
			PRINTK_AMPDU("  AGGR_LIMIT2\n");
			bf_first->bf_al= al;
			bf_first->bf_nframes = nframes;
			return ATH_TGT_AGGR_LIMITED;
		}

		ath_tx_addto_baw(tid, bf);
		asf_tailq_remove(&tid->buf_q, bf, bf_list);
		asf_tailq_insert_tail(bf_q, bf, bf_list);
		nframes ++;

		adf_os_assert(bf);

		adf_os_assert(bf->bf_comp == ath_tgt_tx_comp_aggr);

		al += bpad + al_delta;
		bf->bf_ndelim = ATH_AGGR_GET_NDELIM(bf->bf_pktlen);

		switch (bf->bf_keytype) {
		case HAL_KEY_TYPE_AES:
			bf->bf_ndelim += ATH_AGGR_ENCRYPTDELIM;
			break;
		case HAL_KEY_TYPE_WEP:
		case HAL_KEY_TYPE_TKIP:
			bf->bf_ndelim += 64;
			break;
		case HAL_KEY_TYPE_WAPI:
			bf->bf_ndelim += 12;
			break;
		default:
			break;
		}

		bpad = PADBYTES(al_delta) + (bf->bf_ndelim << 2);

		if (bf_prev) {
			bf_prev->bf_next = bf;
			bf_prev->bf_lastds->ds_link = ATH_BUF_GET_DESC_PHY_ADDR(bf);
		}
		bf_prev = bf;

		for(ds = bf->bf_desc; ds <= bf->bf_lastds; ds++)
			ah->ah_set11nAggrMiddle(ds, bf->bf_ndelim);

#ifdef DEBUG_INJECT_AMPDU
		if (txampdu_done)
			printk("   AGGR_DONE\n");
#endif

	} while (!asf_tailq_empty(&tid->buf_q) && !txampdu_done);

	bf_first->bf_al= al;
	bf_first->bf_nframes = nframes;

	return ATH_TGT_AGGR_DONE;
}

void ath_tx_addto_baw(ath_atx_tid_t *tid, struct ath_tx_buf *bf)
{
	int index, cindex;

	if (bf->bf_isretried) {
		return;
	}

	index  = ATH_BA_INDEX(tid->seq_start, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
	cindex = (tid->baw_head + index) & (ATH_TID_MAX_BUFS - 1);

	TX_BUF_BITMAP_SET(tid->tx_buf_bitmap, cindex);

	if (index >= ((tid->baw_tail - tid->baw_head) & (ATH_TID_MAX_BUFS - 1))) {
		tid->baw_tail = cindex;
		INCR(tid->baw_tail, ATH_TID_MAX_BUFS);
	}
}

void ath_tgt_tx_comp_aggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);
	struct ath_tx_desc lastds;
	struct ath_tx_desc *ds = &lastds;
	struct ath_rc_series rcs[4];
	u_int16_t seq_st;
	u_int32_t *ba;
	int ba_index;
	int nbad = 0;
	int nframes = bf->bf_nframes;
	struct ath_tx_buf *bf_next;
	ath_tx_bufhead bf_q;
	int tx_ok = 1;
	struct ath_tx_buf *bar = NULL;
	struct ath_txq *txq;

	txq = bf->bf_txq;

	if (tid->flag & TID_CLEANUP_INPROGRES) {
		ath_tx_comp_cleanup(sc, bf);
		return;
	}

	adf_os_mem_copy(ds, bf->bf_lastds, sizeof (struct ath_tx_desc));
	adf_os_mem_copy(rcs, bf->bf_rcs, sizeof(rcs));

	if (ds->ds_txstat.ts_flags == HAL_TX_SW_FILTERED) {
		adf_os_assert(0);
		return;
	}

	if (!bf->bf_isaggr) {
		ath_tx_comp_unaggr(sc, bf);
		return;
	}

	__stats(sc, tx_compaggr);

	asf_tailq_init(&bf_q);

	seq_st =  ATH_DS_BA_SEQ(ds);
	ba     =  ATH_DS_BA_BITMAP(ds);
	tx_ok  =  (ATH_DS_TX_STATUS(ds) == HAL_OK);

	if (ATH_DS_TX_STATUS(ds) & HAL_TXERR_XRETRY) {
		ath_tx_comp_aggr_error(sc, bf, tid);
		return;
	}

	if (tx_ok && !ATH_DS_TX_BA(ds)) {
		__stats(sc, txaggr_babug);
		adf_os_print("BA Bug?\n");
		ath_tx_comp_aggr_error(sc, bf, tid);
		return;
	}

	while (bf) {
		ba_index = ATH_BA_INDEX(seq_st, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
		bf_next  = bf->bf_next;

		if (tx_ok && ATH_BA_ISSET(ba, ba_index)) {
			__stats(sc, txaggr_compgood);
			ath_tx_update_baw(tid, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
			ath_tx_status_update_aggr(sc, bf, ds, rcs, 1);
			ath_tx_freebuf(sc, bf);
		} else {
			PRINTK_AMPDU("comp_aggr: retry\n");
			ath_tx_retry_subframe(sc, bf, &bf_q, &bar);
			nbad ++;
		}
		bf = bf_next;
	}

	ath_update_aggr_stats(sc, ds, nframes, nbad);
	ath_rate_tx_complete(sc, an, ds, rcs, nframes, nbad);

	if (bar) {
		ath_bar_tx(sc, tid, bar);
	}

	if (!asf_tailq_empty(&bf_q)) {
		__stats(sc, txaggr_prepends);
		TAILQ_INSERTQ_HEAD(&tid->buf_q, &bf_q, bf_list);
		ath_tgt_tx_enqueue(txq, tid);
		PRINTK_AMPDU("comp_aggr: tx_enqueue\n");
	}
}

static void
ath_tx_comp_aggr_error(struct ath_softc_tgt *sc, struct ath_tx_buf *bf,
		       ath_atx_tid_t *tid)
{


	struct ath_tx_desc lastds;
	struct ath_tx_desc *ds = &lastds;
	struct ath_rc_series rcs[4];
	struct ath_tx_buf *bar = NULL;
	struct ath_tx_buf *bf_next;
	int nframes = bf->bf_nframes;
	ath_tx_bufhead bf_q;
	struct ath_txq *txq;

	asf_tailq_init(&bf_q);
	txq = bf->bf_txq;

	adf_os_mem_copy(ds, bf->bf_lastds, sizeof (struct ath_tx_desc));
	adf_os_mem_copy(rcs, bf->bf_rcs, sizeof(rcs));

	while (bf) {
		PRINTK_AMPDU("aggr_err retry\n");
		bf_next = bf->bf_next;
		ath_tx_retry_subframe(sc, bf, &bf_q, &bar);
		bf = bf_next;
	}

	ath_update_aggr_stats(sc, ds, nframes, nframes);
	ath_rate_tx_complete(sc, tid->an, ds, rcs, nframes, nframes);

	if (bar) {
		ath_bar_tx(sc, tid, bar);
	}

	if (!asf_tailq_empty(&bf_q)) {
		__stats(sc, txaggr_prepends);
		TAILQ_INSERTQ_HEAD(&tid->buf_q, &bf_q, bf_list);
		ath_tgt_tx_enqueue(txq, tid);
	}
}

static void
ath_tx_comp_cleanup(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{

	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);
	struct ath_tx_desc lastds;
	struct ath_tx_desc *ds = &lastds;
	struct ath_rc_series rcs[4];
	u_int16_t seq_st;
	u_int32_t *ba;
	int ba_index;
	int nbad = 0;
	int nframes = bf->bf_nframes;
	struct ath_tx_buf *bf_next;
	int tx_ok = 1;

	adf_os_mem_copy(ds, bf->bf_lastds, sizeof (struct ath_tx_desc));
	adf_os_mem_copy(rcs, bf->bf_rcs, sizeof(rcs));

	seq_st = ATH_DS_BA_SEQ(ds);
	ba     = ATH_DS_BA_BITMAP(ds);
	tx_ok  = (ATH_DS_TX_STATUS(ds) == HAL_OK);

	if (!bf->bf_isaggr) {
		ath_update_stats(sc, bf);

		__stats(sc, tx_compunaggr);

		ath_tx_status_update(sc, bf);

		ath_tx_freebuf(sc, bf);

		if (tid->flag & TID_CLEANUP_INPROGRES) {
			owl_tgt_tid_cleanup(sc, tid);

		}

		return;
	}

	while (bf) {
		ba_index = ATH_BA_INDEX(seq_st, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
		bf_next  = bf->bf_next;

		ath_tx_status_update_aggr(sc, bf, ds, rcs, 0);

		ath_tx_freebuf(sc, bf);

		tid->incomp--;
		if (!tid->incomp) {
			tid->flag  &= ~TID_CLEANUP_INPROGRES;
			ath_aggr_resume_tid(sc, tid);
			break;
		}

		bf = bf_next;
	}

	ath_update_aggr_stats(sc, ds, nframes, nbad);
	ath_rate_tx_complete(sc, an, ds, rcs, nframes, nbad);
}

static void
ath_tx_retry_subframe(struct ath_softc_tgt *sc, struct ath_tx_buf *bf,
		      ath_tx_bufhead *bf_q, struct ath_tx_buf **bar)
{

	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);
	struct ath_tx_desc *ds = NULL;
	struct ath_hal *ah = sc->sc_ah;
	int i = 0;

	__stats(sc, txaggr_compretries);

	for(ds = bf->bf_desc, i = 0; i < bf->bf_dmamap_info.nsegs; ds++, i++) {
		ah->ah_clr11nAggr(ds);
		ah->ah_set11nBurstDuration(ds, 0);
		ah->ah_set11nVirtualMoreFrag(ds, 0);
	}

	if (bf->bf_retries >= OWLMAX_RETRIES) {
		__stats(sc, txaggr_xretries);
		ath_tx_update_baw(tid, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
		ath_tx_status_update_aggr(sc, bf, bf->bf_lastds, NULL, 0);

		if (!*bar)
			*bar = bf;
		else
			ath_tx_freebuf(sc, bf);
		return;
	}

	if (!bf->bf_next) {
		__stats(sc, txaggr_errlast);
		bf = ath_buf_toggle(sc, bf, 1);
	} else
		bf->bf_lastds = &(bf->bf_descarr[bf->bf_dmamap_info.nsegs - 1]);

	ath_tx_set_retry(sc, bf);
	asf_tailq_insert_tail(bf_q, bf, bf_list);
}

static void
ath_update_aggr_stats(struct ath_softc_tgt *sc,
		      struct ath_tx_desc *ds, int nframes,
		      int nbad)
{

	u_int8_t status = ATH_DS_TX_STATUS(ds);
	u_int8_t txflags = ATH_DS_TX_FLAGS(ds);

	__statsn(sc, txaggr_longretries, ds->ds_txstat.ts_longretry);
	__statsn(sc, txaggr_shortretries, ds->ds_txstat.ts_shortretry);

	if (txflags & HAL_TX_DESC_CFG_ERR)
		__stats(sc, txaggr_desc_cfgerr);

	if (txflags & HAL_TX_DATA_UNDERRUN)
		__stats(sc, txaggr_data_urun);

	if (txflags & HAL_TX_DELIM_UNDERRUN)
		__stats(sc, txaggr_delim_urun);

	if (!status) {
		return;
	}

	if (status & HAL_TXERR_XRETRY)
		__stats(sc, txaggr_compxretry);

	if (status & HAL_TXERR_FILT)
		__stats(sc, txaggr_filtered);

	if (status & HAL_TXERR_FIFO)
		__stats(sc, txaggr_fifo);

	if (status & HAL_TXERR_XTXOP)
		__stats(sc, txaggr_xtxop);

	if (status & HAL_TXERR_TIMER_EXPIRED)
		__stats(sc, txaggr_timer_exp);
}

static void
ath_tx_comp_unaggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);
	struct ath_tx_desc *ds  = bf->bf_lastds;

	ath_update_stats(sc, bf);
	ath_rate_tx_complete(sc, an, ds, bf->bf_rcs, 1, 0);

	if (ATH_DS_TX_STATUS(ds) & HAL_TXERR_XRETRY) {
		PRINTK_AMPDU("comp_unaggr: retry\n");
		ath_tx_retry_unaggr(sc, bf);
		return;
	}
	__stats(sc, tx_compunaggr);

	ath_tx_update_baw(tid, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
	ath_tx_status_update(sc, bf);
	ath_tx_freebuf(sc, bf);
}

static inline void
ath_tx_retry_unaggr(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);
	struct ath_txq *txq;

	txq = bf->bf_txq;

	if (bf->bf_retries >= OWLMAX_RETRIES) {
		__stats(sc, txunaggr_xretry);
		ath_tx_update_baw(tid, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
		ath_tx_status_update(sc, bf);
		ath_bar_tx(sc, tid, bf);
		return;
	}

	__stats(sc, txunaggr_compretries);
	if (!bf->bf_lastds->ds_link) {
		__stats(sc, txunaggr_errlast);
		bf = ath_buf_toggle(sc, bf, 1);
	}

	ath_tx_set_retry(sc, bf);
	asf_tailq_insert_head(&tid->buf_q, bf, bf_list);
	ath_tgt_tx_enqueue(txq, tid);
}

static void
ath_tx_update_baw(ath_atx_tid_t *tid, int seqno)
{
	int index;
	int cindex;

	index  = ATH_BA_INDEX(tid->seq_start, seqno);
	cindex = (tid->baw_head + index) & (ATH_TID_MAX_BUFS - 1);

	TX_BUF_BITMAP_CLR(tid->tx_buf_bitmap, cindex);

	while (tid->baw_head != tid->baw_tail &&
	       (!TX_BUF_BITMAP_IS_SET(tid->tx_buf_bitmap, tid->baw_head))) {
		INCR(tid->seq_start, IEEE80211_SEQ_MAX);
		INCR(tid->baw_head, ATH_TID_MAX_BUFS);
	}
}

static void ath_tx_set_retry(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ieee80211_frame *wh;

	__stats(sc, txaggr_retries);

	bf->bf_isretried = 1;
	bf->bf_retries ++;
	wh = ATH_SKB_2_WH(bf->bf_skb);
	wh->i_fc[1] |= IEEE80211_FC1_RETRY;
}

void ath_tgt_tx_cleanup(struct ath_softc_tgt *sc, struct ath_node_target *an,
			ath_atx_tid_t *tid, a_uint8_t discard_all)
{
	struct ath_tx_buf *bf;
	struct ath_tx_buf *bf_next;
	struct ath_txq *txq;

	txq = TID_TO_ACTXQ(tid->tidno);

	bf = asf_tailq_first(&tid->buf_q);

	while (bf) {
		if (discard_all || bf->bf_isretried) {
			bf_next = asf_tailq_next(bf, bf_list);
			TAILQ_DEQ(&tid->buf_q, bf, bf_list);
			if (bf->bf_isretried)
				ath_tx_update_baw(tid, SEQNO_FROM_BF_SEQNO(bf->bf_seqno));
			ath_tx_freebuf(sc, bf);
			bf = bf_next;
			continue;
		}
		bf->bf_comp = ath_tgt_tx_comp_normal;
		bf = asf_tailq_next(bf, bf_list);
	}

	ath_aggr_pause_tid(sc, tid);

	while (tid->baw_head != tid->baw_tail) {
		if (TX_BUF_BITMAP_IS_SET(tid->tx_buf_bitmap, tid->baw_head)) {
			tid->incomp++;
			tid->flag |= TID_CLEANUP_INPROGRES;
			TX_BUF_BITMAP_CLR(tid->tx_buf_bitmap, tid->baw_head);
		}
		INCR(tid->baw_head, ATH_TID_MAX_BUFS);
		INCR(tid->seq_start, IEEE80211_SEQ_MAX);
	}

	if (!(tid->flag & TID_CLEANUP_INPROGRES)) {
		ath_aggr_resume_tid(sc, tid);
	}
}

/******************/
/* BAR Management */
/******************/

static void ath_tgt_delba_send(struct ath_softc_tgt *sc,
			       struct ieee80211_node_target *ni,
			       a_uint8_t tidno, a_uint8_t initiator,
			       a_uint16_t reasoncode)
{
	struct ath_node_target *an = ATH_NODE_TARGET(ni);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, tidno);
	struct wmi_data_delba wmi_delba;

	tid->flag &= ~TID_AGGR_ENABLED;

	ath_tgt_tx_cleanup(sc, an, tid, 1);

	wmi_delba.ni_nodeindex = ni->ni_nodeindex;
	wmi_delba.tidno = tid->tidno;
	wmi_delba.initiator = 1;
	wmi_delba.reasoncode = IEEE80211_REASON_UNSPECIFIED;

	__stats(sc, txbar_xretry);
	wmi_event(sc->tgt_wmi_handle,
		  WMI_DELBA_EVENTID,
		  &wmi_delba,
		  sizeof(wmi_delba));
}

static void ath_bar_retry(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_node_target *an = ATH_NODE_TARGET(bf->bf_node);
	ath_atx_tid_t *tid = ATH_AN_2_TID(an, bf->bf_tidno);

	if (bf->bf_retries >= OWLMAX_BAR_RETRIES) {
		ath_tgt_delba_send(sc, bf->bf_node, tid->tidno, 1,
				   IEEE80211_REASON_UNSPECIFIED);
		ath_tgt_tid_drain(sc, tid);

		bf->bf_comp = NULL;
		ath_buf_comp(sc, bf);
		return;
	}

	__stats(sc, txbar_compretries);

	if (!bf->bf_lastds->ds_link) {
		__stats(sc, txbar_errlast);
		bf = ath_buf_toggle(sc, bf, 1);
	}

	bf->bf_lastds->ds_link = 0;

	ath_tx_set_retry(sc, bf);
	ath_tgt_txq_add_ucast(sc, bf);
}

static void ath_bar_tx_comp(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
{
	struct ath_tx_desc *ds = bf->bf_lastds;
	struct ath_node_target *an;
	ath_atx_tid_t *tid;
	struct ath_txq *txq;

	an = (struct ath_node_target *)bf->bf_node;
	tid = &an->tid[bf->bf_tidno];
	txq = TID_TO_ACTXQ(tid->tidno);

	if (ATH_DS_TX_STATUS(ds) & HAL_TXERR_XRETRY) {
		ath_bar_retry(sc, bf);
		return;
	}

	ath_aggr_resume_tid(sc, tid);

	bf->bf_comp = NULL;
	ath_buf_comp(sc, bf);
}

static void ath_bar_tx(struct ath_softc_tgt *sc,
		       ath_atx_tid_t *tid, struct ath_tx_buf *bf)
{
	adf_nbuf_t skb;
	struct ieee80211_frame_bar *bar;
	u_int8_t min_rate;
	struct ath_tx_desc *ds, *ds0;
	struct ath_hal *ah = sc->sc_ah;
	HAL_11N_RATE_SERIES series[4];
	int i = 0;
	adf_nbuf_queue_t skbhead;
	a_uint8_t *anbdata;
	a_uint32_t anblen;

	__stats(sc, tx_bars);

	adf_os_mem_set(&series, 0, sizeof(series));

	ath_aggr_pause_tid(sc, tid);

	skb = adf_nbuf_queue_remove(&bf->bf_skbhead);
	adf_nbuf_peek_header(skb, &anbdata, &anblen);
	adf_nbuf_trim_tail(skb, anblen);
	bar = (struct ieee80211_frame_bar *) anbdata;

	min_rate =  0x0b;

	ath_dma_unmap(sc, bf);
	adf_nbuf_queue_add(&bf->bf_skbhead, skb);

	bar->i_fc[1] = IEEE80211_FC1_DIR_NODS;
	bar->i_fc[0] = IEEE80211_FC0_VERSION_0 |
		IEEE80211_FC0_TYPE_CTL |
		IEEE80211_FC0_SUBTYPE_BAR;
	bar->i_ctl = tid->tidno << IEEE80211_BAR_CTL_TID_S |
		IEEE80211_BAR_CTL_COMBA;
	bar->i_seq = adf_os_cpu_to_le16(tid->seq_start << IEEE80211_SEQ_SEQ_SHIFT);

	bf->bf_seqno = tid->seq_start << IEEE80211_SEQ_SEQ_SHIFT;

	adf_nbuf_put_tail(skb, sizeof(struct ieee80211_frame_bar));

	bf->bf_comp = ath_bar_tx_comp;
	bf->bf_tidno = tid->tidno;
	bf->bf_node = &tid->an->ni;
	ath_dma_map(sc, bf);
	adf_nbuf_dmamap_info(bf->bf_dmamap, &bf->bf_dmamap_info);

	ds = bf->bf_desc;
	ah->ah_setupTxDesc(ds
			    , adf_nbuf_len(skb) + IEEE80211_CRC_LEN
			    , 0
			    , HAL_PKT_TYPE_NORMAL
			    , ATH_MIN(60, 60)
			    , min_rate
			    , ATH_TXMAXTRY
			    , bf->bf_keyix
			    , HAL_TXDESC_INTREQ
			    | HAL_TXDESC_CLRDMASK
			    , 0, 0);

	skbhead = bf->bf_skbhead;
	bf->bf_isaggr = 0;
	bf->bf_next = NULL;

	for (ds0 = ds, i=0; i < bf->bf_dmamap_info.nsegs; ds0++, i++) {
		ah->ah_clr11nAggr(ds0);
	}

	ath_filltxdesc(sc, bf);

	for (i = 0 ; i < 4; i++) {
		series[i].Tries = ATH_TXMAXTRY;
		series[i].Rate = min_rate;
		series[i].ChSel = sc->sc_ic.ic_tx_chainmask;
	}

	ah->ah_set11nRateScenario(bf->bf_desc, 0, 0, series, 4, 4);
	ath_tgt_txq_add_ucast(sc, bf);
}
