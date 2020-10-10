#include <string.h>
#include <stdio.h>

#include "ieee80211header.h"
#include "util.h"

bool is_empty(const uint8_t *buffer, size_t len)
{
	size_t i;

	for (i = 0; i < len; ++i)
	{
		if (buffer[i] != 0)
			return false;
	}

	return true;
}

static void timespec_normalize(struct timespec *x)
{
	if (x->tv_nsec > 1000000000) {
		x->tv_sec += x->tv_nsec / 1000000000;
		x->tv_nsec %= 1000000000;
	}
}

int timespec_cmp(const struct timespec *rhs, const struct timespec *lhs)
{
	if (rhs->tv_sec < lhs->tv_sec)
		return -1;
	else if (rhs->tv_sec > lhs->tv_sec)
		return 1;

	if (rhs->tv_nsec < lhs->tv_nsec)
		return -1;
	else if (rhs->tv_nsec > lhs->tv_nsec)
		return 1;

	return 0;
}

/** Assumes timespec fields are signed */
void timespec_diff(const struct timespec *end, const struct timespec *start,
	struct timespec *result)
{
	if (end->tv_nsec - start->tv_nsec < 0) {
		result->tv_sec = end->tv_sec - start->tv_sec-1;
		result->tv_nsec = 1000000000 + end->tv_nsec - start->tv_nsec;
	} else {
		result->tv_sec = end->tv_sec - start->tv_sec;
		result->tv_nsec = end->tv_nsec - start->tv_nsec;
	}
}

void timespec_add(const struct timespec *x, const struct timespec *y,
	struct timespec *result)
{
	result->tv_sec = x->tv_sec + y->tv_sec;
	result->tv_nsec = x->tv_nsec + y->tv_nsec;
	timespec_normalize(result);
}

void timespec_add_nsec(struct timespec *x, int nsecs)
{
	x->tv_nsec += nsecs;
	timespec_normalize(x);
}

bool getmac(const char *macaddr, uint8_t mac[6])
{
	char normaddr[32];
	int intmac[6];
	int i, len;

	if (macaddr == NULL) return false;

	len = strlen(macaddr);
	if (len < 11 || len > 17)
		return false;

	// Normalize the input
	strncpy(normaddr, macaddr, sizeof(normaddr));
	for (i = 0; normaddr[i] != '\x0'; ++i) {
		if (normaddr[i] == '-')
			normaddr[i] = ':';
	}

	// Parse normalized mac address
	if (sscanf(normaddr, "%x:%x:%x:%x:%x:%x", &intmac[0], &intmac[1],
		&intmac[2], &intmac[3], &intmac[4], &intmac[5]) != 6)
		return false;

	// Copy to output
	for (i = 0; i < 6; ++i) {
		mac[i] = intmac[i];
	}

	return true;
}

