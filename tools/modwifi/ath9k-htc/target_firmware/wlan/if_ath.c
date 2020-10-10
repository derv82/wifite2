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
#include <adf_os_pci.h>
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
#include <adf_os_irq.h>

#include <if_ath_pci.h>
#include "if_llc.h"
#include "ieee80211_var.h"
#include "if_athrate.h"
#include "if_athvar.h"
#include "ah_desc.h"
#include "ah.h"

#include "attacks.h"
#include "modwifi.h"

static a_int32_t ath_numrxbufs = -1;
static a_int32_t ath_numrxdescs = -1;

#if defined(PROJECT_MAGPIE)
uint32_t *init_htc_handle = 0;
#endif

#define RX_ENDPOINT_ID 3
#define ATH_CABQ_HANDLING_THRESHOLD 9000
#define UAPSDQ_NUM   9
#define CABQ_NUM     8

void owl_tgt_tx_tasklet(TQUEUE_ARG data);
static void ath_tgt_send_beacon(struct ath_softc_tgt *sc,adf_nbuf_t bc_hdr,adf_nbuf_t nbuf,HTC_ENDPOINT_ID EndPt);
static void ath_hal_reg_write_tgt(void *Context, A_UINT16 Command, A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen);
static void ath_hal_reg_rmw_tgt(void *Context, A_UINT16 Command, A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen);
extern struct ath_tx_buf* ath_tgt_tx_prepare(struct ath_softc_tgt *sc, adf_nbuf_t skb, ath_data_hdr_t *dh);
extern void  ath_tgt_send_mgt(struct ath_softc_tgt *sc,adf_nbuf_t mgt_hdr, adf_nbuf_t skb,HTC_ENDPOINT_ID EndPt);
extern HAL_BOOL ath_hal_wait(struct ath_hal *ah, a_uint32_t reg, a_uint32_t mask, a_uint32_t val);
extern void owltgt_tx_processq(struct ath_softc_tgt *sc, struct ath_txq *txq,  owl_txq_state_t txqstate);
void owl_tgt_node_init(struct ath_node_target * an);
void ath_tgt_tx_sched_normal(struct ath_softc_tgt *sc, struct ath_buf *bf);
void ath_tgt_tx_sched_nonaggr(struct ath_softc_tgt *sc,struct ath_buf * bf_host);

/*
 * Extend a 32 bit TSF to nearest 64 bit TSF value.
 * When the adapter is a STATION, its local TSF is periodically modified by
 * the hardware to match the BSS TSF (as received in beacon packets), and
 * rstamp may appear to be from the future or from the past (with reference
 * to the current local TSF) because of jitter. This is mostly noticable in
 * highly congested channels. The code uses signed modulo arithmetic to
 * handle both past/future cases and signed-extension to avoid branches.
 * Test cases:
 * extend(0x0000001200000004, 0x00000006) == 0x0000001200000006
 * extend(0x0000001200000004, 0x00000002) == 0x0000001200000002
 * extend(0x0000001200000004, 0xfffffffe) == 0x00000011fffffffe  ! tsfhigh--
 * extend(0x000000127ffffffe, 0x80000002) == 0x0000001280000002
 * extend(0x0000001280000002, 0x7ffffffe) == 0x000000127ffffffe
 * extend(0x00000012fffffffc, 0xfffffffe) == 0x00000012fffffffe
 * extend(0x00000012fffffffc, 0xfffffffa) == 0x00000012fffffffa
 * extend(0x00000012fffffffc, 0x00000002) == 0x0000001300000002  ! tsfhigh++
 */
static u_int64_t ath_extend_tsf(struct ath_softc_tgt *sc, u_int32_t rstamp)
{
	struct ath_hal *ah = sc->sc_ah;
	u_int64_t tsf;
	u_int32_t tsf_low;
	a_int64_t tsf_delta;  /* signed int64 */

	tsf = ah->ah_getTsf64(ah);
	tsf_low = tsf & 0xffffffffUL;

	tsf_delta = (a_int32_t)((rstamp - tsf_low) & 0xffffffffUL);

	return (tsf + (u_int64_t)tsf_delta);
}

static a_int32_t ath_rate_setup(struct ath_softc_tgt *sc, a_uint32_t mode)
{
	struct ath_hal *ah = sc->sc_ah;
	const HAL_RATE_TABLE *rt;

	switch (mode) {
	case IEEE80211_MODE_11NA:
		sc->sc_rates[mode] = ah->ah_getRateTable(ah, HAL_MODE_11NA);
		break;
	case IEEE80211_MODE_11NG:
		sc->sc_rates[mode] = ah->ah_getRateTable(ah, HAL_MODE_11NG);
		break;
	default:
		return 0;
	}
	rt = sc->sc_rates[mode];
	if (rt == NULL)
		return 0;

	return 1;
}

static void ath_setcurmode(struct ath_softc_tgt *sc,
			   enum ieee80211_phymode mode)
{
	const HAL_RATE_TABLE *rt;
	a_int32_t i;

	adf_os_mem_set(sc->sc_rixmap, 0xff, sizeof(sc->sc_rixmap));

	rt = sc->sc_rates[mode];
	adf_os_assert(rt != NULL);

	for (i = 0; i < rt->rateCount; i++) {
		sc->sc_rixmap[rt->info[i].rateCode] = i;
	}

	sc->sc_currates = rt;
	sc->sc_curmode = mode;
	sc->sc_protrix = ((mode == IEEE80211_MODE_11NG) ? 3 : 0);

}

void wmi_event(wmi_handle_t handle, WMI_EVENT_ID evt_id,
	       void *buffer, a_int32_t Length)
{
	adf_nbuf_t netbuf = ADF_NBUF_NULL;
	a_uint8_t *pData;

	netbuf = WMI_AllocEvent(handle, WMI_EVT_CLASS_CMD_EVENT,
				sizeof(WMI_CMD_HDR) + Length);

	if (netbuf == ADF_NBUF_NULL) {
		adf_os_print("Buf null\n");
		return;
	}

	if (buffer != NULL && Length != 0 && Length < WMI_SVC_MAX_BUFFERED_EVENT_SIZE) {
		pData = adf_nbuf_put_tail(netbuf, Length);
		adf_os_mem_copy(pData, buffer, Length);
	}

	WMI_SendEvent(handle, netbuf, evt_id, 0, Length);
}

void wmi_cmd_rsp(void *pContext, WMI_COMMAND_ID cmd_id, A_UINT16 SeqNo,
		 void *buffer, a_int32_t Length)
{
	adf_nbuf_t netbuf = ADF_NBUF_NULL;
	A_UINT8 *pData;

	netbuf = WMI_AllocEvent(pContext, WMI_EVT_CLASS_CMD_REPLY,
				sizeof(WMI_CMD_HDR) + Length);

	if (netbuf == ADF_NBUF_NULL) {
		adf_os_assert(0);
		return;
	}

	if (Length != 0 && buffer != NULL) {
		pData = (A_UINT8 *)adf_nbuf_put_tail(netbuf, Length);
		adf_os_mem_copy(pData, buffer, Length);
	}

	WMI_SendEvent(pContext, netbuf, cmd_id, SeqNo, Length);
}

static void ath_node_vdelete_tgt(struct ath_softc_tgt *sc, a_uint8_t vap_index)
{
	a_int32_t i;

	for (i = 0; i < TARGET_NODE_MAX; i++) {
		if(sc->sc_sta[i].ni.ni_vapindex == vap_index)
			sc->sc_sta[i].an_valid = 0;
	}
}

a_uint8_t ath_get_minrateidx(struct ath_softc_tgt *sc, struct ath_vap_target *avp)
{
	if (sc->sc_curmode == IEEE80211_MODE_11NG)
		return avp->av_minrateidx[0];
	else if (sc->sc_curmode == IEEE80211_MODE_11NA)
		return avp->av_minrateidx[1];

	return 0;
}

/******/
/* RX */
/******/

static adf_nbuf_t ath_alloc_skb_align(struct ath_softc_tgt *sc,
				      a_uint32_t size, a_uint32_t align)
{
	adf_nbuf_t skb;

	skb = BUF_Pool_alloc_buf_align(sc->pool_handle, POOL_ID_WLAN_RX_BUF,
				       RX_HEADER_SPACE, align);
	return skb;
}

static a_int32_t ath_rxdesc_init(struct ath_softc_tgt *sc, struct ath_rx_desc *ds)
{
	struct ath_hal *ah = sc->sc_ah;
	struct ath_rx_desc *ds_held;
	a_uint8_t *anbdata;
	a_uint32_t anblen;

	if (!sc->sc_rxdesc_held) {
		sc->sc_rxdesc_held = ds;
		return 0;
	}

	ds_held = sc->sc_rxdesc_held;
	sc->sc_rxdesc_held = ds;
	ds = ds_held;

	if (ds->ds_nbuf == ADF_NBUF_NULL) {
		ds->ds_nbuf = ath_alloc_skb_align(sc, sc->sc_rxbufsize, sc->sc_cachelsz);
		if (ds->ds_nbuf == ADF_NBUF_NULL) {
			sc->sc_rxdesc_held = ds;
			sc->sc_rx_stats.ast_rx_nobuf++;
			return ENOMEM;
		}
		adf_nbuf_map(sc->sc_dev, ds->ds_dmap, ds->ds_nbuf, ADF_OS_DMA_FROM_DEVICE);
		adf_nbuf_dmamap_info(ds->ds_dmap, &ds->ds_dmap_info);
		ds->ds_data = ds->ds_dmap_info.dma_segs[0].paddr;
	}

	ds->ds_link = 0;
	adf_nbuf_peek_header(ds->ds_nbuf, &anbdata, &anblen);

	ah->ah_setupRxDesc(ds, adf_nbuf_tailroom(ds->ds_nbuf), 0);

	if (sc->sc_rxlink == NULL) {
		ah->ah_setRxDP(ah, ds->ds_daddr);
	}
	else {
		*sc->sc_rxlink = ds->ds_daddr;
	}
	sc->sc_rxlink = &ds->ds_link;
	ah->ah_enableReceive(ah);

	return 0;
}

