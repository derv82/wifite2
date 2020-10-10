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

#ifndef _DEV_ATH_ATHVAR_H
#define _DEV_ATH_ATHVAR_H


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
#include <asf_queue.h>
#include "ah.h"

#include "ieee80211_var.h"
#include "ieee80211_node.h"
#include "if_athrate.h"
#include <osapi.h>
#include <Magpie_api.h>
#include <htc_services.h>
#include <htc.h>
#include <wlan_hdr.h>
#include <wlan_cfg.h>

#define tq_struct adf_os_bh_t
#define ATH_INIT_TQUEUE(a,b,c,d)      adf_os_init_bh((a),(b),(c),(void *)(d))
#define ATH_SCHEDULE_TQUEUE(a,b)      adf_os_sched_bh((a),(b))
typedef void * TQUEUE_ARG;

#define ATH_MIN(a,b)        ((a) < (b) ? (a) : (b))
#define ATH_AC_2_TXQ(_sc, _ac)      (_sc)->sc_ac2q[(_ac)]
#define TID_TO_ACTXQ(tidno)         sc->sc_ac2q[ TID_TO_WME_AC(tidno)]

#define RATE_TABLE_SIZE             32

#define INCR(_l, _sz)   (_l) ++; (_l) &= ((_sz) - 1)

#define IEEE80211_SEQ_MAX       4096
#define SEQNO_FROM_BF_SEQNO(_x) (_x >> IEEE80211_SEQ_SEQ_SHIFT)
#define BAW_WITHIN(_start, _bawsz, _seqno)      \
	((((_seqno) - (_start)) & 4095) < (_bawsz))

#define __stats(sc, _x)         sc->sc_tx_stats._x ++
#define __statsn(sc, _x, _n)    sc->sc_tx_stats._x += _n

#define IS_HT_RATE(_rate)     ((_rate) & 0x80)

typedef enum {
	ATH_TGT_AGGR_DONE,
	ATH_TGT_AGGR_BAW_CLOSED,
	ATH_TGT_AGGR_LIMITED,
	ATH_AGGR_SHORTPKT,
	ATH_AGGR_8K_LIMITED,
} ATH_AGGR_STATUS;

#define ATH_BA_ISSET(_bm, _n)        (((_n) < (WME_BA_BMP_SIZE)) &&	\
				      ((_bm)[(_n) >> 5] & (1 << ((_n) & 31))))

#define ATH_DS_BA_SEQ(_ds)          ((struct ath_tx_desc *)_ds)->ds_us.tx.ts_seqnum
#define ATH_DS_BA_BITMAP(_ds)       (&((struct ath_tx_desc *)_ds)->ds_us.tx.ba_low)
#define ATH_DS_TX_BA(_ds)           (((struct ath_tx_desc *)_ds)->ds_us.tx.ts_flags & HAL_TX_BA)
#define ATH_DS_TX_STATUS(_ds)       ((struct ath_tx_desc *)_ds)->ds_us.tx.ts_status
#define ATH_DS_TX_FLAGS(_ds)        ((struct ath_tx_desc *)_ds)->ds_us.tx.ts_flags
#define ATH_BA_INDEX(_st, _seq)     (((_seq) - (_st)) & (IEEE80211_SEQ_MAX - 1))

#define ATH_AGGR_DELIM_SZ       4
#define ATH_AGGR_MINPLEN        256
#define ATH_AGGR_ENCRYPTDELIM   10

#define ATH_AGGR_GET_NDELIM(_len)					\
	(((((_len) + ATH_AGGR_DELIM_SZ) < ATH_AGGR_MINPLEN) ?           \
	  (ATH_AGGR_MINPLEN - (_len) - ATH_AGGR_DELIM_SZ) : 0) >> 2)

#define PADBYTES(_len)   ((4 - ((_len) % 4)) % 4)
#define OWLMAX_RETRIES   10
#define OWLMAX_BAR_RETRIES 10

#define ATH_AN_2_TID(_an, _tidno)   (&(_an)->tid[(_tidno)])
#define ATH_TXDESC  1

#define ATH_TXMAXTRY    11
#define TARGET_NODE_MAX ATH_NODE_MAX
#define TARGET_VAP_MAX  ATH_VAP_MAX

