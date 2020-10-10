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

#ifndef _NET80211_IEEE80211_VAR_H_
#define _NET80211_IEEE80211_VAR_H_

#include"ieee80211_linux.h"
#include <asf_bitmap.h>
#include"_ieee80211.h"
#include"ieee80211.h"
#include"ieee80211_node.h"
#include <wlan_hdr.h>

#define ieee80211_tgt_free_nbuf( _nbuf)          adf_nbuf_free( _nbuf)
/*
 * Built-in implementation for local skb free. Only interesting for platforms
 * that pass skbs between OS instances.
 */ 
#define ieee80211_tgt_free_local_nbuf( _nbuf)    ieee80211_tgt_free_nbuf( _nbuf)


#define IEEE80211_ADDR_EQ(a1,a2)    (adf_os_mem_cmp(a1,a2,IEEE80211_ADDR_LEN) == 0)
#define IEEE80211_ADDR_COPY(dst,src)    adf_os_mem_copy(dst, src, IEEE80211_ADDR_LEN)

/* ic_flags */
#define IEEE80211_F_FF          0x00000001  /* CONF: ATH FF enabled */
#define IEEE80211_F_TURBOP      0x00000002  /* CONF: ATH Turbo enabled*/
#define IEEE80211_F_PROMISC     0x00000004  /* STATUS: promiscuous mode */
#define IEEE80211_F_ALLMULTI    0x00000008  /* STATUS: all multicast mode */
/* NB: this is intentionally setup to be IEEE80211_CAPINFO_PRIVACY */
#define IEEE80211_F_PRIVACY     0x00000010  /* CONF: privacy enabled */
#define IEEE80211_F_PUREG       0x00000020  /* CONF: 11g w/o 11b sta's */
#define IEEE80211_F_XRUPDATE    0x00000040  /* CONF: update beacon XR element*/
#define IEEE80211_F_SCAN        0x00000080  /* STATUS: scanning */
#define IEEE80211_F_XR          0x00000100  /* CONF: operate in XR mode */
#define IEEE80211_F_SIBSS       0x00000200  /* STATUS: start IBSS */
/* NB: this is intentionally setup to be IEEE80211_CAPINFO_SHORT_SLOTTIME */
#define IEEE80211_F_SHSLOT      0x00000400  /* STATUS: use short slot time*/
#define IEEE80211_F_PMGTON      0x00000800  /* CONF: Power mgmt enable */
#define IEEE80211_F_DESBSSID    0x00001000  /* CONF: des_bssid is set */
#define IEEE80211_F_WME         0x00002000  /* CONF: enable WME use */
#define IEEE80211_F_BGSCAN      0x00004000  /* CONF: bg scan enabled */
#define IEEE80211_F_SWRETRY     0x00008000  /* CONF: sw tx retry enabled */
#define IEEE80211_F_TXPOW_FIXED 0x00010000  /* TX Power: fixed rate */
#define IEEE80211_F_IBSSON      0x00020000  /* CONF: IBSS creation enable */
#define IEEE80211_F_SHPREAMBLE  0x00040000  /* STATUS: use short preamble */
#define IEEE80211_F_DATAPAD     0x00080000  /* CONF: do alignment pad */
#define IEEE80211_F_USEPROT     0x00100000  /* STATUS: protection enabled */
#define IEEE80211_F_USEBARKER   0x00200000  /* STATUS: use barker preamble*/
#define IEEE80211_F_TIMUPDATE   0x00400000  /* STATUS: update beacon tim */
#define IEEE80211_F_WPA1        0x00800000  /* CONF: WPA enabled */
#define IEEE80211_F_WPA2        0x01000000  /* CONF: WPA2 enabled */
#define IEEE80211_F_WPA         0x01800000  /* CONF: WPA/WPA2 enabled */
#define IEEE80211_F_DROPUNENC   0x02000000  /* CONF: drop unencrypted */
#define IEEE80211_F_COUNTERM    0x04000000  /* CONF: TKIP countermeasures */
#define IEEE80211_F_HIDESSID    0x08000000  /* CONF: hide SSID in beacon */
#define IEEE80211_F_NOBRIDGE    0x10000000  /* CONF: disable internal bridge */
#define IEEE80211_F_WMEUPDATE   0x20000000  /* STATUS: update beacon wme */
#define IEEE80211_F_DOTH        0x40000000  /* enable 11.h */
#define IEEE80211_F_CHANSWITCH  0x80000000  /* force chanswitch */