static void ath_rx_complete(struct ath_softc_tgt *sc, adf_nbuf_t buf)
{
	struct ath_rx_desc *ds;
	adf_nbuf_t buf_tmp;
	adf_nbuf_queue_t nbuf_head;

	adf_nbuf_split_to_frag(buf, &nbuf_head);
	ds = asf_tailq_first(&sc->sc_rxdesc_idle);

	while (ds) {
		struct ath_rx_desc *ds_tmp;
		buf_tmp = adf_nbuf_queue_remove(&nbuf_head);

		if (buf_tmp == NULL) {
			break;
		}

		BUF_Pool_free_buf(sc->pool_handle, POOL_ID_WLAN_RX_BUF, buf_tmp);

		ds_tmp = ds;
		ds = asf_tailq_next(ds, ds_list);

		ath_rxdesc_init(sc, ds_tmp);

		asf_tailq_remove(&sc->sc_rxdesc_idle, ds_tmp, ds_list);
		asf_tailq_insert_tail(&sc->sc_rxdesc, ds_tmp, ds_list);
	}
}

static void tgt_HTCSendCompleteHandler(HTC_ENDPOINT_ID Endpt, adf_nbuf_t buf, void *ServiceCtx)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)ServiceCtx;

	if (Endpt == RX_ENDPOINT_ID) {
		sc->sc_rx_stats.ast_rx_done++;
		ath_rx_complete(sc, buf);
	}
}

static void ath_uapsd_processtriggers(struct ath_softc_tgt *sc)
{
	struct ath_hal *ah = sc->sc_ah;
	struct ath_rx_buf *bf = NULL;
	struct ath_rx_desc *ds, *ds_head, *ds_tail, *ds_tmp;
	a_int32_t retval;
	a_uint32_t cnt = 0;
	a_uint16_t frame_len = 0;
	a_uint64_t tsf;

#ifdef DEBUG_RXQUEUE
	printk(".");
#endif

#define	PA2DESC(_sc, _pa)						\
	((struct ath_desc *)((caddr_t)(_sc)->sc_rxdma.dd_desc +		\
			     ((_pa) - (_sc)->sc_rxdma.dd_desc_paddr)))

	tsf = ah->ah_getTsf64(ah);
	bf = asf_tailq_first(&sc->sc_rxbuf);

	ds = asf_tailq_first(&sc->sc_rxdesc);
	ds_head = ds;

	while(ds) {
		++cnt;

		if (cnt == ath_numrxbufs - 1) {
			adf_os_print("VERY LONG PACKET!!!!!\n");
			ds_tail = ds;
			ds_tmp = ds_head;
			while (ds_tmp) {
				struct ath_rx_desc *ds_rmv;
				adf_nbuf_unmap(sc->sc_dev, ds_tmp->ds_dmap, ADF_OS_DMA_FROM_DEVICE);
				ds_rmv = ds_tmp;
				ds_tmp = asf_tailq_next(ds_tmp, ds_list);

				if (ds_tmp == NULL) {
					adf_os_print("ds_tmp is NULL\n");
					adf_os_assert(0);
				}

				BUF_Pool_free_buf(sc->pool_handle, POOL_ID_WLAN_RX_BUF, ds_rmv->ds_nbuf);
				ds_rmv->ds_nbuf = ADF_NBUF_NULL;

				if (ath_rxdesc_init(sc, ds_rmv) == 0) {
					asf_tailq_remove(&sc->sc_rxdesc, ds_rmv, ds_list);
					asf_tailq_insert_tail(&sc->sc_rxdesc, ds_rmv, ds_list);
				}
				else {
					asf_tailq_remove(&sc->sc_rxdesc, ds_rmv, ds_list);
					asf_tailq_insert_tail(&sc->sc_rxdesc_idle, ds_rmv, ds_list);
				}

				if (ds_rmv == ds_tail) {
					break;
				}
			}
			break;
		}

		if (ds->ds_link == 0) {
#ifdef DEBUG_RXQUEUE
			printk("0");
#endif
			break;
		}

		if (bf->bf_status & ATH_BUFSTATUS_DONE) {
#ifdef DEBUG_RXQUEUE
			printk("D");
#endif
			continue;
		}

		retval = ah->ah_procRxDescFast(ah, ds, ds->ds_daddr,
						PA2DESC(sc, ds->ds_link), &bf->bf_rx_status);
		if (HAL_EINPROGRESS == retval) {
#ifdef DEBUG_RXQUEUE
			printk("P");
#endif
			break;
		}

		if (adf_nbuf_len(ds->ds_nbuf) == 0) {
			adf_nbuf_put_tail(ds->ds_nbuf, bf->bf_rx_status.rs_datalen);
		}

		frame_len += bf->bf_rx_status.rs_datalen;

		if (bf->bf_rx_status.rs_more == 0) {
			adf_nbuf_queue_t nbuf_head;
			adf_nbuf_queue_init(&nbuf_head);

			cnt = 0;

			ds_tail = ds;
			ds = asf_tailq_next(ds, ds_list);

			ds_tmp = ds_head;
			ds_head = asf_tailq_next(ds_tail, ds_list);

			while (ds_tmp) {
				struct ath_rx_desc *ds_rmv;

				adf_nbuf_unmap(sc->sc_dev, ds_tmp->ds_dmap, ADF_OS_DMA_FROM_DEVICE);
				adf_nbuf_queue_add(&nbuf_head, ds_tmp->ds_nbuf);
				ds_tmp->ds_nbuf = ADF_NBUF_NULL;

				ds_rmv = ds_tmp;
				ds_tmp = asf_tailq_next(ds_tmp, ds_list);
				if (ds_tmp == NULL) {
					adf_os_assert(0);
				}

				if (ath_rxdesc_init(sc, ds_rmv) == 0) {
					asf_tailq_remove(&sc->sc_rxdesc, ds_rmv, ds_list);
					asf_tailq_insert_tail(&sc->sc_rxdesc, ds_rmv, ds_list);
				}  else {
					asf_tailq_remove(&sc->sc_rxdesc, ds_rmv, ds_list);
					asf_tailq_insert_tail(&sc->sc_rxdesc_idle, ds_rmv, ds_list);
				}

				if (ds_rmv == ds_tail) {
					break;
				}
			}


			bf->bf_rx_status.rs_datalen = frame_len;
			frame_len = 0;

			bf->bf_skb = adf_nbuf_create_frm_frag(&nbuf_head);

			bf->bf_status |= ATH_BUFSTATUS_DONE;

			bf = (struct ath_rx_buf *)asf_tailq_next(bf, bf_list);
		}
		else {
			ds = asf_tailq_next(ds, ds_list);
		}

#ifdef DEBUG_RXQUEUE
		printk(">");
#endif
	}
#undef PA2DESC
}

static a_int32_t ath_startrecv(struct ath_softc_tgt *sc)
{
	struct ath_hal *ah = sc->sc_ah;
	struct ath_rx_desc *ds;

	sc->sc_rxbufsize = 1024+512+128;
	sc->sc_rxlink = NULL;

	sc->sc_rxdesc_held = NULL;

	asf_tailq_foreach(ds, &sc->sc_rxdesc, ds_list) {
		a_int32_t error = ath_rxdesc_init(sc, ds);
		if (error != 0) {
			return error;
		}
	}

	ds = asf_tailq_first(&sc->sc_rxdesc);
	ah->ah_setRxDP(ah, ds->ds_daddr);

	return 0;
}

static void ath_tgt_rx_tasklet(TQUEUE_ARG data)
{
	struct ath_softc_tgt *sc  = (struct ath_softc_tgt *)data;
	struct ath_rx_buf *bf = NULL;
	struct ath_hal *ah = sc->sc_ah;
	struct rx_frame_header *rxhdr;
	struct ath_rx_status *rxstats;
	adf_nbuf_t skb = ADF_NBUF_NULL;

	do {
		bf = asf_tailq_first(&sc->sc_rxbuf);
		if (bf == NULL) {
			break;
		}

		if (!(bf->bf_status & ATH_BUFSTATUS_DONE)) {
			break;
		}

		skb = bf->bf_skb;
		if (skb == NULL) {
			continue;
		}

		asf_tailq_remove(&sc->sc_rxbuf, bf, bf_list);

		bf->bf_skb = NULL;

		rxhdr = (struct rx_frame_header *)adf_nbuf_push_head(skb,
						     sizeof(struct rx_frame_header));
		rxstats = (struct ath_rx_status *)(&rxhdr->rx_stats[0]);
		adf_os_mem_copy(rxstats, &(bf->bf_rx_status),
				sizeof(struct ath_rx_status));

		rxstats->rs_tstamp = ath_extend_tsf(sc, (u_int32_t)rxstats->rs_tstamp);

		HTC_SendMsg(sc->tgt_htc_handle, RX_ENDPOINT_ID, skb);
		sc->sc_rx_stats.ast_rx_send++;

		bf->bf_status &= ~ATH_BUFSTATUS_DONE;
		asf_tailq_insert_tail(&sc->sc_rxbuf, bf, bf_list);

	} while(1);

	sc->sc_imask |= HAL_INT_RX;
	ah->ah_setInterrupts(ah, sc->sc_imask);
}