// TODO: Place this function somewhere else?
void dump_packet(unsigned char* h80211, int len)
{
	int z, i, j;
	int mi_b = 0, mi_s = 0, mi_d = 0, mi_t = 0, mi_r = 0, is_wds = 0, key_index_offset;

	z = ((h80211[1] & 3) != 3) ? 24 : 30;
	if ((h80211[0] & 0x80) == 0x80) /* QoS */
		z += 2;

	switch (h80211[1] & 3) {
	case 0:
		mi_b = 16;
		mi_s = 10;
		mi_d = 4;
		is_wds = 0;
		break;
	case 1:
		mi_b = 4;
		mi_s = 10;
		mi_d = 16;
		is_wds = 0;
		break;
	case 2:
		mi_b = 10;
		mi_s = 16;
		mi_d = 4;
		is_wds = 0;
		break;
	case 3:
		mi_t = 10;
		mi_r = 4;
		mi_d = 16;
		mi_s = 24;
		is_wds = 1;
		break; // WDS packet
	}

	printf("\n\n  Size: %d, FromDS: %d, ToDS: %d", len, (h80211[1] & 2) >> 1, (h80211[1] & 1));

	if ((h80211[0] & 0x0C) == 8 && (h80211[1] & 0x40) != 0) {
		//             if (is_wds) key_index_offset = 33; // WDS packets have an additional MAC, so the key index is at byte 33
		//             else key_index_offset = 27;
		key_index_offset = z + 3;

		if ((h80211[key_index_offset] & 0x20) == 0)
			printf(" (WEP)");
		else
			printf(" (WPA)");
	}

	printf("\n\n");

	if (is_wds) {
		printf("  Transmitter  =  %02X:%02X:%02X:%02X:%02X:%02X\n",
				h80211[mi_t], h80211[mi_t + 1], h80211[mi_t + 2],
				h80211[mi_t + 3], h80211[mi_t + 4], h80211[mi_t + 5]);

		printf("     Receiver  =  %02X:%02X:%02X:%02X:%02X:%02X\n",
				h80211[mi_r], h80211[mi_r + 1], h80211[mi_r + 2],
				h80211[mi_r + 3], h80211[mi_r + 4], h80211[mi_r + 5]);
	} else {
		printf("        BSSID  =  %02X:%02X:%02X:%02X:%02X:%02X\n",
				h80211[mi_b], h80211[mi_b + 1], h80211[mi_b + 2],
				h80211[mi_b + 3], h80211[mi_b + 4], h80211[mi_b + 5]);
	}

	printf("    Dest. MAC  =  %02X:%02X:%02X:%02X:%02X:%02X\n",
			h80211[mi_d], h80211[mi_d + 1], h80211[mi_d + 2], h80211[mi_d
					+ 3], h80211[mi_d + 4], h80211[mi_d + 5]);

	printf("   Source MAC  =  %02X:%02X:%02X:%02X:%02X:%02X\n",
			h80211[mi_s], h80211[mi_s + 1], h80211[mi_s + 2], h80211[mi_s
					+ 3], h80211[mi_s + 4], h80211[mi_s + 5]);

	/* print a hex dump of the packet */

	for (i = 0; i < len; i++) {
		if ((i & 15) == 0) {
			if (i == 224) {
				printf("\n  --- CUT ---");
				break;
			}

			printf("\n  0x%04x: ", i);
		}

		printf("%02x", h80211[i]);

		if ((i & 1) != 0)
			printf(" ");

		if (i == len - 1 && ((i + 1) & 15) != 0) {
			for (j = ((i + 1) & 15); j < 16; j++) {
				printf("  ");
				if ((j & 1) != 0)
					printf(" ");
			}

			printf(" ");

			for (j = 16 - ((i + 1) & 15); j < 16; j++)
				printf("%c", (h80211[i - 15 + j] < 32 || h80211[i - 15 + j]
						> 126) ? '.' : h80211[i - 15 + j]);
		}

		if (i > 0 && ((i + 1) & 15) == 0) {
			printf(" ");

			for (j = 0; j < 16; j++)
				printf("%c", (h80211[i - 15 + j] < 32 || h80211[i - 15 + j]
						> 127) ? '.' : h80211[i - 15 + j]);
		}
	}
}

// =============================================
//
//		IEEE 802.11 Functions
//
// =============================================

const char * frametype(int type)
{
	switch (type) {
		case 0: return "Mngmt";
		case 1: return "Cntrl";
		case 2: return "Data";
	}

	return "Unknown";
}

static const char * framesubtype_mngmt(int subtype)
{
	switch (subtype) {
		case 0: return "Asso Req";
		case 1: return "Asso Resp";
		case 2: return "Reasso Req";
		case 3: return "Reasso Resp";
		case 4: return "Probe Req";
		case 5: return "Probe Resp";
		case 6: return "Timing Advert";
		case 7: return "Reserved";
		case 8: return "Beacon";
		case 9: return "ATIM";
		case 10: return "Disasso";
		case 11: return "Auth";
		case 12: return "Deauth";
		case 13: return "Action";
		case 14: return "Action No Ack";
		case 15: return "Reserved";
	}

	return "Unknown";
}

