#ifndef ieee80211header_h__
#define ieee80211header_h__

#include <stdint.h>

#define PREPACK __attribute__ ((__packed__))

/** http://www.radiotap.org/ */
typedef struct PREPACK ieee80211_radiotap_header {
        uint8_t        it_version;     /* set to 0 */
        uint8_t        it_pad;
        uint16_t       it_len;         /* entire length */
        uint32_t       it_present;     /* fields present */
} ieee80211_radiotap_header;

/** hardcoded radiotap header for ath9k_htc devices */
typedef struct PREPACK ieee80211_radiotap_ath9k_htc {
        uint8_t        it_version;     /* set to 0 */
        uint8_t        it_pad;
        uint16_t       it_len;         /* entire length */
        uint32_t       it_present;     /* fields present */
        uint64_t       tsf;
        uint8_t        flags;
        uint8_t        rate;
        uint16_t       frequency;
        uint16_t       channelflags;
        int8_t         dbsignal;
	uint8_t        antenna;
        uint16_t       rxflags;
	uint8_t        padding[8];
} ieee80211_radiotap_ath9k_htc;

#define RX_FLAG_SPECTRAL_REPORT		0x0100

#define IEEE80211_FCSLEN		4
// Minimum size of ACK
#define IEEE80211_MINSIZE		10

enum TYPE {
	TYPE_MNGMT = 0,
	TYPE_CNTRL = 1,
	TYPE_DATA  = 2
};

enum CONTROL {
	CONTROL_ACK  = 13
};

/** IEEE Std 802.11-2007 paragraph 7.1 MAC frame formats */
typedef struct PREPACK ieee80211header {
	/** 7.1.3.1 Frame Control Field */
	struct PREPACK fc
	{
		uint8_t version : 2;
		/** see IEEE802.11-2012 8.2.4.1.3 Type and Subtype fields */
		uint8_t type : 2;
		uint8_t subtype : 4;
		uint8_t tods : 1;
		uint8_t fromds : 1;
		uint8_t morefrag : 1;
		uint8_t retry : 1;
		uint8_t pwrmgt : 1;
		uint8_t moredata : 1;
		uint8_t protectedframe : 1;
		uint8_t order : 1;
	} fc;
	/** 7.1.3.2 Duration/ID field. Content varies with frame type and subtype. */
	uint16_t duration_id;
	/** 7.1.3.3 Address fields. For this program we always assume 3 addresses. */
	uint8_t addr1[6];
	uint8_t addr2[6];
	uint8_t addr3[6];
	/** 7.1.3.4 Sequence Control Field */
	struct PREPACK sequence
	{
		uint8_t fragnum : 4;
		uint16_t seqnum : 12;
	} sequence;
} ieee80211header;

static inline bool ieee80211_broadcast_mac(uint8_t mac[6]) { return mac[0] & 0x01; }
static inline bool ieee80211_dataqos(const ieee80211header *hdr) {
	return hdr->fc.type == TYPE_DATA && hdr->fc.subtype >= 8 && hdr->fc.subtype <= 12;
}

/** 7.1.3.5 QoS Control field. This is not present in all frames, and exact
 * usage of the bits depends on the type/subtype. Here we assume QoS data frame. */
typedef struct PREPACK ieee80211qosheader {
	// 7.1.3.5.1 TID subfield. Allowed values depend on Access Policy (7.3.2.30).
	uint8_t tid : 4;
	uint8_t eosp : 1;
	uint8_t ackpolicy : 2;
	uint8_t reserved : 1;
	uint8_t appsbufferstate;
} ieee80211qosheader;

/** IEEE Std 802.11-2007 paragraph 8.3.3.2 TKIP MPDU formats */
typedef struct PREPACK tkipheader
{
	struct PREPACK iv
	{
		uint8_t tsc1;
		uint8_t wepseed;
		uint8_t tsc0;
		uint8_t reserved : 5;
		uint8_t extendediv : 1;
		uint8_t keyid : 2;
	} iv;
	struct PREPACK eiv
	{
		uint8_t tsc2;
		uint8_t tsc3;
		uint8_t tsc4;
		uint8_t tsc5;
	} eiv;
} tkipheader;

/** IEEE Std 802.11-2007 paragraph 8.3.3.2 TKIP MPDU formats */
typedef struct PREPACK tkiptail
{
	uint8_t mic[8];
	uint8_t icv[4];
} tkiptail;

static const int TIMEUNIT_USEC = 1024;

typedef struct PREPACK ieee802211fixedparams {
	// Value of the timing synchronization function (TSF)
	uint64_t timestamp;
	// Number of time units (TUs) between target beacon transmission times (TBTTs)
	uint16_t interval;
	// Capabilities (not detected yet..)
	uint16_t capabilities;
} ieee802211fixedparams;

typedef struct PREPACK llcsnaphdr
{
	uint8_t dsap;
	uint8_t ssap;
	uint8_t ctrl;
	uint8_t oui[3];
	uint16_t type;
} llcsnaphdr;

static const uint16_t DOT1X_AUTHENTICATION = 0x8E88;

struct PREPACK ieee80211xauth
{
	uint8_t ver;
	uint8_t type;
	uint16_t len;
	uint8_t desctype;
	struct PREPACK {
		uint8_t mic : 1;
		uint8_t secure : 1;
		uint8_t error : 1;
		uint8_t request : 1;
		uint8_t encdata : 1;
		uint8_t pad : 3;

		uint8_t keyver : 3;
		uint8_t type : 1;
		uint8_t idx : 2;
		uint8_t install : 1;
		uint8_t ack : 1;
	} inf;
	uint16_t keylen;
	uint64_t counter;
	uint8_t nonce[32];
	uint8_t iv[16];
	uint8_t rsc[8];
	uint8_t id[8];
	uint8_t mic[16];
	uint16_t datalen;
} __attribute__((packed));

// TODO: put this somewhere else
struct PREPACK arppacket
{
	uint16_t hardwaretype;
	uint16_t protocoltype;
	uint8_t hardwaresize;
	uint8_t protocolsize;
	uint16_t opcode;
	uint8_t sendermac[6];
	uint8_t senderip[4];
	uint8_t targetmac[6];
	uint8_t targetip[4];
} __attribute__((packed));

#endif // ieee80211header_h__