/*******************/
/* Beacon Handling */
/*******************/

/*
 * Setup the beacon frame for transmit.
 * FIXME: Short Preamble.
 */
static void ath_beacon_setup(struct ath_softc_tgt *sc,
			     struct ath_tx_buf *bf,
			     struct ath_vap_target *avp)
{
	adf_nbuf_t skb = bf->bf_skb;
	struct ath_hal *ah = sc->sc_ah;
	struct ath_tx_desc *ds;
	a_int32_t flags;
	const HAL_RATE_TABLE *rt;
	a_uint8_t rix, rate;
	HAL_11N_RATE_SERIES series[4] = {{ 0 }};

	flags = HAL_TXDESC_NOACK;

	ds = bf->bf_desc;
	ds->ds_link = 0;
	ds->ds_data = bf->bf_dmamap_info.dma_segs[0].paddr;

	rix = ath_get_minrateidx(sc, avp);
	rt  = sc->sc_currates;
	rate = rt->info[rix].rateCode;

	ah->ah_setupTxDesc(ds
			    , adf_nbuf_len(skb) + IEEE80211_CRC_LEN
			    , sizeof(struct ieee80211_frame)
			    , HAL_PKT_TYPE_BEACON
			    , MAX_RATE_POWER
			    , rate, 1
			    , HAL_TXKEYIX_INVALID
			    , flags
			    , 0
			    , 0);

	ah->ah_fillTxDesc(ds
			   , asf_roundup(adf_nbuf_len(skb), 4)
			   , AH_TRUE
			   , AH_TRUE
			   , ds);

	series[0].Tries = 1;
	series[0].Rate = rate;
	series[0].ChSel = sc->sc_ic.ic_tx_chainmask;
	series[0].RateFlags = 0;
	ah->ah_set11nRateScenario(ds, 0, 0, series, 4, 0);
}

static void ath_tgt_send_beacon(struct ath_softc_tgt *sc, adf_nbuf_t bc_hdr,
				adf_nbuf_t nbuf, HTC_ENDPOINT_ID EndPt)
{
	struct ath_hal *ah = sc->sc_ah;
	struct ath_tx_buf *bf;
	a_uint8_t vap_index, *anbdata;
	ath_beacon_hdr_t *bhdr;
	struct ieee80211vap_target  *vap;
	a_uint32_t anblen;
	struct ieee80211_frame *wh;

	if (!bc_hdr) {
		adf_nbuf_peek_header(nbuf, &anbdata, &anblen);
		bhdr = (ath_beacon_hdr_t *)anbdata;
	} else {
		adf_os_print("found bc_hdr! 0x%x\n", bc_hdr);
	}

	vap_index = bhdr->vap_index;
	adf_os_assert(vap_index < TARGET_VAP_MAX);
	vap = &sc->sc_vap[vap_index].av_vap;

	wh = (struct ieee80211_frame *)adf_nbuf_pull_head(nbuf,
						  sizeof(ath_beacon_hdr_t));

	bf = sc->sc_vap[vap_index].av_bcbuf;
	adf_os_assert(bf);
	bf->bf_endpt = EndPt;

	if (bf->bf_skb) {
		adf_nbuf_unmap(sc->sc_dev, bf->bf_dmamap, ADF_OS_DMA_TO_DEVICE);
		adf_nbuf_push_head(bf->bf_skb, sizeof(ath_beacon_hdr_t));
		ath_free_tx_skb(sc->tgt_htc_handle, bf->bf_endpt, bf->bf_skb);
	}

	bf->bf_skb = nbuf;

	adf_nbuf_map(sc->sc_dev, bf->bf_dmamap, nbuf, ADF_OS_DMA_TO_DEVICE);
	adf_nbuf_dmamap_info(bf->bf_dmamap,&bf->bf_dmamap_info);

	ath_beacon_setup(sc, bf, &sc->sc_vap[vap_index]);
	ah->ah_stopTxDma(ah, sc->sc_bhalq);
	ah->ah_setTxDP(ah, sc->sc_bhalq, ATH_BUF_GET_DESC_PHY_ADDR(bf));
	ah->ah_startTxDma(ah, sc->sc_bhalq);
}

/******/
/* TX */
/******/

static void ath_tx_stopdma(struct ath_softc_tgt *sc, struct ath_txq *txq)
{
	struct ath_hal *ah = sc->sc_ah;

	ah->ah_stopTxDma(ah, txq->axq_qnum);
}

static void owltgt_txq_drain(struct ath_softc_tgt *sc, struct ath_txq *txq)
{
	owltgt_tx_processq(sc, txq, OWL_TXQ_STOPPED);
}

static void ath_tx_draintxq(struct ath_softc_tgt *sc, struct ath_txq *txq)
{
	owltgt_txq_drain(sc, txq);
}

static void ath_draintxq(struct ath_softc_tgt *sc, HAL_BOOL drain_softq)
{
	struct ath_hal *ah = sc->sc_ah;
	a_uint16_t i;
	struct ath_txq *txq = NULL;
	struct ath_atx_tid *tid = NULL;

	ath_tx_status_clear(sc);
	sc->sc_tx_draining = 1;

	ah->ah_stopTxDma(ah, sc->sc_bhalq);

	for (i = 0; i < HAL_NUM_TX_QUEUES; i++)
		if (ATH_TXQ_SETUP(sc, i))
			ath_tx_stopdma(sc, ATH_TXQ(sc, i));

	for (i = 0; i < HAL_NUM_TX_QUEUES; i++)
		if (ATH_TXQ_SETUP(sc, i)) {
			owltgt_tx_processq(sc, ATH_TXQ(sc,i), OWL_TXQ_STOPPED);

			txq = ATH_TXQ(sc,i);
			while (!asf_tailq_empty(&txq->axq_tidq)){
				TAILQ_DEQ(&txq->axq_tidq, tid, tid_qelem);
				if(tid == NULL)
					break;
				tid->sched = AH_FALSE;
				ath_tgt_tid_drain(sc,tid);
			}
		}

	sc->sc_tx_draining = 0;
}

static void ath_tgt_txq_setup(struct ath_softc_tgt *sc)
{
	a_int32_t qnum;
	struct ath_txq *txq;

	sc->sc_txqsetup=0;

	for (qnum=0;qnum<HAL_NUM_TX_QUEUES;qnum++) {
		txq= &sc->sc_txq[qnum];
		txq->axq_qnum = qnum;
		txq->axq_link = NULL;
		asf_tailq_init(&txq->axq_q);
		txq->axq_depth = 0;
		txq->axq_linkbuf = NULL;
		asf_tailq_init(&txq->axq_tidq);
		sc->sc_txqsetup |= 1<<qnum;
	}

	sc->sc_uapsdq  = &sc->sc_txq[UAPSDQ_NUM];
	sc->sc_cabq    = &sc->sc_txq[CABQ_NUM];

	sc->sc_ac2q[WME_AC_BE]  = &sc->sc_txq[0];
	sc->sc_ac2q[WME_AC_BK]  = &sc->sc_txq[1];
	sc->sc_ac2q[WME_AC_VI]  = &sc->sc_txq[2];
	sc->sc_ac2q[WME_AC_VO]  = &sc->sc_txq[3];

	return;
#undef N
}

static void tgt_HTCRecv_beaconhandler(HTC_ENDPOINT_ID EndPt, adf_nbuf_t hdr_buf,
				      adf_nbuf_t buf, void *ServiceCtx)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)ServiceCtx;

	ath_tgt_send_beacon(sc, hdr_buf, buf, EndPt);
}

static void tgt_HTCRecv_uapsdhandler(HTC_ENDPOINT_ID EndPt, adf_nbuf_t hdr_buf,
				     adf_nbuf_t buf, void *ServiceCtx)
{
}

static void tgt_HTCRecv_mgmthandler(HTC_ENDPOINT_ID EndPt, adf_nbuf_t hdr_buf,
				    adf_nbuf_t buf, void *ServiceCtx)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)ServiceCtx;

	ath_tgt_send_mgt(sc,hdr_buf,buf,EndPt);
}

static void tgt_HTCRecvMessageHandler(HTC_ENDPOINT_ID EndPt,
				      adf_nbuf_t hdr_buf, adf_nbuf_t buf,
				      void *ServiceCtx)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)ServiceCtx;
	struct ath_tx_buf *bf;
	a_uint8_t *data;
	a_uint32_t len;
	ath_data_hdr_t *dh;
	struct ath_node_target *an;
	struct ath_atx_tid *tid;

	if (!hdr_buf) {
		adf_nbuf_peek_header(buf, &data, &len);
		adf_nbuf_pull_head(buf, sizeof(ath_data_hdr_t));
	} else {
		adf_nbuf_peek_header(hdr_buf, &data, &len);
	}

	adf_os_assert(len >= sizeof(ath_data_hdr_t));
	dh = (ath_data_hdr_t *)data;

	an = &sc->sc_sta[dh->ni_index];
	tid = ATH_AN_2_TID(an, dh->tidno);

	sc->sc_tx_stats.tx_tgt++;

	bf = ath_tgt_tx_prepare(sc, buf, dh);
	if (!bf) {
		ath_free_tx_skb(sc->tgt_htc_handle,EndPt,buf);
		return;
	}

#ifdef DEBUG_INJECT_AMPDU
	printk("RecvMsg: aggr=");
	if (tid != NULL)
		printk(itox(!!(tid->flag & TID_AGGR_ENABLED)));
	if (modwifi_txampdu_check(buf, NULL))
		printk(" force");
	printk("\n");