static const char * framesubtype_cntrl(int subtype)
{
	switch (subtype) {
		case 0:
		case 1:
		case 2:
		case 3:
		case 4:
		case 5:
		case 6:
			return "Reserved";
		case 7: return "Control Wrapper";
		case 8: return "BlockAckReq";
		case 9: return "BlockAck";
		case 10: return "PS-Poll";
		case 11: return "RTS";
		case 12: return "CTS";
		case 13: return "ACK";
		case 14: return "CF-End";
		case 15: return "CF-End + CF-Ack";
	}

	return "Unknown";
}

static const char * framesubtype_data(int subtype)
{
	switch (subtype) {
		case 0: return "Data";
		case 1: return "Data + CF-Ack";
		case 2: return "Data + CF-Poll";
		case 3: return "Data + CF-Ack + CF-Poll";
		case 4: return "Null";
		case 5: return "CF-Ack";
		case 6: return "CF-Poll";
		case 7: return "CF-Ack + CF-Poll";
		case 8: return "QoS Data";
		case 9: return "QoS Data + CF-Ack";
		case 10: return "QoS Data + CF-Poll";
		case 11: return "QoS Data + CF-Ack + CF-Poll";

		case 12: return "QoS Null";
		case 13: return "Reserved";
		case 14: return "QoS CF-Poll";
		case 15: return "QoS CF-Ack + CF-Poll";
	}

	return "Unknown";
}

/** IEEE802.11-2012 8.2.4.1.3 Type and Subtype fields */
const char * framesubtype(int type, int subtype)
{
	switch (type) {
		case 0: return framesubtype_mngmt(subtype);
		case 1: return framesubtype_cntrl(subtype);
		case 2: return framesubtype_data(subtype);
		default: return "Unknown";
	}
}

size_t add_qos_hdr(uint8_t *buf, size_t len, size_t maxlen)
{
	ieee80211header *hdr = (ieee80211header*)buf;

	// include QoS header for chopchop attack - FIXME: Check for buffer overflow
	if (!ieee80211_dataqos(hdr))
	{
		if (maxlen < len + 2)
			return 0;

		// set type to QoS frame
		hdr->fc.subtype = 8;

		// make space for the two QoS bytes
		memmove(buf + 26, buf + 24, len - 24);

		// fill in the QoS bytes - give it priority 0 (Best Effort)
		buf[24] = 0x00;
		buf[25] = 0x00;

		// packet got bigger
		len += 2;
	}

	return len;
}

// ===========================================
//
//		BEACON FUNCTIONS
//
// ===========================================

struct NetInfo {
	char *ssid;
	MacAddr bssid;
};

static bool is_our_beacon(uint8_t *buf, size_t len, void *data)
{
	struct NetInfo *info = (struct NetInfo *)data;
	ieee80211header *hdr = (ieee80211header*)buf;
	char packet_ssid[256];

	if (len < sizeof(ieee80211header) || hdr->fc.type != 0 || hdr->fc.subtype != 8
		|| memcmp(hdr->addr1, "\xFF\xFF\xFF\xFF\xFF\xFF", 6) != 0)
		return false;

	if (!info->bssid.empty() && info->bssid == MacAddr(hdr->addr2))
		return true;

	if (info->ssid && beacon_get_ssid(buf, len, packet_ssid, sizeof(packet_ssid))
	    && strcmp(info->ssid, packet_ssid) == 0)
		return true;

	return false;
}

int get_beacon(wi_dev *ap, uint8_t *buf, size_t len, char *ssid, const MacAddr &mac)
{
	struct timespec timeout;
	struct NetInfo info;

	timeout.tv_sec = 2;
	timeout.tv_nsec = 0;
	info.ssid = ssid;
	info.bssid = mac;
	return osal_wi_sniff(ap, buf, len, is_our_beacon, &info, &timeout);
}

