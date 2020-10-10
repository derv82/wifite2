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
#ifndef _WLAN_HDR_H
#define _WLAN_HDR_H

/* Please make sure the size of ALL headers is on word alignment */

#define	M_FF 0x02 /* fast frame */

#define RX_STATS_SIZE 10

struct  rx_frame_header {
	a_uint32_t rx_stats[RX_STATS_SIZE];
};

#define ATH_DATA_TYPE_AGGR       0x1
#define ATH_DATA_TYPE_NON_AGGR   0x2
#define ATH_HTC_TX_ASSIGN_SEQ    0x10
#define ATH_HTC_TX_NO_ACK        0x20
#define ATH_SHORT_PREAMBLE       0x1

typedef struct _mgt_header {
	a_uint8_t   ni_index;
	a_uint8_t   vap_index;
	a_uint8_t   tidno;
	a_uint8_t   flags;
	a_int8_t    keytype;
	a_int8_t    keyix;
	a_uint8_t   cookie;
	a_uint8_t   pad;
} POSTPACK ath_mgt_hdr_t;

typedef struct _beacon_header {
	a_uint8_t   vap_index;   
	a_uint8_t   len_changed;    
	a_uint16_t  reserved;
} ath_beacon_hdr_t;

#define	M_LINK0		0x01			/* frame needs WEP encryption */
#define M_UAPSD		0x08			/* frame flagged for u-apsd handling */

/* Tx frame header flags definition */
//Reserved bit-0 for selfCTS
//Reserved bit-1 for RTS
#define TFH_FLAGS_USE_MIN_RATE                      0x100

typedef struct __data_header {
	a_uint8_t   datatype;
	a_uint8_t   ni_index;
	a_uint8_t   vap_index;
	a_uint8_t   tidno;
	a_uint32_t  flags;  
	a_int8_t    keytype;
	a_int8_t    keyix;
	a_uint8_t   cookie;
	a_uint8_t   pad;
} POSTPACK ath_data_hdr_t;

#define RX_HEADER_SPACE     HTC_HDR_LENGTH + sizeof(struct rx_frame_header)

struct ieee80211com_target {
	a_uint32_t    ic_ampdu_limit;
	a_uint8_t     ic_ampdu_subframes;
	a_uint8_t     ic_enable_coex;
	a_uint8_t     ic_tx_chainmask;
	a_uint8_t     pad;
};

#define ATH_NODE_MAX 8       /* max no. of nodes */
#define ATH_VAP_MAX  2       /* max no. of vaps */

#define VAP_TARGET_SIZE 12

struct ieee80211vap_target 
{
	a_uint8_t               iv_vapindex;
	a_uint8_t               iv_opmode; /* enum ieee80211_opmode */
	a_uint8_t               iv_myaddr[IEEE80211_ADDR_LEN];
	a_uint8_t               iv_ath_cap;
	a_uint16_t              iv_rtsthreshold;
	a_uint8_t               pad;

	/* Internal */
	a_uint8_t               iv_nodeindex;
	struct ieee80211_node_target *iv_bss;
};

/* NB: this must have the same value as IEEE80211_FC1_PWR_MGT */
#define	IEEE80211_NODE_PWR_MGT	0x0010		/* power save mode enabled */
#define	IEEE80211_NODE_AREF	0x0020		/* authentication ref held */
#define IEEE80211_NODE_UAPSD	0x0040		/* U-APSD power save enabled */
#define IEEE80211_NODE_UAPSD_TRIG 0x0080	/* U-APSD triggerable state */
#define IEEE80211_NODE_UAPSD_SP	0x0100		/* U-APSD SP in progress */
#define	IEEE80211_NODE_ATH	0x0200		/* Atheros Owl or follow-on device */
#define	IEEE80211_NODE_OWL_WORKAROUND	0x0400	/* Owl WDS workaround needed*/
#define	IEEE80211_NODE_WDS	0x0800		/* WDS link */

#define NODE_TARGET_SIZE 22

struct ieee80211_node_target
{
	a_uint8_t       ni_macaddr[IEEE80211_ADDR_LEN];
	a_uint8_t       ni_bssid[IEEE80211_ADDR_LEN];
	a_uint8_t       ni_nodeindex;
	a_uint8_t       ni_vapindex;
	a_uint8_t       ni_is_vapnode;
	a_uint16_t      ni_flags;
	a_uint16_t 	ni_htcap;
	a_uint16_t      ni_maxampdu;
	a_uint8_t       pad;

	/*
	 * Internal.
	 * Should move to ath_node_target later on ...
	 */
	a_uint16_t ni_txseqmgmt;
	a_uint16_t ni_iv16;
	a_uint32_t ni_iv32;
	struct ieee80211vap_target *ni_vap;
};