#endif

	bf->bf_endpt = EndPt;
	bf->bf_cookie = dh->cookie;

	if ( (tid->flag & TID_AGGR_ENABLED) || modwifi_txampdu_check(buf, NULL))
		ath_tgt_handle_aggr(sc, bf);
	else
		ath_tgt_handle_normal(sc, bf);
}

static void tgt_HTCRecv_cabhandler(HTC_ENDPOINT_ID EndPt, adf_nbuf_t hdr_buf,
				   adf_nbuf_t buf, void *ServiceCtx)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)ServiceCtx;
	struct ath_hal *ah = sc->sc_ah;
	a_uint64_t tsf;
	a_uint32_t tmp;

#ifdef ATH_ENABLE_CABQ
	tsf = ah->ah_getTsf64(ah);
	tmp = tsf - sc->sc_swba_tsf;

	if ( tmp > ATH_CABQ_HANDLING_THRESHOLD ) {
		HTC_ReturnBuffers(sc->tgt_htc_handle, EndPt, buf);
		return;
	}

	tgt_HTCRecvMessageHandler(EndPt, hdr_buf, buf, ServiceCtx);
#endif
}

/***********************/
/* Descriptor Handling */
/***********************/

static a_int32_t ath_descdma_setup(struct ath_softc_tgt *sc,
				   struct ath_descdma *dd, ath_bufhead *head,
				   const char *name, a_int32_t nbuf, a_int32_t ndesc,
				   a_uint32_t bfSize, a_uint32_t descSize)
{
#define DS2PHYS(_dd, _ds)						\
	((_dd)->dd_desc_paddr + ((caddr_t)(_ds) - (caddr_t)(_dd)->dd_desc))

	struct ath_desc *ds;
	struct ath_buf *bf;
	a_int32_t i, bsize, error;
	a_uint8_t *bf_addr;
	a_uint8_t *ds_addr;

	dd->dd_name = name;
	dd->dd_desc_len = descSize * nbuf * ndesc;

	dd->dd_desc = adf_os_dmamem_alloc(sc->sc_dev,
				  dd->dd_desc_len, 1, &dd->dd_desc_dmamap);
	dd->dd_desc_paddr = adf_os_dmamem_map2addr(dd->dd_desc_dmamap);
	if (dd->dd_desc == NULL) {
		error = -ENOMEM;
		goto fail;
	}
	ds = dd->dd_desc;

	bsize = bfSize * nbuf;
	bf = adf_os_mem_alloc(bsize);
	if (bf == NULL) {
		error = -ENOMEM;
		goto fail2;
	}
	adf_os_mem_set(bf, 0, bsize);
	dd->dd_bufptr = bf;

	bf_addr = (a_uint8_t *)bf;
	ds_addr = (a_uint8_t *)ds;

	asf_tailq_init(head);

	for (i = 0; i < nbuf; i++) {
		a_int32_t j;

		if (adf_nbuf_dmamap_create( sc->sc_dev, &bf->bf_dmamap) != A_STATUS_OK) {
			goto fail2;
		}

		bf->bf_desc = bf->bf_descarr = bf->bf_lastds = ds;
		for (j = 0; j < ndesc; j++)
			ATH_BUF_SET_DESC_PHY_ADDR_WITH_IDX(bf, j, (ds_addr + (j*descSize)));

		ATH_BUF_SET_DESC_PHY_ADDR(bf, ATH_BUF_GET_DESC_PHY_ADDR_WITH_IDX(bf, 0));

		adf_nbuf_queue_init(&bf->bf_skbhead);
		asf_tailq_insert_tail(head, bf, bf_list);

		bf_addr += bfSize;
		ds_addr += (ndesc * descSize);
		bf = (struct ath_buf *)bf_addr;
		ds = (struct ath_desc *)ds_addr;
	}

	return 0;
fail2:
	adf_os_dmamem_free(sc->sc_dev, dd->dd_desc_len,
			   1, dd->dd_desc, dd->dd_desc_dmamap);
fail:
	adf_os_mem_set(dd, 0, sizeof(*dd));
	adf_os_assert(0);
	return error;

#undef DS2PHYS
}

static void ath_descdma_cleanup(struct ath_softc_tgt *sc,
				struct ath_descdma *dd,
				ath_bufhead *head, a_int32_t dir)
{
	struct ath_buf *bf;
	struct ieee80211_node_target *ni;

	asf_tailq_foreach(bf, head, bf_list) {
		if (adf_nbuf_queue_len(&bf->bf_skbhead) != 0) {
			adf_nbuf_unmap(sc->sc_dev, bf->bf_dmamap, dir);
			while(adf_nbuf_queue_len(&bf->bf_skbhead) != 0) {
				ath_free_rx_skb(sc,
					adf_nbuf_queue_remove(&bf->bf_skbhead));
			}
			bf->bf_skb = NULL;
		} else if (bf->bf_skb != NULL) {
			adf_nbuf_unmap(sc->sc_dev,bf->bf_dmamap, dir);
			ath_free_rx_skb(sc, bf->bf_skb);
			bf->bf_skb = NULL;
		}

		adf_nbuf_dmamap_destroy(sc->sc_dev, bf->bf_dmamap);

		ni = bf->bf_node;
		bf->bf_node = NULL;
	}

	adf_os_dmamem_free(sc->sc_dev, dd->dd_desc_len,
			   1, dd->dd_desc, dd->dd_desc_dmamap);

	asf_tailq_init(head);
	adf_os_mem_free(dd->dd_bufptr);
	adf_os_mem_set(dd, 0, sizeof(*dd));
}

static a_int32_t ath_desc_alloc(struct ath_softc_tgt *sc)
{
#define DS2PHYS(_dd, _ds)						\
	((_dd)->dd_desc_paddr + ((caddr_t)(_ds) - (caddr_t)(_dd)->dd_desc))

	a_int32_t error;
	struct ath_tx_buf *bf;

	if(ath_numrxbufs == -1)
		ath_numrxbufs = ATH_RXBUF;

	if (ath_numrxdescs == -1)
		ath_numrxdescs = ATH_RXDESC;

	error = ath_descdma_setup(sc, &sc->sc_rxdma, (ath_bufhead *)&sc->sc_rxbuf,
				  "rx", ath_numrxdescs, 1,
				  sizeof(struct ath_rx_buf),
				  sizeof(struct ath_rx_desc));
	if (error != 0)
		return error;

	a_uint32_t i;
	struct ath_descdma *dd = &sc->sc_rxdma;
	struct ath_rx_desc *ds = (struct ath_rx_desc *)dd->dd_desc;
	struct ath_rx_desc *ds_prev = NULL;

	asf_tailq_init(&sc->sc_rxdesc);
	asf_tailq_init(&sc->sc_rxdesc_idle);

	/** this works because descriptors follow eachother linearly in memory */
	for (i = 0; i < ath_numrxdescs; i++, ds++) {

		if (ds->ds_nbuf != ADF_NBUF_NULL) {
			ds->ds_nbuf = ADF_NBUF_NULL;
		}

		if (adf_nbuf_dmamap_create(sc->sc_dev, &ds->ds_dmap) != A_STATUS_OK) {
			adf_os_assert(0);
		}

		ds->ds_daddr = DS2PHYS(&sc->sc_rxdma, ds);

		if (ds_prev) {
			ds_prev->ds_link = ds->ds_daddr;
		}

		ds->ds_link = 0;
		ds_prev = ds;

		asf_tailq_insert_tail(&sc->sc_rxdesc, ds, ds_list);
	}

	error = ath_descdma_setup(sc, &sc->sc_txdma, (ath_bufhead *)&sc->sc_txbuf,
				  "tx", ATH_TXBUF + 1, ATH_TXDESC,
				  sizeof(struct ath_tx_buf),
				  sizeof(struct ath_tx_desc));
	if (error != 0) {
		ath_descdma_cleanup(sc, &sc->sc_rxdma, (ath_bufhead *)&sc->sc_rxbuf,
				    ADF_OS_DMA_FROM_DEVICE);
		return error;
	}

	error = ath_descdma_setup(sc, &sc->sc_bdma, (ath_bufhead *)&sc->sc_bbuf,
				  "beacon", ATH_BCBUF, 1,
				  sizeof(struct ath_tx_buf),
				  sizeof(struct ath_tx_desc));
	if (error != 0) {
		ath_descdma_cleanup(sc, &sc->sc_txdma, (ath_bufhead *)&sc->sc_txbuf,
				    ADF_OS_DMA_TO_DEVICE);
		ath_descdma_cleanup(sc, &sc->sc_rxdma, (ath_bufhead *)&sc->sc_rxbuf,
				    ADF_OS_DMA_FROM_DEVICE);
		return error;
	}

	bf = asf_tailq_first(&sc->sc_txbuf);
	bf->bf_isaggr = bf->bf_isretried = bf->bf_retries = 0;
	asf_tailq_remove(&sc->sc_txbuf, bf, bf_list);

	sc->sc_txbuf_held = bf;

	return 0;

#undef DS2PHYS
}

static void ath_desc_free(struct ath_softc_tgt *sc)
{
	asf_tailq_insert_tail(&sc->sc_txbuf, sc->sc_txbuf_held, bf_list);

	sc->sc_txbuf_held = NULL;

	if (sc->sc_txdma.dd_desc_len != 0)
		ath_descdma_cleanup(sc, &sc->sc_txdma, (ath_bufhead *)&sc->sc_txbuf,
				    ADF_OS_DMA_TO_DEVICE);
	if (sc->sc_rxdma.dd_desc_len != 0)
		ath_descdma_cleanup(sc, &sc->sc_rxdma, (ath_bufhead *)&sc->sc_rxbuf,
				    ADF_OS_DMA_FROM_DEVICE);
}

/**********************/
/* Interrupt Handling */
/**********************/