#define MAX_RATE_POWER               63
#define ATH_COMP_PROC_NO_COMP_NO_CCS 3

#define ATH_BUFSTATUS_DONE 0x00000001 /* hw processing complete, desc processed by hal */

#define ATH_AGGR_MIN_QDEPTH 1

struct ath_softc_tgt;
struct ath_buf;
struct ath_txq;

#define ATH_TXQ(_sc, _qi)           (&(_sc)->sc_txq[(_qi)])
#define ATH_TXQ_SETUP(sc, i)        ((sc)->sc_txqsetup & (1<<i))

#define ATH_NODE_TARGET(_n) ((struct ath_node_target *)(_n))

/*
 * Built-in implementation for skb free.
 */
#define ath_free_rx_skb(_sc,_skb)                   BUF_Pool_free_buf(_sc->pool_handle, POOL_ID_WLAN_RX_BUF, _skb)
#define ath_free_tx_skb(_htc_handle, endpt, _skb)   HTC_ReturnBuffers(_htc_handle, endpt, _skb);

struct ath_tx_buf;

typedef void (*ath_txq_add_fn_t)(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);
typedef void (*ath_tx_comp_fn_t)(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);

struct ath_buf_state {
	ath_tx_comp_fn_t        bfs_comp;           /* completion function          */
	ath_txq_add_fn_t        bfs_txq_add;        /* txq buffer add function      */
	a_uint16_t              bfs_pktlen;         /* pktlen including crc         */
	a_uint16_t              bfs_seqno;          /* sequence nuber               */
	a_uint8_t               bfs_hdrlen;         /* header length                */
	a_uint8_t               bfs_keyix;          /* key index                    */
	a_uint8_t               bfs_atype;          /* packet type                  */
	a_uint8_t               bfs_ndelim;         /* # delims for padding         */
	a_uint8_t               bfs_nframes;        /* # frames in aggregate        */
	a_uint8_t               bfs_tidno;          /* tid of the buffer            */
	a_uint16_t              bfs_al;             /* length of aggregate          */
	struct ath_rc_series    bfs_rcs[4];         /* rate series                  */
	struct ath_txq          *bfs_txq;           /* transmit h/w queue           */
	a_uint8_t               bfs_protmode;       /* protection mode              */
	a_uint8_t               bfs_keytype;        /* encr key type                */
	a_uint8_t               bfs_retries;        /* current retries              */
	a_uint32_t              bfs_ismcast  : 1;   /* is multicast                 */
	a_uint32_t              bfs_shpream  : 1;   /* use short preamble           */
	a_uint32_t              bfs_isaggr   : 1;   /* is an aggregate              */
	a_uint32_t              bfs_isretried: 1;   /* is retried                   */
};

#define bf_comp           bf_state.bfs_comp
#define bf_txq_add        bf_state.bfs_txq_add
#define bf_pktlen         bf_state.bfs_pktlen
#define bf_hdrlen         bf_state.bfs_hdrlen
#define bf_keyix          bf_state.bfs_keyix
#define bf_atype          bf_state.bfs_atype
#define bf_seqno          bf_state.bfs_seqno
#define bf_ndelim         bf_state.bfs_ndelim
#define bf_nframes        bf_state.bfs_nframes
#define bf_al             bf_state.bfs_al
#define bf_tidno          bf_state.bfs_tidno
#define bf_rcs            bf_state.bfs_rcs
#define bf_txq            bf_state.bfs_txq
#define bf_protmode       bf_state.bfs_protmode
#define bf_keytype        bf_state.bfs_keytype
#define bf_ismcast        bf_state.bfs_ismcast
#define bf_shpream        bf_state.bfs_shpream
#define bf_isaggr         bf_state.bfs_isaggr
#define bf_isretried      bf_state.bfs_isretried
#define bf_retries        bf_state.bfs_retries

#define ATH_GENERIC_BUF                     \
    adf_os_dma_map_t      bf_dmamap;	    \
    adf_os_dmamap_info_t  bf_dmamap_info;   \
    struct ieee80211_node_target *bf_node;  \
    adf_nbuf_queue_t      bf_skbhead;	    \
    adf_nbuf_t            bf_skb;