/* ic_flags_ext */
#define IEEE80211_FEXT_WDS          0x00000001  /* CONF: 4 addr allowed */
#define IEEE80211_FEXT_COUNTRYIE    0x00000002 /* CONF: enable country IE */
#define IEEE80211_FEXT_SCAN_PENDING 0x00000004 /* STATE: scan pending */
#define	IEEE80211_FEXT_BGSCAN	    0x00000008	/* STATE: enable full bgscan completion */
#define IEEE80211_FEXT_UAPSD	    0x00000010	/* CONF: enable U-APSD */
#define IEEE80211_FEXT_SLEEP	    0x00000020	/* STATUS: sleeping */
#define IEEE80211_FEXT_EOSPDROP	    0x00000040	/* drop uapsd EOSP frames for test */
#define	IEEE80211_FEXT_MARKDFS	    0x00000080	/* Enable marking of dfs interfernce */
#define IEEE80211_FEXT_REGCLASS	    0x00000100	/* CONF: send regclassids in country ie */
#define	IEEE80211_FEXT_MARKDFS      0x00000080	/* Enable marking of dfs interfernce */
#define IEEE80211_FEXT_ERPUPDATE    0x00000200	/* STATUS: update ERP element */
#define IEEE80211_FEXT_SWBMISS      0x00000400 	/* CONF: use software beacon timer */
#define IEEE80211_FEXT_BLKDFSCHAN   0x00000800 	/* CONF: block the use of DFS channels */
#define IEEE80211_FEXT_APPIE_UPDATE 0x00001000 /* STATE: beacon APP IE updated */
#define IEEE80211_FAST_CC           0x00002000  /* CONF: Fast channel change */
#define IEEE80211_C_AMPDU           0x00004000  /* CONF: A-MPDU supported */
#define IEEE80211_C_AMSDU           0x00008000  /* CONF: A-MSDU supported */
#define IEEE80211_C_HTPROT          0x00010000  /* CONF: HT traffic protected */
#define IEEE80211_C_RESET           0x00020000  /* CONF: Reset once */
#define IEEE80211_F_NONHT_AP        0x00040000  /* STATUS: HT traffic protected */
#define IEEE80211_FEXT_HTUPDATE     0x00080000      /* STATUS: update HT element */
#define IEEE80211_C_WDS_AUTODETECT  0x00100000 /* CONF: WDS auto Detect/DELBA */
#define IEEE80211_C_RB              0x00200000  /* CONF: RB control */
#define IEEE80211_C_RB_DETECT       0x00400000  /* CONF: RB auto detection */
#define IEEE80211_C_NO_HTIE         0x00800000 /* CONF: No HT IE sending/parsing */

/* ic_caps */
#define IEEE80211_C_WEP     0x00000001  /* CAPABILITY: WEP available */
#define IEEE80211_C_TKIP    0x00000002  /* CAPABILITY: TKIP available */
#define IEEE80211_C_AES     0x00000004  /* CAPABILITY: AES OCB avail */
#define IEEE80211_C_AES_CCM 0x00000008  /* CAPABILITY: AES CCM avail */
#define IEEE80211_C_CKIP    0x00000020  /* CAPABILITY: CKIP available */
#define IEEE80211_C_FF      0x00000040  /* CAPABILITY: ATH FF avail */
#define IEEE80211_C_TURBOP  0x00000080  /* CAPABILITY: ATH Turbo avail*/
#define IEEE80211_C_IBSS    0x00000100  /* CAPABILITY: IBSS available */
#define IEEE80211_C_PMGT    0x00000200  /* CAPABILITY: Power mgmt */
#define IEEE80211_C_HOSTAP  0x00000400  /* CAPABILITY: HOSTAP avail */
#define IEEE80211_C_AHDEMO  0x00000800  /* CAPABILITY: Old Adhoc Demo */
#define IEEE80211_C_SWRETRY 0x00001000  /* CAPABILITY: sw tx retry */
#define IEEE80211_C_TXPMGT  0x00002000  /* CAPABILITY: tx power mgmt */
#define IEEE80211_C_SHSLOT  0x00004000  /* CAPABILITY: short slottime */
#define IEEE80211_C_SHPREAMBLE  0x00008000  /* CAPABILITY: short preamble */
#define IEEE80211_C_MONITOR 0x00010000  /* CAPABILITY: monitor mode */
#define IEEE80211_C_TKIPMIC 0x00020000  /* CAPABILITY: TKIP MIC avail */
#define IEEE80211_C_WPA1    0x00800000  /* CAPABILITY: WPA1 avail */
#define IEEE80211_C_WPA2    0x01000000  /* CAPABILITY: WPA2 avail */
#define IEEE80211_C_WPA     0x01800000  /* CAPABILITY: WPA1+WPA2 avail*/
#define IEEE80211_C_BURST   0x02000000  /* CAPABILITY: frame bursting */
#define IEEE80211_C_WME     0x04000000  /* CAPABILITY: WME avail */
#define IEEE80211_C_WDS     0x08000000  /* CAPABILITY: 4-addr support */
#define IEEE80211_C_WME_TKIPMIC 0x10000000  /* CAPABILITY: TKIP MIC for QoS frame */
#define IEEE80211_C_BGSCAN  0x20000000  /* CAPABILITY: bg scanning */
#define	IEEE80211_C_UAPSD	0x40000000	/* CAPABILITY: UAPSD */
#define IEEE80211_C_FASTCC	0x80000000	/* CAPABILITY: fast channel change */