static size_t get_offset_fixedparams(uint8_t *buf, size_t len)
{
	ieee80211header *hdr = (ieee80211header*)buf;

	if (hdr->fc.type != TYPE_MNGMT)
		return 0;

	// beacon, probe response
	if (hdr->fc.subtype == 8 || hdr->fc.subtype == 5)
		return sizeof(ieee80211header) + sizeof(ieee802211fixedparams);
	
	// association request
	if (hdr->fc.subtype == 0)
		return sizeof(ieee80211header) + 4;
	
	// probe request
	if (hdr->fc.subtype == 4)
		return sizeof(ieee80211header);

	return 0;
}

bool beacon_get_ssid(uint8_t *buf, size_t len, char *outssid, size_t outlen)
{
	// iterate over all tagged parameters of the beacon frame
	size_t pos = get_offset_fixedparams(buf, len);
	if (pos == 0) return false;

	while (pos < len)
	{
		// is it the SSID element?
		if (buf[pos] == 0)
		{
			size_t ssidlen = std::min((size_t)buf[pos + 1], outlen - 1);

			memcpy(outssid, (char*)(buf + pos + 2), ssidlen);
			outssid[ssidlen] = '\x0';
			
			return true;
		}

		// move to next parameter
		pos += 2 + buf[pos + 1];
	}

	return false;
}

bool beacon_set_ssid(uint8_t *buf, size_t *len, size_t maxlen, char *newssid)
{
	int newssidlen = strlen(newssid);
	if (newssidlen > 255) {
		fprintf(stderr, "%s: new ssid name %s is too long", __FUNCTION__, newssid);
		return false;
	}

	// iterate over all tagged parameters of the beacon frame
	size_t pos = get_offset_fixedparams(buf, *len);
	if (pos == 0) return false;

	while (pos < *len)
	{
		// is it the SSID element?
		if (buf[pos] == 0)
		{
			size_t currssidlen = buf[pos + 1];
			size_t newlen = *len + newssidlen - currssidlen;

			// do we have enough space for the new SSID name?
			if (newlen > maxlen) {
				fprintf(stderr, "%s: not enough space for new ssid %s\n",
					__FUNCTION__, newssid);
				return false;
			}

			// move data after this element to make/reduce space
			memmove(&buf[pos + 2 + newssidlen],
				&buf[pos + 2 + currssidlen],
				*len - pos - 2 - currssidlen);
			*len = newlen;

			// set the new ssid name
			buf[pos + 1] = newssidlen;
			memcpy(buf + pos + 2, newssid, newssidlen);
			
			return true;
		}

		// move to next parameter
		pos += 2 + buf[pos + 1];
	}

	return false;
}

int beacon_get_chan(uint8_t *buf, size_t len)
{
	size_t pos = get_offset_fixedparams(buf, len);
	if (pos == 0) return false;

	// iterate over all tagged parameters of the beacon frame
	while (pos < len)
	{
		// is it the SSID element?
		if (buf[pos] == 3) {
			if (buf[pos + 2] >= 1 && buf[pos + 2] <= 13)
				return buf[pos + 2];
			else
				return -1;
		}
		// is it the HT Information element?
		if (buf[pos] == 61) {
			if (buf[pos + 2] >= 34 && buf[pos + 2] <= 165)
				return buf[pos + 2];
			else
				return -1;
		}

		// move to next parameter
		pos += 2 + buf[pos + 1];
	}

	return -1;
}

bool beacon_set_chan(uint8_t *buf, size_t len, uint8_t chan)
{
	size_t pos = get_offset_fixedparams(buf, len);
	if (pos == 0) return false;

	// iterate over all tagged parameters of the beacon frame
	while (pos < len)
	{
		// is it the SSID element?
		if (buf[pos] == 3)
		{
			buf[pos + 2] = chan;
			return true;
		}

		// move to next parameter
		pos += 2 + buf[pos + 1];
	}

	return false;
}