struct ath_buf
{
    ATH_GENERIC_BUF
    asf_tailq_entry(ath_buf)  bf_list;
    struct ath_buf        *bf_next;
    struct ath_desc 	  *bf_lastds;
    struct ath_desc       *bf_desc;
    struct ath_desc       *bf_descarr;
};

struct ath_tx_buf
{
	ATH_GENERIC_BUF
	asf_tailq_entry(ath_tx_buf)  bf_list;
	struct ath_tx_buf	     *bf_next;
	struct ath_tx_desc	     *bf_desc;
	struct ath_tx_desc	     *bf_descarr;
	struct ath_tx_desc	     *bf_lastds;
	struct ath_buf_state  bf_state;
	a_uint16_t            bf_flags;
	HTC_ENDPOINT_ID       bf_endpt;
	a_uint16_t            al_delta;
	a_uint8_t             bf_cookie;
};

struct ath_rx_buf
{
	ATH_GENERIC_BUF
	asf_tailq_entry(ath_rx_buf)  bf_list;
	struct ath_rx_buf	     *bf_next;
	struct ath_rx_desc	     *bf_desc;
	struct ath_rx_desc	     *bf_descarr;
	struct ath_rx_desc	     *bf_lastds;
	a_uint32_t            bf_status;
	struct ath_rx_status  bf_rx_status;
};

#define ATH_BUF_GET_DESC_PHY_ADDR(bf)                       (a_uint32_t)bf->bf_desc
#define ATH_BUF_GET_DESC_PHY_ADDR_WITH_IDX(bf, idx)         (adf_os_dma_addr_t)(&bf->bf_descarr[idx])
#define ATH_BUF_SET_DESC_PHY_ADDR(bf, addr)
#define ATH_BUF_SET_DESC_PHY_ADDR_WITH_IDX(bf, idx, addr)

typedef asf_tailq_head(ath_deschead_s, ath_rx_desc) ath_deschead;
typedef asf_tailq_head(ath_bufhead_s, ath_buf) ath_bufhead;
typedef asf_tailq_head(ath_rx_bufhead_s, ath_rx_buf) ath_rx_bufhead;
typedef asf_tailq_head(ath_tx_bufhead_s, ath_tx_buf) ath_tx_bufhead;

#define WME_NUM_TID 8
#define WME_BA_BMP_SIZE 64
#define WME_MAX_BA WME_BA_BMP_SIZE
#define ATH_TID_MAX_BUFS (2 * WME_MAX_BA)
#define TID_CLEANUP_INPROGRES 0x1
#define TID_AGGR_ENABLED 0x2
#define TID_REINITIALIZE 0x4

#define TAILQ_DEQ(_q, _elm, _field) do {			\
		(_elm) = asf_tailq_first((_q));			\
		if (_elm) {					\
			asf_tailq_remove((_q), (_elm), _field); \
		}						\
	} while (0)

#define TX_BUF_BITMAP_SIZE  32
#define TX_BUF_BITMAP_SET(bitmap, i)     bitmap[i>>5] |= ((a_uint32_t)1 << (i&0x1f))
#define TX_BUF_BITMAP_CLR(bitmap, i)     bitmap[i>>5] &= (~((a_uint32_t)1 << (i&0x1f)))
#define TX_BUF_BITMAP_IS_SET(bitmap, i) ((bitmap[i>>5] & ((a_uint32_t)1 << (i&0x1f))) != 0)

typedef struct ath_atx_tid {
	a_int32_t          tidno;
	a_uint16_t         seq_start;
	a_uint16_t         seq_next;
	a_uint16_t         baw_size;
	a_int32_t          baw_head;
	a_int32_t          baw_tail;
	a_uint32_t         tx_buf_bitmap[ATH_TID_MAX_BUFS/TX_BUF_BITMAP_SIZE];
	asf_tailq_entry(ath_atx_tid) tid_qelem;
	asf_tailq_head(ath_tid_rbq,ath_tx_buf) buf_q;
	a_int8_t           paused;
	a_int8_t           sched;
	a_uint8_t          flag;
	a_int8_t           incomp;
	struct ath_node_target  *an;
} ath_atx_tid_t;