adf_os_irq_resp_t ath_intr(adf_drv_handle_t hdl)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)hdl;
	struct ath_hal *ah = sc->sc_ah;
	HAL_INT status;

	if (sc->sc_invalid)
		return ADF_OS_IRQ_NONE;

	if (!ah->ah_isInterruptPending(ah))
		return ADF_OS_IRQ_NONE;

	ah->ah_getPendingInterrupts(ah, &status);

	status &= sc->sc_imask;

	if (status & HAL_INT_FATAL) {
		ah->ah_setInterrupts(ah, 0);
		ATH_SCHEDULE_TQUEUE(sc->sc_dev, &sc->sc_fataltq);
	} else {
		if (status & HAL_INT_SWBA) {
			WMI_SWBA_EVENT swbaEvt;
			struct ath_txq *txq = ATH_TXQ(sc, 8);

			swbaEvt.tsf = ah->ah_getTsf64(ah);
			swbaEvt.beaconPendingCount = ah->ah_numTxPending(ah, sc->sc_bhalq);
			sc->sc_swba_tsf = ah->ah_getTsf64(ah);

			wmi_event(sc->tgt_wmi_handle,
				  WMI_SWBA_EVENTID,
				  &swbaEvt,
				  sizeof(WMI_SWBA_EVENT));

			ath_tx_draintxq(sc, txq);
		}

		if (status & HAL_INT_RXORN)
			sc->sc_int_stats.ast_rxorn++;

		if (status & HAL_INT_RXEOL)
			sc->sc_int_stats.ast_rxeol++;

		if (status & (HAL_INT_RX | HAL_INT_RXEOL | HAL_INT_RXORN)) {
			if (status & HAL_INT_RX)
				sc->sc_int_stats.ast_rx++;

#ifdef DEBUG_RXQUEUE
			if (status & HAL_INT_RX)
				printk("\niR");
			if (status & HAL_INT_RXEOL)
				printk("\niE");
			if (status & HAL_INT_RXORN)
				printk("\niO");
#endif

			ath_uapsd_processtriggers(sc);

			sc->sc_imask &= ~HAL_INT_RX;
			ah->ah_setInterrupts(ah, sc->sc_imask);

			ATH_SCHEDULE_TQUEUE(sc->sc_dev, &sc->sc_rxtq);
		}

		if (status & HAL_INT_TXURN) {
			sc->sc_int_stats.ast_txurn++;
			ah->ah_updateTxTrigLevel(ah, AH_TRUE);
		}

		ATH_SCHEDULE_TQUEUE(sc->sc_dev, &sc->sc_txtq);

		if (status & HAL_INT_BMISS) {
			ATH_SCHEDULE_TQUEUE(sc->sc_dev, &sc->sc_bmisstq);
		}

		if (status & HAL_INT_GTT)
			sc->sc_int_stats.ast_txto++;

		if (status & HAL_INT_CST)
			sc->sc_int_stats.ast_cst++;
	}

	return ADF_OS_IRQ_HANDLED;
}

static void ath_fatal_tasklet(TQUEUE_ARG data )
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)data;

	wmi_event(sc->tgt_wmi_handle, WMI_FATAL_EVENTID, NULL, 0);
}

static void ath_bmiss_tasklet(TQUEUE_ARG data)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)data;

	wmi_event(sc->tgt_wmi_handle, WMI_BMISS_EVENTID, NULL, 0);
}

/****************/
/* WMI Commands */
/****************/

static void ath_enable_intr_tgt(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;
	a_uint32_t intr;

	if (data)
		intr = (*(a_uint32_t *)data);

	intr = adf_os_ntohl(intr);

	if (intr & HAL_INT_SWBA) {
		sc->sc_imask |= HAL_INT_SWBA;
	} else {
		sc->sc_imask &= ~HAL_INT_SWBA;
	}

	if (intr & HAL_INT_BMISS) {
		sc->sc_imask |= HAL_INT_BMISS;
	}

	ah->ah_setInterrupts(ah, sc->sc_imask);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo,NULL, 0);
}

static void ath_init_tgt(void *Context, A_UINT16 Command,
			 A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;

	sc->sc_imask = HAL_INT_RX | HAL_INT_TX
		| HAL_INT_RXEOL | HAL_INT_RXORN
		| HAL_INT_FATAL | HAL_INT_GLOBAL;

	sc->sc_imask |= HAL_INT_GTT;

	if (ath_hal_getcapability(ah, HAL_CAP_HT))
		sc->sc_imask |= HAL_INT_CST;

	adf_os_setup_intr(sc->sc_dev, ath_intr);
	ah->ah_setInterrupts(ah, sc->sc_imask);

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_int_stats_tgt(void *Context,A_UINT16 Command, A_UINT16 SeqNo,
			      A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;

	struct fusion_stats {
		a_uint32_t ast_rx;
		a_uint32_t ast_rxorn;
		a_uint32_t ast_rxeol;
		a_uint32_t ast_txurn;
		a_uint32_t ast_txto;
		a_uint32_t ast_cst;
	};

	struct fusion_stats stats;

	stats.ast_rx = sc->sc_int_stats.ast_rx;
	stats.ast_rxorn = sc->sc_int_stats.ast_rxorn;
	stats.ast_rxeol = sc->sc_int_stats.ast_rxeol;
	stats.ast_txurn = sc->sc_int_stats.ast_txurn;
	stats.ast_txto = sc->sc_int_stats.ast_txto;
	stats.ast_cst = sc->sc_int_stats.ast_cst;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &stats, sizeof(stats));
}

static void ath_tx_stats_tgt(void *Context,A_UINT16 Command, A_UINT16 SeqNo,
			     A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;

	struct fusion_stats {
		a_uint32_t   ast_tx_xretries;
		a_uint32_t   ast_tx_fifoerr;
		a_uint32_t   ast_tx_filtered;
		a_uint32_t   ast_tx_timer_exp;
		a_uint32_t   ast_tx_shortretry;
		a_uint32_t   ast_tx_longretry;

		a_uint32_t   tx_qnull;
		a_uint32_t   tx_noskbs;
		a_uint32_t   tx_nobufs;
	};

	struct fusion_stats stats;

	stats.ast_tx_xretries = sc->sc_tx_stats.ast_tx_xretries;
	stats.ast_tx_fifoerr = sc->sc_tx_stats.ast_tx_fifoerr;
	stats.ast_tx_filtered = sc->sc_tx_stats.ast_tx_filtered;
	stats.ast_tx_timer_exp = sc->sc_tx_stats.ast_tx_timer_exp;
	stats.ast_tx_shortretry = sc->sc_tx_stats.ast_tx_shortretry;
	stats.ast_tx_longretry = sc->sc_tx_stats.ast_tx_longretry;
	stats.tx_qnull = sc->sc_tx_stats.tx_qnull;
	stats.tx_noskbs = sc->sc_tx_stats.tx_noskbs;
	stats.tx_nobufs = sc->sc_tx_stats.tx_nobufs;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &stats, sizeof(stats));
}

static void ath_rx_stats_tgt(void *Context,A_UINT16 Command, A_UINT16 SeqNo,
			     A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;

	struct fusion_stats {
		a_uint32_t   ast_rx_nobuf;
		a_uint32_t   ast_rx_send;
		a_uint32_t   ast_rx_done;
	};

	struct fusion_stats stats;

	stats.ast_rx_nobuf = sc->sc_rx_stats.ast_rx_nobuf;
	stats.ast_rx_send = sc->sc_rx_stats.ast_rx_send;
	stats.ast_rx_done = sc->sc_rx_stats.ast_rx_done;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &stats, sizeof(stats));
}

static void ath_get_tgt_version(void *Context,A_UINT16 Command, A_UINT16 SeqNo,
				A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct wmi_fw_version ver;

	ver.major = ATH_VERSION_MAJOR;
	ver.minor = ATH_VERSION_MINOR;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &ver, sizeof(ver));
}

