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
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>

#include <if_llc.h>
#include "ieee80211_var.h"

#include "ieee80211.h"
#include <wlan_hdr.h>

a_status_t
ieee80211_tgt_crypto_encap(struct ieee80211_frame *wh,
			   struct ieee80211_node_target *ni,
			   a_uint8_t keytype)
{
#define CRYPTO_KEY_TYPE_AES          2
#define CRYPTO_KEY_TYPE_TKIP         3
#define CRYPTO_KEY_TYPE_WAPI         4
#define IEEE80211_WLAN_HDR_LEN      24

	a_uint8_t *iv = NULL;
	a_uint16_t tmp;
	a_uint16_t offset = IEEE80211_WLAN_HDR_LEN;
	a_uint8_t b1, b2;
	struct ieee80211_qosframe_addr4 *wh_mesh;

	if (IEEE80211_QOS_HAS_SEQ(wh))
		offset += 4;  // pad for 4 byte alignment

	/* set the offset to 32 if the mesh control field is present */
	wh_mesh = (struct ieee80211_qosframe_addr4 *)wh;
	if (wh_mesh->i_qos[1] & 0x01)
		offset = 32;

	iv = (a_uint8_t *) wh;
	iv = iv + offset;

	switch (keytype) {
	case CRYPTO_KEY_TYPE_AES:
		ni->ni_iv16++;
		if (ni->ni_iv16 == 0)
		{
			ni->ni_iv32++;
		}

		*iv++ = (a_uint8_t) ni->ni_iv16;
		*iv++ = (a_uint8_t) (ni->ni_iv16 >> 8);
		*iv++ = 0x00;
		*iv++ |= 0x20;

		tmp = (a_uint16_t) ni->ni_iv32;
		*iv++ = (a_uint8_t) tmp;
		*iv++ = (a_uint8_t) (tmp >> 8);

		tmp = (a_uint16_t) (ni->ni_iv32 >> 16);
		*iv++ = (a_uint8_t) tmp;
		*iv = (a_uint8_t) (tmp >> 8);
		break;
	case CRYPTO_KEY_TYPE_TKIP:
		ni->ni_iv16++;
		if (ni->ni_iv16 == 0)
		{
			ni->ni_iv32++;
		}

		b1 = (a_uint8_t) (ni->ni_iv16 >> 8);
		b2 = (b1 | 0x20) & 0x7f;

		*iv++ = b1;
		*iv++ = b2;

		*iv++ = (a_uint8_t) ni->ni_iv16;
		*iv++ |= 0x20;

		tmp = (a_uint16_t) ni->ni_iv32;
		*iv++ = (a_uint8_t) tmp;
		*iv++ = (a_uint8_t) (tmp >> 8);

		tmp = (a_uint16_t) (ni->ni_iv32 >> 16);
		*iv++ = (a_uint8_t) tmp;
		*iv = (a_uint8_t) (tmp >> 8);
		break;
	default:
		break;
	}

	return 1;

#undef CRYPTO_KEY_TYPE_TKIP
#undef CRYPTO_KEY_TYPE_AES
#undef CRYPTO_KEY_TYPE_WAPI
#undef IEEE80211_WLAN_HDR_LEN
}
#undef  IEEE80211_ADDR_LEN     