struct ath_node_target {
	struct ieee80211_node_target ni;
	struct ath_atx_tid tid[WME_NUM_TID];
	a_int8_t an_valid;
	void *an_rcnode;
};

struct ath_descdma {
	const a_int8_t    *dd_name;
	struct ath_desc   *dd_desc;
	adf_os_dma_map_t  dd_desc_dmamap;
	adf_os_dma_addr_t dd_desc_paddr;
	adf_os_size_t     dd_desc_len;
	struct ath_buf    *dd_bufptr;
};

struct ath_txq {
	a_uint32_t           axq_qnum;
	a_uint32_t           *axq_link;
	asf_tailq_head(,ath_tx_buf) axq_q;
	a_uint32_t           axq_depth;
	struct  ath_tx_buf     *axq_linkbuf;
	asf_tailq_head(,ath_atx_tid) axq_tidq;
};

struct wmi_rc_rate_mask_cmd {
	a_uint8_t vap_index;
	a_uint8_t band;
	a_uint32_t mask;
	a_uint16_t pad;
} POSTPACK;

struct ath_vap_target {
	struct ieee80211vap_target      av_vap;
	struct ath_txq                  av_mcastq;
	struct ath_tx_buf		*av_bcbuf;
	a_uint32_t                      av_rate_mask[2];  /* 0 - 2G, 1 - 5G */
	a_uint8_t                       av_minrateidx[2]; /* 0 - 2G, 1 - 5G */
	a_int8_t                        av_valid;
};

#define ATH_RXBUF_RESET(bf) \
	bf->bf_status=0

struct ath_softc_tgt
{
	/* Target-side HTC/HIF/WMI related data structure */
	pool_handle_t     pool_handle;
	hif_handle_t      tgt_hif_handle;
	htc_handle_t      tgt_htc_handle;
	wmi_handle_t      tgt_wmi_handle;

	/* Target HTC Service IDs */
	HTC_SERVICE       htc_beacon_service;
	HTC_SERVICE       htc_cab_service;
	HTC_SERVICE       htc_uapsd_service;
	HTC_SERVICE       htc_mgmt_service;
	HTC_SERVICE       htc_data_VO_service;
	HTC_SERVICE       htc_data_VI_service;
	HTC_SERVICE       htc_data_BE_service;
	HTC_SERVICE       htc_data_BK_service;


	/* Target HTC Endpoint IDs */
	HTC_ENDPOINT_ID   wmi_command_ep;
	HTC_ENDPOINT_ID   beacon_ep;
	HTC_ENDPOINT_ID   cab_ep;
	HTC_ENDPOINT_ID   uapsd_ep;
	HTC_ENDPOINT_ID   mgmt_ep;
	HTC_ENDPOINT_ID   data_VO_ep;
	HTC_ENDPOINT_ID   data_VI_ep;
	HTC_ENDPOINT_ID   data_BE_ep;
	HTC_ENDPOINT_ID   data_BK_ep;

	adf_os_handle_t         sc_hdl;
	adf_os_device_t         sc_dev;
	a_uint8_t               sc_bhalq;
	struct ath_ratectrl    *sc_rc;

	a_uint32_t            sc_invalid : 1,
		sc_tx_draining         : 1,
		sc_enable_coex         : 1;

	a_int32_t        sc_rxbufsize;
	a_uint16_t       sc_cachelsz;

	struct ath_interrupt_stats sc_int_stats;
	struct ath_tx_stats sc_tx_stats;
	struct ath_rx_stats sc_rx_stats;

 	const HAL_RATE_TABLE    *sc_rates[IEEE80211_MODE_MAX];
 	const HAL_RATE_TABLE    *sc_currates;

	a_uint8_t        sc_rixmap[256];

	enum ieee80211_phymode sc_curmode;

	a_uint8_t         sc_protrix;
	HAL_INT           sc_imask;

	tq_struct         sc_rxtq;
   	tq_struct         sc_bmisstq;
   	tq_struct         sc_txtotq;
   	tq_struct         sc_fataltq;

	ath_rx_bufhead     sc_rxbuf;

