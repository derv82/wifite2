/*-
 * Copyright (c) 2004 Sam Leffler, Errno Consulting
 * Copyright (c) 2004 Video54 Technologies, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer,
    without modification.
 * 2. Redistributions in binary form must reproduce at minimum a disclaimer
 *    similar to the "NO WARRANTY" disclaimer below ("Disclaimer") and any
 *    redistribution must be conditioned upon including a substantially
 *    similar Disclaimer requirement for further binary redistribution.
 * 3. Neither the names of the above-listed copyright holders nor the names
 *    of any contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * Alternatively, this software may be distributed under the terms of the
 * GNU General Public License ("GPL") version 2 as published by the Free
 * Software Foundation.
 *
 * NO WARRANTY
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF NONINFRINGEMENT, MERCHANTIBILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
 * THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR SPECIAL, EXEMPLARY,
 * OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
 * IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGES.
 *
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/wlan/target/madwifi/ath/if_athrate.h#2 $
 */
#ifndef _ATH_RATECTRL_H_
#define _ATH_RATECTRL_H_

struct ath_softc_tgt;
struct ath_node;
struct ath_node_target;
struct ath_desc;
struct ieee80211vap;
struct ieee80211com_target;
struct ath_tx_desc;

struct ath_ratectrl {
	size_t	arc_space;	/* space required for per-node state */
};

#define ATH_RC_DS_FLAG               0x01
#define ATH_RC_CW40_FLAG             0x02
#define ATH_RC_HT40_SGI_FLAG         0x04
#define ATH_RC_HT_FLAG               0x08
#define ATH_RC_RTSCTS_FLAG           0x10
#define ATH_RC_TX_STBC_FLAG          0x20    /* TX STBC */
#define ATH_RC_RX_STBC_FLAG          0xC0    /* RX STBC ,2 bits */
#define ATH_RC_RX_STBC_FLAG_S        6   
#define ATH_RC_WEP_TKIP_FLAG         0x100    /* WEP/TKIP encryption */

enum ath_rc_cwmode{
	ATH_RC_CW20_MODE,
	ATH_RC_CW40_MODE,     
};

#define ATH_RC_PROBE_ALLOWED    0x00000001
#define ATH_RC_MINRATE_LASTRATE 0x00000002

struct ath_rc_series {
	a_uint8_t rix;	
	a_uint8_t tries;	
	u_int8_t tx_chainmask;
	a_uint8_t flags;
	a_uint32_t max4msframelen;
	a_uint32_t txrateKbps;
};

/*
 * Attach/detach a rate control module.
 */
struct ath_ratectrl *ath_rate_attach(struct ath_softc_tgt *);

/*
 * Return the transmit info for a data packet.  If multi-rate state
 * is to be setup then try0 should contain a value other than ATH_TXMATRY
 * and ath_rate_setupxtxdesc will be called after deciding if the frame
 * can be transmitted with multi-rate retry.
 */
void ath_rate_findrate(struct ath_softc_tgt *sc,
		       struct ath_node_target *an,
		       a_int32_t shortPreamble,
		       size_t frameLen,
		       a_int32_t numTries,
		       a_int32_t numRates,
		       a_int32_t stepDnInc,
		       a_uint32_t rcflag,
		       struct ath_rc_series series[],
		       a_int32_t *isProbe);
/*
 * Update rate control state for a packet associated with the
 * supplied transmit descriptor.  The routine is invoked both
 * for packets that were successfully sent and for those that
 * failed (consult the descriptor for details).
 */
void ath_rate_tx_complete(struct ath_softc_tgt *, struct ath_node_target *,
			  struct ath_tx_desc *, struct ath_rc_series series[],
			  a_int32_t nframes, a_int32_t nbad);


void ath_rate_stateupdate(struct ath_softc_tgt *sc, struct ath_node_target *an, 
			  enum ath_rc_cwmode cwmode);

#endif /* _ATH_RATECTRL_H_ */