static void ath_enable_aggr_tgt(void *Context,A_UINT16 Command, A_UINT16 SeqNo,
				A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_aggr_info *aggr = (struct ath_aggr_info *)data;
	a_uint8_t nodeindex = aggr->nodeindex;
	a_uint8_t tidno = aggr->tidno;
	struct ath_node_target *an = NULL ;
	struct ath_atx_tid  *tid = NULL;

	if (nodeindex >= TARGET_NODE_MAX) {
		goto done;
	}

	an = &sc->sc_sta[nodeindex];
	if (!an->an_valid) {
		goto done;
	}

	if (tidno >= WME_NUM_TID) {
		adf_os_print("[%s] enable_aggr with invalid tid %d(node = %d)\n",
			     __FUNCTION__, tidno, nodeindex);
		goto done;
	}

	tid = ATH_AN_2_TID(an, tidno);

	if (aggr->aggr_enable) {
		tid->flag |= TID_AGGR_ENABLED;
	} else if ( tid->flag & TID_AGGR_ENABLED ) {
		tid->flag &= ~TID_AGGR_ENABLED;
		ath_tgt_tx_cleanup(sc, an, tid, 1);
	}
done:
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_ic_update_tgt(void *Context,A_UINT16 Command, A_UINT16 SeqNo,
			      A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ieee80211com_target *ic = (struct ieee80211com_target * )data;
	struct ieee80211com_target *ictgt = &sc->sc_ic ;

	adf_os_mem_copy(ictgt, ic, sizeof(struct  ieee80211com_target));

	ictgt->ic_ampdu_limit         = adf_os_ntohl(ic->ic_ampdu_limit);

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_vap_create_tgt(void *Context, A_UINT16 Command, A_UINT16 SeqNo,
			       A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ieee80211vap_target *vap;
    	a_uint8_t vap_index;

	vap = (struct ieee80211vap_target *)data;

	vap->iv_rtsthreshold    = adf_os_ntohs(vap->iv_rtsthreshold);
	vap->iv_opmode          = adf_os_ntohl(vap->iv_opmode);

	vap_index = vap->iv_vapindex;

	adf_os_assert(sc->sc_vap[vap_index].av_valid == 0);

	adf_os_mem_copy(&(sc->sc_vap[vap_index].av_vap), vap,
			VAP_TARGET_SIZE);

	sc->sc_vap[vap_index].av_bcbuf = asf_tailq_first(&(sc->sc_bbuf));
	sc->sc_vap[vap_index].av_valid = 1;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_node_create_tgt(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ieee80211_node_target *node;
	a_uint8_t vap_index;
	a_uint8_t node_index;

	node = (struct ieee80211_node_target *)data;

	node_index = node->ni_nodeindex;

	node->ni_htcap = adf_os_ntohs(node->ni_htcap);
	node->ni_flags = adf_os_ntohs(node->ni_flags);
	node->ni_maxampdu = adf_os_ntohs(node->ni_maxampdu);

	adf_os_mem_copy(&(sc->sc_sta[node_index].ni), node,
			NODE_TARGET_SIZE);

    	vap_index = sc->sc_sta[node_index].ni.ni_vapindex;
	sc->sc_sta[node_index].ni.ni_vap = &(sc->sc_vap[vap_index].av_vap);
	if(sc->sc_sta[node_index].ni.ni_is_vapnode == 1)
		sc->sc_vap[vap_index].av_vap.iv_nodeindex = node_index;

	sc->sc_sta[node_index].an_valid = 1;
	sc->sc_sta[node_index].ni.ni_txseqmgmt = 0;
	sc->sc_sta[node_index].ni.ni_iv16 = 0;
	sc->sc_sta[node_index].ni.ni_iv32 = 0;

	owl_tgt_node_init(&sc->sc_sta[node_index]);

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_node_cleanup_tgt(void *Context, A_UINT16 Command,
				 A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	a_uint8_t node_index;
	a_uint8_t *nodedata;

	nodedata = (a_uint8_t *)data;
	node_index = *nodedata;
	sc->sc_sta[node_index].an_valid = 0;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_node_update_tgt(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ieee80211_node_target *node;
	a_uint8_t vap_index;
	a_uint8_t node_index;

	node = (struct ieee80211_node_target *)data;

	node_index = node->ni_nodeindex;

	node->ni_htcap = adf_os_ntohs(node->ni_htcap);
	node->ni_flags = adf_os_ntohs(node->ni_flags);
	node->ni_maxampdu = adf_os_ntohs(node->ni_maxampdu);

	adf_os_mem_copy(&(sc->sc_sta[node_index].ni), node,
			NODE_TARGET_SIZE);

	vap_index = sc->sc_sta[node_index].ni.ni_vapindex;
	sc->sc_sta[node_index].ni.ni_vap = &(sc->sc_vap[vap_index].av_vap);

	sc->sc_sta[node_index].ni.ni_txseqmgmt = 0;
	sc->sc_sta[node_index].ni.ni_iv16 = 0;
	sc->sc_sta[node_index].ni.ni_iv32 = 0;

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static a_int32_t ath_reg_read_filter(struct ath_hal *ah, a_int32_t addr)
{
	if ((addr & 0xffffe000) == 0x2000) {
		/* SEEPROM registers */
		ioread32_mac(addr);
		if (!ath_hal_wait(ah, 0x407c, 0x00030000, 0))
			adf_os_print("SEEPROM Read fail: 0x%08x\n", addr);

		return ioread32_mac(0x407c) & 0x0000ffff;
	} else if (addr > 0xffff)
		/* SoC registers */
		return ioread32(addr);
	else
		/* MAC registers */
		return ioread32_mac(addr);
}

static void ath_hal_reg_read_tgt(void *Context, A_UINT16 Command,
				 A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;
	a_uint32_t addr;
	a_uint32_t val[32];
	int i;

	for (i = 0; i < datalen; i += sizeof(a_int32_t)) {
		addr = *(a_uint32_t *)(data + i);
		addr = adf_os_ntohl(addr);

		val[i/sizeof(a_int32_t)] =
			adf_os_ntohl(ath_reg_read_filter(ah, addr));
	}

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &val[0], datalen);
}

static void ath_pll_reset_ones(struct ath_hal *ah)
{
	static uint8_t reset_pll = 0;

	if(reset_pll == 0) {
#if defined(PROJECT_K2)
		/* here we write to core register */
		iowrite32(MAGPIE_REG_RST_PWDN_CTRL_ADDR, 0x0);
		/* and here to mac register */
		iowrite32_mac(0x786c,
			 ioread32_mac(0x786c) | 0x6000000);
		iowrite32_mac(0x786c,
			 ioread32_mac(0x786c) & (~0x6000000));

		iowrite32(MAGPIE_REG_RST_PWDN_CTRL_ADDR, 0x20);

#elif defined(PROJECT_MAGPIE) && !defined (FPGA)
		iowrite32_mac(0x7890,
			 ioread32_mac(0x7890) | 0x1800000);
		iowrite32_mac(0x7890,
			 ioread32_mac(0x7890) & (~0x1800000));
#endif
		reset_pll = 1;
	}
}

static void ath_hal_reg_write_filter(struct ath_hal *ah,
			a_uint32_t reg, a_uint32_t val)
{
	if(reg > 0xffff) {
		iowrite32(reg, val);
#if defined(PROJECT_K2)
		if(reg == 0x50040) {
			static uint8_t flg=0;

			if(flg == 0) {
				/* reinit clock and uart.
				 * TODO: Independent on what host will
				 * here set. We do our own decision. Why? */
				A_CLOCK_INIT(117);
				A_UART_HWINIT(117*1000*1000, 19200);
				flg = 1;
			}
		}
#endif
	} else {
		if(reg == 0x7014)
			ath_pll_reset_ones(ah);

		iowrite32_mac(reg, val);
	}
}

static void ath_hal_reg_write_tgt(void *Context, A_UINT16 Command,
				  A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;
	int i;
	struct registerWrite {
		a_uint32_t reg;
		a_uint32_t val;
	}*t;

	for (i = 0; i < datalen; i += sizeof(struct registerWrite)) {
		t = (struct registerWrite *)(data+i);

		ath_hal_reg_write_filter(ah, t->reg, t->val);
	}

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_hal_reg_rmw_tgt(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *data,
				a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;
	struct register_rmw *buf = (struct register_rmw *)data;
	int i;

	for (i = 0; i < datalen;
	     i += sizeof(struct register_rmw)) {
		a_uint32_t val;
		buf = (struct register_rmw *)(data + i);

		val = ath_reg_read_filter(ah, buf->reg);
		val &= ~buf->clr;
		val |= buf->set;
		ath_hal_reg_write_filter(ah, buf->reg, val);
	}
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_vap_delete_tgt(void *Context, A_UINT16 Command,
			       A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	a_uint8_t vap_index;

	vap_index = *(a_uint8_t *)data;

	sc->sc_vap[vap_index].av_valid = 0;
	sc->sc_vap[vap_index].av_bcbuf = NULL;
	ath_node_vdelete_tgt(sc, vap_index);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_disable_intr_tgt(void *Context, A_UINT16 Command,
				 A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;

	ah->ah_setInterrupts(ah, 0);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo,NULL, 0);
}

static void ath_flushrecv_tgt(void *Context, A_UINT16 Command,
			      A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_rx_buf *bf;

	asf_tailq_foreach(bf, &sc->sc_rxbuf, bf_list)
		if (bf->bf_skb != NULL) {
			adf_nbuf_unmap(sc->sc_dev, bf->bf_dmamap,
				       ADF_OS_DMA_FROM_DEVICE);
			ath_free_rx_skb(sc, adf_nbuf_queue_remove(&bf->bf_skbhead));
			bf->bf_skb = NULL;
		}

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_tx_draintxq_tgt(void *Context, A_UINT16 Command, A_UINT16 SeqNo,
				A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	a_uint32_t q = *(a_uint32_t *)data;
	struct ath_txq *txq = NULL;

	q = adf_os_ntohl(q);
	txq = ATH_TXQ(sc, q);

	ath_tx_draintxq(sc, txq);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_draintxq_tgt(void *Context, A_UINT16 Command,
			     A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	HAL_BOOL b = (HAL_BOOL) *(a_int32_t *)data;

	ath_draintxq(Context, b);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_aborttx_dma_tgt(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;

	ah->ah_abortTxDma(sc->sc_ah);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_aborttxq_tgt(void *Context, A_UINT16 Command,
			     A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{

	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	a_uint16_t i;

	for (i = 0; i < HAL_NUM_TX_QUEUES; i++) {
		if (ATH_TXQ_SETUP(sc, i))
			ath_tx_draintxq(sc, ATH_TXQ(sc,i));
	}

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_stop_tx_dma_tgt(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;
	a_uint32_t q;

	if (data)
		q = *(a_uint32_t *)data;

	q = adf_os_ntohl(q);
	ah->ah_stopTxDma(ah, q);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_startrecv_tgt(void *Context, A_UINT16 Command,
			      A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{

	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;

	ath_startrecv(sc);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_stoprecv_tgt(void *Context, A_UINT16 Command,
			     A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;

	ah->ah_stopPcuReceive(ah);
	ah->ah_setRxFilter(ah, 0);
	ah->ah_stopDmaReceive(ah);

	sc->sc_rxlink = NULL;
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_setcurmode_tgt(void *Context, A_UINT16 Command,
			       A_UINT16 SeqNo, A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	a_uint16_t mode;

	mode= *((a_uint16_t *)data);
	mode = adf_os_ntohs(mode);

	ath_setcurmode(sc, mode);

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_detach_tgt(void *Context, A_UINT16 Command, A_UINT16 SeqNo,
				 A_UINT8 *data, a_int32_t datalen)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct ath_hal *ah = sc->sc_ah;

	ath_desc_free(sc);
	ah->ah_detach(ah);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
	adf_os_mem_free(sc);
}

static void handle_echo_command(void *pContext, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	wmi_cmd_rsp(pContext, WMI_ECHO_CMDID, SeqNo, buffer, Length);
}

static void handle_rc_state_change_cmd(void *Context, A_UINT16 Command,
				       A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)

{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct wmi_rc_state_change_cmd *wmi_data = (struct wmi_rc_state_change_cmd *)buffer;

	a_uint32_t capflag = adf_os_ntohl(wmi_data->capflag);

	ath_rate_newstate(sc, &sc->sc_vap[wmi_data->vap_index].av_vap,
			  wmi_data->vap_state,
			  capflag,
			  &wmi_data->rs);

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void handle_rc_rate_update_cmd(void *Context, A_UINT16 Command,
				      A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct wmi_rc_rate_update_cmd *wmi_data = (struct wmi_rc_rate_update_cmd *)buffer;

	a_uint32_t capflag = adf_os_ntohl(wmi_data->capflag);

	ath_rate_node_update(sc, &sc->sc_sta[wmi_data->node_index],
			     wmi_data->isNew,
			     capflag,
			     &wmi_data->rs);

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void dispatch_magpie_sys_cmds(void *pContext, A_UINT16 Command,
				     A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	adf_os_assert(0);
}

static void ath_rc_mask_tgt(void *Context, A_UINT16 Command,
			    A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	struct wmi_rc_rate_mask_cmd *wmi_data = (struct wmi_rc_rate_mask_cmd *)buffer;
	int idx, band, i;

	idx = wmi_data->vap_index;
	band = wmi_data->band;

	sc->sc_vap[idx].av_rate_mask[band] = adf_os_ntohl(wmi_data->mask);

	if (sc->sc_vap[idx].av_rate_mask[band]) {
		for (i = 0; i < RATE_TABLE_SIZE; i++) {
			if ((1 << i) & sc->sc_vap[idx].av_rate_mask[band]) {
				sc->sc_vap[idx].av_minrateidx[band] = i;
				break;
			}
		}
	} else {
		sc->sc_vap[idx].av_minrateidx[band] = 0;
	}

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, NULL, 0);
}

static void ath_dmesg(void *Context, A_UINT16 Command,
				A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	WMI_DEBUGMSG_CMD *cmd = (WMI_DEBUGMSG_CMD *)buffer;
	WMI_DEBUGMSG_RESP cmd_rsp;
	unsigned int offset;
	
	A_MEMSET(&cmd_rsp, 0, sizeof(cmd_rsp));

	offset = adf_os_ntohs(cmd->offset);
	cmd_rsp.length = get_dmesg(offset, cmd_rsp.buffer,
					 sizeof(cmd_rsp.buffer));

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &cmd_rsp, sizeof(cmd_rsp));
}

static void ath_reactivejam(void *Context, A_UINT16 Command,
			    A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	WMI_REACTIVEJAM_CMD *cmd = (WMI_REACTIVEJAM_CMD*)buffer;
	char reply[] = "OK";
	int i;

	cmd->mduration = adf_os_ntohl(cmd->mduration);

	printk("ReactJam ");
	for (i = 0; i < 5; ++i) {
		printk(itox(cmd->bssid[i]));
		printk(":");
	}
	printk(itox(cmd->bssid[5]));
	printk(" 0x");
	printk(itox(cmd->mduration));
	printk("ms\n");

	// Reactive jamming is blocking. When the duration is zero, we jam indefinitely,
	// meaning the the device will become unresponsive.
	if (cmd->mduration == 0) cmd->mduration = 0xFFFFFFFF;
	attack_reactivejam(sc, cmd->bssid, cmd->mduration);
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, reply, sizeof(reply));
}

static void ath_fastreply(void *Context, A_UINT16 Command,
			  A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	static uint8_t reply[256];
	static int replylen;
	static struct ath_tx_buf *bf = NULL;
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	WMI_FASTREPLY_CMD *cmd = (WMI_FASTREPLY_CMD*)buffer;
	int rval = 0;

	if (cmd->type == FASTREPLY_PACKET && cmd->pkt.offset + cmd->pkt.datalen < sizeof(reply))
	{
		replylen = cmd->pkt.length;
		A_MEMCPY(reply + cmd->pkt.offset, cmd->pkt.data, cmd->pkt.datalen);

		if (replylen == cmd->pkt.offset + cmd->pkt.datalen) {
			// FIXME: This memory needs to be properly freed
			int waitack = !(reply[4] & 0x01); // Don't wait for ACK on group-addressed frames
			bf = attack_build_packet(sc, reply, replylen, waitack, NULL);
			if (bf == NULL) rval = 1;
		}
	}
	else if (cmd->type == FASTREPLY_START)
	{
		unsigned int duration = adf_os_ntohl(cmd->start.mduration);

		if (bf != NULL) {
			rval = attack_fastreply(sc, bf, cmd->start.source, duration, cmd->start.jam);
		} else {
			rval = 2;
			printk("fastreply no bf\n");
		}
	}

	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &rval, sizeof(rval));
}

static void ath_constantjam(void *Context, A_UINT16 Command,
			      A_UINT16 SeqNo, A_UINT8 *buffer, a_int32_t Length)
{
	static int constjam_running = 0;
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)Context;
	WMI_CONSTANTJAM_CMD *cmd = (WMI_CONSTANTJAM_CMD*)buffer;
	WMI_CONSTANTJAM_RESP cmd_resp;

	cmd->len = adf_os_ntohs(cmd->len);

	switch (cmd->request)
	{
	case CONSTJAM_START:
		if (constjam_running) break;

		if (cmd->conf_radio) {
			// jamming of the channel, other clients can't see any traffic and sense channel busy
			printk("contjam+radio\n");
			attack_confradio(sc, 1);
			attack_constantjam_start(sc, 0, NULL, cmd->len);
		} else {
			// uninterrupted packet injection, useful to test number of packets per second possible
			printk("contjam\n");
			attack_constantjam_start(sc, 1, NULL, cmd->len);
		}

		constjam_running = 1;
		break;

	case CONSTJAM_STOP:
		if (!constjam_running) break;

		printk("stopjam\n");
		attack_constantjam_stop(sc);
		constjam_running = 0;
		break;

	case CONSTJAM_STATUS:
		// Nothing special needed, status is always filled in.
		break;
	}

	cmd_resp.status = constjam_running;
	wmi_cmd_rsp(sc->tgt_wmi_handle, Command, SeqNo, &cmd_resp, sizeof(cmd_resp));
}

static WMI_DISPATCH_ENTRY Magpie_Sys_DispatchEntries[] =
{
	{handle_echo_command,         WMI_ECHO_CMDID,               0},
	{dispatch_magpie_sys_cmds,    WMI_ACCESS_MEMORY_CMDID,      0},
	{ath_get_tgt_version,         WMI_GET_FW_VERSION,           0},
	{ath_disable_intr_tgt,        WMI_DISABLE_INTR_CMDID,       0},
	{ath_enable_intr_tgt,         WMI_ENABLE_INTR_CMDID,        0},
	{ath_init_tgt,                WMI_ATH_INIT_CMDID,           0},
	{ath_aborttxq_tgt,            WMI_ABORT_TXQ_CMDID,          0},
	{ath_stop_tx_dma_tgt,         WMI_STOP_TX_DMA_CMDID,        0},
	{ath_aborttx_dma_tgt,         WMI_ABORT_TX_DMA_CMDID,       0},
	{ath_tx_draintxq_tgt,         WMI_DRAIN_TXQ_CMDID,          0},
	{ath_draintxq_tgt,            WMI_DRAIN_TXQ_ALL_CMDID,      0},
	{ath_startrecv_tgt,           WMI_START_RECV_CMDID,         0},
	{ath_stoprecv_tgt,            WMI_STOP_RECV_CMDID,          0},
	{ath_flushrecv_tgt,           WMI_FLUSH_RECV_CMDID,         0},
	{ath_setcurmode_tgt,          WMI_SET_MODE_CMDID,           0},
	{ath_node_create_tgt,         WMI_NODE_CREATE_CMDID,        0},
	{ath_node_cleanup_tgt,        WMI_NODE_REMOVE_CMDID,        0},
	{ath_vap_delete_tgt,          WMI_VAP_REMOVE_CMDID,         0},
	{ath_vap_create_tgt,          WMI_VAP_CREATE_CMDID,         0},
	{ath_hal_reg_read_tgt,        WMI_REG_READ_CMDID,           0},
	{ath_hal_reg_write_tgt,       WMI_REG_WRITE_CMDID,          0},
	{handle_rc_state_change_cmd,  WMI_RC_STATE_CHANGE_CMDID,    0},
	{handle_rc_rate_update_cmd,   WMI_RC_RATE_UPDATE_CMDID,     0},
	{ath_ic_update_tgt,           WMI_TARGET_IC_UPDATE_CMDID,   0},
	{ath_enable_aggr_tgt,         WMI_TX_AGGR_ENABLE_CMDID,     0},
	{ath_detach_tgt,              WMI_TGT_DETACH_CMDID,         0},
	{ath_node_update_tgt,         WMI_NODE_UPDATE_CMDID,        0},
	{ath_int_stats_tgt,           WMI_INT_STATS_CMDID,          0},
	{ath_tx_stats_tgt,            WMI_TX_STATS_CMDID,           0},
	{ath_rx_stats_tgt,            WMI_RX_STATS_CMDID,           0},
	{ath_rc_mask_tgt,             WMI_BITRATE_MASK_CMDID,       0},
	{ath_hal_reg_rmw_tgt,         WMI_REG_RMW_CMDID,            0},

	/** New commands */
	{ath_dmesg,                   WMI_DEBUGMSG_CMDID,           0},
	{ath_reactivejam,             WMI_REACTIVEJAM_CMDID,        0},
	{ath_fastreply,               WMI_FASTREPLY_CMDID,          0},
	{ath_constantjam,             WMI_CONSTANTJAM_CMDID,        0},
};

/*****************/
/* Init / Deinit */
/*****************/

static void htc_setup_comp(void)
{
}

static A_UINT8 tgt_ServiceConnect(HTC_SERVICE *pService,
				  HTC_ENDPOINT_ID eid,
				  A_UINT8 *pDataIn,
				  a_int32_t LengthIn,
				  A_UINT8 *pDataOut,
				  a_int32_t *pLengthOut)
{
	struct ath_softc_tgt *sc = (struct ath_softc_tgt *)pService->ServiceCtx;

	switch(pService->ServiceID) {
	case WMI_CONTROL_SVC:
		sc->wmi_command_ep= eid;
		break;
	case WMI_BEACON_SVC:
		sc->beacon_ep= eid;
		break;
	case WMI_CAB_SVC:
		sc->cab_ep= eid;
		break;
	case WMI_UAPSD_SVC:
		sc->uapsd_ep= eid;
		break;
	case WMI_MGMT_SVC:
		sc->mgmt_ep= eid;
		break;
	case WMI_DATA_VO_SVC:
		sc->data_VO_ep = eid;
		break;
	case WMI_DATA_VI_SVC:
		sc->data_VI_ep = eid;
		break;
	case WMI_DATA_BE_SVC:
		sc->data_BE_ep = eid;
		break;
	case WMI_DATA_BK_SVC:
		sc->data_BK_ep = eid;
		break;
	default:
		adf_os_assert(0);
	}

	return HTC_SERVICE_SUCCESS;
}

static void tgt_reg_service(struct ath_softc_tgt *sc, HTC_SERVICE *svc,
			    int svcId, HTC_SERVICE_ProcessRecvMsg recvMsg)
{
	svc->ProcessRecvMsg = recvMsg;
	svc->ProcessSendBufferComplete = tgt_HTCSendCompleteHandler;
	svc->ProcessConnect = tgt_ServiceConnect;
	svc->MaxSvcMsgSize = 1600;
	svc->TrailerSpcCheckLimit = 0;
	svc->ServiceID = svcId;
	svc->ServiceCtx = sc;
	HTC_RegisterService(sc->tgt_htc_handle, svc);
}

static void tgt_hif_htc_wmi_init(struct ath_softc_tgt *sc)
{
	HTC_CONFIG htc_conf;
	WMI_SVC_CONFIG wmiConfig;
	WMI_DISPATCH_TABLE *Magpie_Sys_Commands_Tbl;

	/* Init dynamic buf pool */
	sc->pool_handle = BUF_Pool_init(sc->sc_hdl);

	/* Init target-side HIF */
	sc->tgt_hif_handle = HIF_init(0);

	/* Init target-side HTC */
	htc_conf.HIFHandle = sc->tgt_hif_handle;
	htc_conf.CreditSize = 320;
	htc_conf.CreditNumber = ATH_TXBUF;
	htc_conf.OSHandle = sc->sc_hdl;
	htc_conf.PoolHandle = sc->pool_handle;
	sc->tgt_htc_handle = HTC_init(htc_setup_comp, &htc_conf);
#if defined(PROJECT_MAGPIE)
	init_htc_handle = sc->tgt_htc_handle;
#endif

	tgt_reg_service(sc, &sc->htc_beacon_service, WMI_BEACON_SVC, tgt_HTCRecv_beaconhandler);
	tgt_reg_service(sc, &sc->htc_cab_service, WMI_CAB_SVC, tgt_HTCRecv_cabhandler);
	tgt_reg_service(sc, &sc->htc_uapsd_service, WMI_UAPSD_SVC, tgt_HTCRecv_uapsdhandler);
	tgt_reg_service(sc, &sc->htc_mgmt_service, WMI_MGMT_SVC, tgt_HTCRecv_mgmthandler);
	tgt_reg_service(sc, &sc->htc_data_BE_service, WMI_DATA_BE_SVC, tgt_HTCRecvMessageHandler);
	tgt_reg_service(sc, &sc->htc_data_BK_service, WMI_DATA_BK_SVC, tgt_HTCRecvMessageHandler);
	tgt_reg_service(sc, &sc->htc_data_VI_service, WMI_DATA_VI_SVC, tgt_HTCRecvMessageHandler);
	tgt_reg_service(sc, &sc->htc_data_VO_service, WMI_DATA_VO_SVC, tgt_HTCRecvMessageHandler);

	/* Init target-side WMI */
	Magpie_Sys_Commands_Tbl = (WMI_DISPATCH_TABLE *)adf_os_mem_alloc(sizeof(WMI_DISPATCH_TABLE));
	adf_os_mem_zero(Magpie_Sys_Commands_Tbl, sizeof(WMI_DISPATCH_TABLE));
	Magpie_Sys_Commands_Tbl->NumberOfEntries = WMI_DISPATCH_ENTRY_COUNT(Magpie_Sys_DispatchEntries);
	Magpie_Sys_Commands_Tbl->pTable = Magpie_Sys_DispatchEntries;

	adf_os_mem_zero(&wmiConfig, sizeof(WMI_SVC_CONFIG));
	wmiConfig.HtcHandle = sc->tgt_htc_handle;
	wmiConfig.PoolHandle = sc->pool_handle;
	wmiConfig.MaxCmdReplyEvts = ATH_WMI_MAX_CMD_REPLY;
	wmiConfig.MaxEventEvts = ATH_WMI_MAX_EVENTS;

	sc->tgt_wmi_handle = WMI_Init(&wmiConfig);
	Magpie_Sys_Commands_Tbl->pContext = sc;
	WMI_RegisterDispatchTable(sc->tgt_wmi_handle, Magpie_Sys_Commands_Tbl);

	HTC_NotifyTargetInserted(sc->tgt_htc_handle);

	/* Start HTC messages exchange */
	HTC_Ready(sc->tgt_htc_handle);
}

a_int32_t ath_tgt_attach(a_uint32_t devid, struct ath_softc_tgt *sc, adf_os_device_t osdev)
{
	struct ath_hal *ah;
	HAL_STATUS status;
	a_int32_t error = 0, i, flags = 0;
	a_uint8_t csz;

	adf_os_pci_config_read8(osdev, ATH_PCI_CACHE_LINE_SIZE, &csz);

	if (csz == 0)
		csz = 16;
	sc->sc_cachelsz = csz << 2;

	sc->sc_dev = osdev;
	sc->sc_hdl = osdev;

	ATH_INIT_TQUEUE(sc->sc_dev, &sc->sc_rxtq, ath_tgt_rx_tasklet, sc);
	ATH_INIT_TQUEUE(sc->sc_dev, &sc->sc_txtq, owl_tgt_tx_tasklet, sc);
	ATH_INIT_TQUEUE(sc->sc_dev, &sc->sc_bmisstq, ath_bmiss_tasklet, sc);
	ATH_INIT_TQUEUE(sc->sc_dev, &sc->sc_fataltq, ath_fatal_tasklet, sc);

	flags |= AH_USE_EEPROM;
	ah = _ath_hal_attach_tgt(devid, sc, sc->sc_dev, flags, &status);
	if (ah == NULL) {
		error = ENXIO;
		goto bad;
	}
	sc->sc_ah = ah;

	tgt_hif_htc_wmi_init(sc);

	sc->sc_bhalq = HAL_NUM_TX_QUEUES - 1;

	ath_rate_setup(sc, IEEE80211_MODE_11NA);
	ath_rate_setup(sc, IEEE80211_MODE_11NG);

	sc->sc_rc = ath_rate_attach(sc);
	if (sc->sc_rc == NULL) {
		error = EIO;
		goto bad2;
	}

	for (i=0; i < TARGET_NODE_MAX; i++) {
		sc->sc_sta[i].an_rcnode = adf_os_mem_alloc(sc->sc_rc->arc_space);
	}

	error = ath_desc_alloc(sc);
	if (error != 0) {
		goto bad;
	}

	BUF_Pool_create_pool(sc->pool_handle, POOL_ID_WLAN_RX_BUF, ath_numrxdescs, 1664);
	BUF_Pool_create_pool(sc->pool_handle, POOL_ID_ATTACKS, 5, 300);

	ath_tgt_txq_setup(sc);
	sc->sc_imask =0;
	ah->ah_setInterrupts(ah, 0);

	return 0;
bad:
bad2:
	ath_desc_free(sc);
	if (ah)
		ah->ah_detach(ah);
}

static void tgt_hif_htc_wmi_shutdown(struct ath_softc_tgt *sc)
{
	HTC_NotifyTargetDetached(sc->tgt_htc_handle);

	WMI_Shutdown(sc->tgt_wmi_handle);
	HTC_Shutdown(sc->tgt_htc_handle);
	HIF_shutdown(sc->tgt_hif_handle);
	BUF_Pool_shutdown(sc->pool_handle);
}

a_int32_t ath_detach(struct ath_softc_tgt *sc)
{
	tgt_hif_htc_wmi_shutdown(sc);
}