	ath_deschead       sc_rxdesc_idle;
	ath_deschead	   sc_rxdesc;
	struct ath_rx_desc    *sc_rxdesc_held;

	struct ath_tx_buf    *sc_txbuf_held;

	struct ath_descdma  sc_rxdma;
   	struct ath_descdma  sc_txdma;
	struct ath_descdma  sc_bdma;

	a_uint32_t	   *sc_rxlink;
	ath_tx_bufhead     sc_txbuf;
  	a_uint8_t          sc_txqsetup;

	struct ath_txq     sc_txq[HAL_NUM_TX_QUEUES];
	struct ath_txq     *sc_ac2q[WME_NUM_AC];
	tq_struct          sc_txtq;

	struct ath_hal 		   *sc_ah;
	struct ath_txq             *sc_cabq;
	struct ath_txq		   *sc_uapsdq;
	struct ath_node_target     sc_sta[TARGET_NODE_MAX];
	struct ath_vap_target      sc_vap[TARGET_VAP_MAX];
	struct ieee80211com_target sc_ic;

	ath_tx_bufhead         sc_bbuf;
	a_uint64_t          sc_swba_tsf;

	WMI_TXSTATUS_EVENT  tx_status[2];
};

#define SM(_v, _f)  (((_v) << _f##_S) & _f)
#define MS(_v, _f)  (((_v) & _f) >> _f##_S)

#define ATH9K_HTC_TXSTAT_ACK        1<<0
#define ATH9K_HTC_TXSTAT_FILT       1<<1
#define ATH9K_HTC_TXSTAT_RTC_CTS    1<<2
#define ATH9K_HTC_TXSTAT_MCS        1<<3
#define ATH9K_HTC_TXSTAT_CW40       1<<4
#define ATH9K_HTC_TXSTAT_SGI        1<<5

#define ATH9K_HTC_TXSTAT_RATE       0x0f
#define ATH9K_HTC_TXSTAT_RATE_S     0
#define ATH9K_HTC_TXSTAT_EPID       0xf0
#define ATH9K_HTC_TXSTAT_EPID_S     4

#define TAILQ_INSERTQ_HEAD(head, tq, field) do {			\
		if ((head)->tqh_first) {                                \
			*(tq)->tqh_last = (head)->tqh_first;		\
			(head)->tqh_first->field.tqe_prev = (tq)->tqh_last; \
		} else {                                                \
			(head)->tqh_last = (tq)->tqh_last;		\
		}                                                       \
		(head)->tqh_first = (tq)->tqh_first;                    \
		(tq)->tqh_first->field.tqe_prev = &(head)->tqh_first;   \
	} while (0)

#define ATH_TXQ_INSERT_TAIL(_tq, _elm, _field) do {			\
		asf_tailq_insert_tail( &(_tq)->axq_q, (_elm), _field);	\
		(_tq)->axq_depth++;					\
		(_tq)->axq_linkbuf = (_elm);				\
	} while (0)
#define ATH_TXQ_REMOVE_HEAD(_tq, _elm, _field) do {			\
		asf_tailq_remove(&(_tq)->axq_q, (_elm), _field);	\
		(_tq)->axq_depth--;					\
	} while (0)

struct ieee80211_rate {
	struct ieee80211_rateset rates;
	struct ieee80211_rateset htrates;
} __attribute__((packed));

struct wmi_rc_state_change_cmd {
	a_uint8_t  vap_index;
	a_uint8_t  vap_state;
	a_uint8_t  pad[2];
	a_uint32_t capflag;
	struct ieee80211_rate rs;
} __attribute__((packed));

struct wmi_rc_rate_update_cmd {
	a_uint8_t  node_index;
	a_uint8_t  isNew;
	a_uint8_t  pad[2];
	a_uint32_t capflag;
	struct ieee80211_rate rs;
} __attribute__((packed));

typedef enum {
	OWL_TXQ_ACTIVE = 0,
	OWL_TXQ_STOPPED,
	OWL_TXQ_FILTERED,
} owl_txq_state_t;

a_uint8_t ath_get_minrateidx(struct ath_softc_tgt *sc, struct ath_vap_target *avp);

#endif /* _DEV_ATH_ATHVAR_H */
