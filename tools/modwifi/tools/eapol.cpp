/**
 * FIXME: GTK extraction with using TKIP only (EapolKeyVer_HMAC_MD5_RC4)
 * FIXME: Proper detection of EAPOL frame id
 *
 * TODO: Reset handshake parameters if we capture a new one...
 */
#include <string.h>
#include <stdio.h>
#include <arpa/inet.h>

#include "util.h"
#include "ieee80211header.h"
#include "crypto.h"

#include "eapol.h"

#define UNUSED_VAR(x)	(void)(x)
//#define DEBUG_DUMP_KEYS

static bool got_full_handshake(eapol_sta_info *sta)
{
	return sta->state.ptk && sta->state.gtk;
}

static void keydump(const char *name, uint8_t *buf, size_t len)
{
#ifdef DEBUG_DUMP_KEYS
	printf(" %-6s = ", name);
	for (size_t i = 0; i < len; ++i)
		printf("%02X", buf[i]);
	printf("\n");
#endif
}


int calculate_ptk(eapol_sta_info *sta)
{
	/* if we can derive the PMK then do it */
	if (!sta->state.pmk && sta->psk[0] && sta->essid[0])
	{
		calc_pmk(sta->psk, sta->essid, sta->pmk);
		sta->state.pmk = true;

		keydump("PMK", sta->pmk, sizeof(sta->pmk));
	}

	/* if we have enough info to derive the PTK then do it */
	if (!sta->state.ptk && sta->state.pmk && sta->state.anonce && sta->state.snonce)
	{
		uint8_t fullptk[80];

		keydump("BSSID", sta->bssid, sizeof(sta->bssid));
		keydump("STMAC", sta->stmac, sizeof(sta->stmac));
		keydump("ANONCE", sta->anonce, sizeof(sta->anonce));
		keydump("SNONCE", sta->snonce, sizeof(sta->snonce));
		keydump("PMK", sta->pmk, sizeof(sta->pmk));

		calc_ptk(sta->bssid, sta->stmac, sta->anonce, sta->snonce, sta->pmk, fullptk);
		memcpy(sta->ptk.ptk, fullptk, sizeof(sta->ptk));
		sta->state.ptk = true;

		keydump("PTK", sta->ptk.ptk, sizeof(sta->ptk.ptk));
	}

	return 0;
}


bool verify_eapol_mic(eapol_sta_info *sta, ieee80211xauth *auth, size_t len)
{
	uint8_t buf[1024];
	uint8_t mic[16];
	ieee80211xauth *authbuf = (ieee80211xauth*)buf;

	if (!sta->state.ptk) {
		fprintf(stderr, "%s: Warning: no PTK available to verify MIC\n", __FUNCTION__);
		return false;
	}

	memcpy(buf, auth, len);
	memcpy(mic, auth->mic, 16);
	memset(authbuf->mic, 0, 16);

	return verify_mic(buf, len, auth->inf.keyver, mic, sta->ptk.kck);
}


int calculate_gtk(eapol_sta_info *sta, ieee80211xauth *auth, size_t len)
{
	int keydatalen;
	uint8_t plain[1024];
	int plainlen;

	// ignore if we already have GTK
	if (sta->state.gtk)
		return 0;

	// verify packet size
	if (len < sizeof(ieee80211xauth))
		return -1;
	keydatalen = ntohs(auth->datalen);
	if (len < keydatalen + sizeof(ieee80211xauth))
		return -1;

	// verify EAPOL frame 3 packet
	if (auth->inf.type != 1 || auth->inf.install != 1
		|| auth->inf.ack != 1 || auth->inf.mic != 1)
		return -1;

	// get PTK data if not yet calculated
	if (!sta->state.ptk)
		calculate_ptk(sta);
	if (!sta->state.ptk)
		return -1;
	if (!sta->valid_ptk)
		fprintf(stderr, "%s: Warning: PTK not verified to be correct\n", __FUNCTION__);

	// verify MIC of packet
	if (!verify_eapol_mic(sta, auth, len)) {
		fprintf(stderr, "%s: Warning: Incorrect MIC, GTK may be tampered with\n", __FUNCTION__);
	}

	// decrypt the data
	plainlen = decrypt_eapol_key_data(auth->iv, sta->ptk.kek, (EapolKeyVer)auth->inf.keyver,
			(uint8_t*)(auth + 1), plain, keydatalen);
	if (plainlen <= 0) {
		fprintf(stderr, "%s: Failed to decrypt EAPOL-WPA Key Data: %zu\n", __FUNCTION__, len);
	} else {
		// FIXME: Properly parse RSN Information Element fields....
		int gtkpos = plain[1] + 2 + 8;
		
		if ((size_t)plainlen < gtkpos + sizeof(sta->gtk)) {
			fprintf(stderr, "%s: invalid GTK position %d/%d in EAPOL-Key data\n", __FUNCTION__, gtkpos, plainlen);
			fprintf(stderr, "This may be caused because RSN Info Elements are hardcoded...\n");
			return-1;
		}

		memcpy(sta->gtk.gtk, plain + gtkpos, sizeof(sta->gtk));
		sta->state.gtk = true;

		keydump("GTK", sta->gtk.gtk, sizeof(sta->gtk.gtk));
	}

	return 0;
}