struct ath_interrupt_stats {
	a_uint32_t ast_rx;
	a_uint32_t ast_rxorn;
	a_uint32_t ast_rxeol;
	a_uint32_t ast_txurn;
	a_uint32_t ast_txto;
	a_uint32_t ast_cst;
};

struct ath_tx_stats {
	a_uint32_t   ast_tx_xretries;    /* tx failed 'cuz too many retries */
	a_uint32_t   ast_tx_fifoerr;     /* tx failed 'cuz FIFO underrun */
	a_uint32_t   ast_tx_filtered;    /* tx failed 'cuz xmit filtered */
	a_uint32_t   ast_tx_timer_exp;   /* tx timer expired */
	a_uint32_t   ast_tx_shortretry;  /* tx on-chip retries (short) */
	a_uint32_t   ast_tx_longretry;   /* tx on-chip retries (long) */

	a_uint32_t   ast_tx_rts;         /* tx frames with rts enabled */
	a_uint32_t   ast_tx_altrate;     /* tx frames with alternate rate */
	a_uint32_t   ast_tx_protect;     /* tx frames with protection */

	a_uint32_t   tx_tgt;	         /* tx data pkts recieved on target */  
	a_uint32_t   tx_qnull;           /* txq empty occurences */

	a_uint32_t   txaggr_nframes;     /* no. of frames aggregated */
	a_uint32_t   tx_compunaggr;      /* tx unaggregated frame completions */ 
	a_uint32_t   tx_compaggr;        /* tx aggregated completions */
	a_uint32_t   txaggr_retries;     /* tx retries of sub frames */
	a_uint32_t   txaggr_single;      /* tx frames not aggregated */
	a_uint32_t   txaggr_compgood;    /* tx aggr good completions */
	a_uint32_t   txaggr_compretries; /* tx aggr unacked subframes */
	a_uint32_t   txaggr_prepends;    /* tx aggr old frames requeued */
	a_uint32_t   txaggr_data_urun;   /* data underrun for an aggregate */
	a_uint32_t   txaggr_delim_urun;  /* delimiter underrun for an aggr */
	a_uint32_t   txaggr_errlast;     /* tx aggr: last sub-frame failed */
	a_uint32_t   txaggr_longretries; /* tx aggr h/w long retries */
	a_uint32_t   txaggr_babug;       /* tx aggr : BA bug */
	a_uint32_t   txaggr_compxretry;  /* tx aggr excessive retries */
	a_uint32_t   txaggr_shortretries;/* tx aggr h/w short retries */
	a_uint32_t   txaggr_timer_exp;   /* tx aggr : tx timer expired */
	a_uint32_t   txunaggr_compretries; /* tx non-aggr unacked subframes */
	a_uint32_t   txaggr_filtered;    /* filtered aggr packet */
	a_uint32_t   txaggr_fifo;        /* fifo underrun of aggregate */
	a_uint32_t   txaggr_xtxop;       /* txop exceeded for an aggregate */
	a_uint32_t   txaggr_desc_cfgerr; /* aggr descriptor config error */
	a_uint32_t   txunaggr_errlast;   /* tx non-aggr: last frame failed */
	a_uint32_t   txunaggr_xretry;    /* tx unaggregated excessive retries */
	a_uint32_t   txaggr_xretries;    /* tx excessive retries of aggr */

	a_uint32_t   tx_stopfiltered;    /* tx pkts filtered for requeueing */
	a_uint32_t   tx_noskbs;          /* tx no skbs for encapsulations */
	a_uint32_t   tx_nobufs;          /* tx no descriptors */

	a_uint32_t   tx_bars;            /* tx bars sent */
	a_uint32_t   txbar_xretry;       /* tx bars excessively retried */
	a_uint32_t   txbar_compretries;  /* tx bars retried */
	a_uint32_t   txbar_errlast;      /* tx bars last frame failed */
};

struct ath_rx_stats {
	a_uint32_t   ast_rx_nobuf;       /* rx setup failed 'cuz no skbuff */
	a_uint32_t   ast_rx_send;
	a_uint32_t   ast_rx_done;
};

struct ath_aggr_info {
	a_uint8_t nodeindex;
	a_uint8_t tidno;
	a_uint8_t aggr_enable;
	a_uint8_t padding;
};    

struct wmi_data_delba {
	a_uint8_t  ni_nodeindex;
	a_uint8_t  tidno;
	a_uint8_t  initiator;
	a_uint8_t reasoncode;
};

struct wmi_fw_version {
	a_uint16_t major;
	a_uint16_t minor;
};

#endif 