/* XXX protection/barker? */

#define IEEE80211_C_CRYPTO  0x0000002f  /* CAPABILITY: crypto alg's */

/* Atheros ABOLT definitions */
#define IEEE80211_ABOLT_TURBO_G     0x01    /* Legacy Turbo G */
#define IEEE80211_ABOLT_TURBO_PRIME 0x02    /* Turbo Prime */
#define IEEE80211_ABOLT_COMPRESSION 0x04    /* Compression */
#define IEEE80211_ABOLT_FAST_FRAME  0x08    /* Fast Frames */
#define IEEE80211_ABOLT_BURST       0x10    /* Bursting */
#define IEEE80211_ABOLT_WME_ELE     0x20    /* WME based cwmin/max/burst tuning */
#define IEEE80211_ABOLT_XR          0x40    /* XR */
#define IEEE80211_ABOLT_AR          0x80    /* AR switches out based on adjaced non-turbo traffic */

/* Atheros Advanced Capabilities ABOLT definition */
#define IEEE80211_ABOLT_ADVCAP  (IEEE80211_ABOLT_TURBO_PRIME |	\
				 IEEE80211_ABOLT_COMPRESSION |	\
				 IEEE80211_ABOLT_FAST_FRAME |	\
				 IEEE80211_ABOLT_XR |		\
				 IEEE80211_ABOLT_AR |		\
				 IEEE80211_ABOLT_BURST |	\
				 IEEE80211_ABOLT_WME_ELE)

/* check if a capability was negotiated for use */
#define IEEE80211_ATH_CAP(vap, ni, bit) \
    ((ni)->ni_ath_flags & (vap)->iv_ath_cap & (bit))

/* flags to VAP create function */
#define IEEE80211_VAP_XR        0x10000 /* create a XR VAP without registering net device with OS*/

/* HT flags */
#define IEEE80211_HTF_SHORTGI          0x0001


/***************  Utility Routines ***/
/*
 * Return the size of the 802.11 header for a management or data frame.
 */
static __inline a_int32_t
ieee80211_hdrsize(const void *data)
{
	const struct ieee80211_frame *wh = data;
	a_int32_t size = sizeof(struct ieee80211_frame);

	/* NB: we don't handle control frames */
	adf_os_assert((wh->i_fc[0]&IEEE80211_FC0_TYPE_MASK) != IEEE80211_FC0_TYPE_CTL);
	if ((wh->i_fc[1] & IEEE80211_FC1_DIR_MASK) == IEEE80211_FC1_DIR_DSTODS)
		size += IEEE80211_ADDR_LEN;
	if (IEEE80211_QOS_HAS_SEQ(wh))
		size += sizeof(a_uint16_t);
	return size;
}

/*
 * Like ieee80211_hdrsize, but handles any type of frame.
 */
static __inline a_int32_t
ieee80211_anyhdrsize(const void *data)
{
	const struct ieee80211_frame *wh = data;

	if ((wh->i_fc[0]&IEEE80211_FC0_TYPE_MASK) == IEEE80211_FC0_TYPE_CTL) {
		switch (wh->i_fc[0] & IEEE80211_FC0_SUBTYPE_MASK) {
		case IEEE80211_FC0_SUBTYPE_CTS:
		case IEEE80211_FC0_SUBTYPE_ACK:
			return sizeof(struct ieee80211_frame_ack);
		}
		return sizeof(struct ieee80211_frame_min);
	} else
		return ieee80211_hdrsize(data);
}

#endif