/**
 * Passively gather information about an EAPOL handshake.
 *
 * The caller should check the bssid and sender MAC address and provide
 * the correct hdsk object.
 */
eapol_update check_eapol_handshake(eapol_sta_info *sta, uint8_t *buf, size_t len)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	size_t pos = 0, hdrsize = 0;
	uint8_t *bssid, *client, *othermac;
	llcsnaphdr *llcsnap;
	ieee80211xauth *auth;
	size_t authlen;
	eapol_update rval;

	UNUSED_VAR(othermac);
	memset(&rval, 0, sizeof(rval));

	//
	// 1. Sanity checks + get basic packet info
	//

	// must be either to or from DS
	if ( !(hdr->fc.tods ^ hdr->fc.fromds) ) return rval;
	// must be an unencrypted data packet
	if (hdr->fc.type != TYPE_DATA || hdr->fc.protectedframe) return rval;

	// get position after IEEE 802.11 header
	pos = sizeof(ieee80211header);
	if (hdr->fc.subtype >= 8 && hdr->fc.subtype <= 11) {
		pos += sizeof(ieee80211qosheader);
	}
	if (len < hdrsize) return rval;

	// get the MAC addresses we need
	if (hdr->fc.tods) {
		bssid = hdr->addr1;
		client = hdr->addr2;
		othermac = hdr->addr3;
	} else {
		client = hdr->addr1;
		bssid = hdr->addr2;
		othermac = hdr->addr3;
	}

	// Must match MAC addresses already present in sta
	if (memcmp(sta->stmac, client, 6) != 0)
		return rval;
	if (memcmp(sta->bssid, bssid, 6) != 0)
		return rval;

	//
	// 2. Check if EAPOL frame
	//

	if (pos + 26 > len) {
		return rval;
	}
	llcsnap = (llcsnaphdr*)(buf + pos);

	/* check ethertype == EAPOL */
	if (llcsnap->type != DOT1X_AUTHENTICATION) {
		return rval;
	}

	pos += sizeof(llcsnaphdr);

	/* if we already have a recent handshake - ignore this packet */
	if (got_full_handshake(sta) && time(NULL) - sta->wpa_time <= 1) {
		return rval;
	}

	//
	// 3. Analyze the EPAOL frame
	//

	auth = (ieee80211xauth*)(buf + pos);
	authlen = len - pos;
	if (authlen != (size_t)ntohs(auth->len) + 4) {
		fprintf(stderr, "%s: EAPOL frame has invalid length field\n", __FUNCTION__);
		return rval;
	}

	/* frame 1: Pairwise == 1, Install == 0, Ack == 1, MIC == 0 */
	if (auth->inf.type == 1 && auth->inf.install == 0
		&& auth->inf.ack == 1 && auth->inf.mic == 0)
	{
		rval.framenum = 1;

		memcpy(sta->anonce, auth->nonce, 32);
		sta->state.anonce = true;
	}

	if (pos + 17 + 32 > len) {
		fprintf(stderr, "EAPOL packet has insufficient length\n");
		return rval;
	}

	/* frame 2: Pairwise == 1, Install == 0, Ack == 0, MIC == 1, secure == 0, key datalen != 0 */
	if (auth->inf.type == 1 && auth->inf.install == 0 && auth->inf.ack == 0
		&& auth->inf.mic == 1 && auth->inf.secure == 0 && auth->datalen != 0)
	{
		rval.framenum = 2;

		memcpy(sta->snonce, auth->nonce, 32);
		sta->state.snonce = true;

		// update keys
		if (!sta->state.ptk) {
			calculate_ptk(sta);
			rval.gotptk = sta->state.ptk;
		}

		// if we have the PTK but haven't verified it yet, try to verify it
		if (sta->state.ptk && !sta->valid_ptk) {
			sta->valid_ptk = verify_eapol_mic(sta, auth, authlen);
		}
	}

	/* frame 3: Pairwise == 1, Install == 1, Ack == 1, MIC == 1 */
	if (auth->inf.type == 1 && auth->inf.install == 1
		&& auth->inf.ack == 1 && auth->inf.mic == 1)
	{
		rval.framenum = 3;

		memcpy(sta->anonce, auth->nonce, 32);
		sta->state.anonce = true;

		// if we have the PTK but haven't verified it yet, try to verify it
		if (sta->state.ptk && !sta->valid_ptk) {
			sta->valid_ptk = verify_eapol_mic(sta, auth, authlen);
		}

		// extract group key if we have the PTK
		if (!sta->state.gtk) {
			calculate_gtk(sta, auth, authlen);
			rval.gotgtk = sta->state.gtk;
		}
	}

	/* frame 4: Pairwise == 1, Install == 0, Ack == 0, MIC == 1, key datalen = 0 */
	if (auth->inf.type == 1 && auth->inf.install == 0 && auth->inf.ack == 0
		&& auth->inf.mic == 1 && auth->datalen == 0)
	{
		// don't care about frame 4
		rval.framenum = 4;
	}

	sta->lastframenum = rval.framenum;
	return rval;
}


