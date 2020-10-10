#ifndef EAPOL_H__
#define EAPOL_H__

#include <stdint.h>
#include <time.h>


#define TK_BITS		32

union tkip_ptk
{
	uint8_t ptk[32 + TK_BITS];
	/** IEEE 802.11-2012 11.6.1.3 - Pairwise key hierarchy */
	struct {
		/** used to calculate MIC of eapol frames */
		uint8_t kck[16];
		/** used to encrypt data in eapol frames */
		uint8_t kek[16];

		/** IEEE 802.11-2012 11.7.1 - Mapping PTK to TKIP keys */
		/** temporal key used to encrypt packets */
		uint8_t enc[16];
		/** MIC key for AP to station */
		uint8_t micfromds[8];
		/** MIC key for station to AP */
		uint8_t mictods[8];
	};
};

union tkip_gtk
{
	uint8_t gtk[TK_BITS];
	/** IEEE 802.11-2012 11.6.1.4 - Group key hierarchy */
	struct {
		/** IEEE 802.11-2012 11.7.2 - Mapping GTK to TKIP keys */
		/** temporal key used to encrypt packets */
		uint8_t enc[16];
		/** temporal key used to calculate MIC */
		uint8_t micfromds[8];
		/** temporal key used to calculate MIC */
		uint8_t mictods[8];
	};
};

struct eapol_rns_ie
{
	uint8_t bElementID;
	uint8_t bLength;
	uint8_t  OUI[4];
	uint16_t iVersion;
	uint8_t  multicastOUI[4];
	uint16_t iUnicastCount;      /* this should always be 1 for WPA client */
	uint8_t  unicastOUI[4];
	uint16_t iAuthCount;         /* this should always be 1 for WPA client */
	uint8_t  authOUI[4];
	uint16_t iWPAcap;
};

/**
 * EAPOL handshake information of a specific STA
 */
struct eapol_sta_info
{
	struct eapol_sta_info *next;  /* next supplicant              */

	/** last EAPOL frame we got from client */
	int lastframenum;

	/** information we have successfully captured */
	struct {
		bool pmk;
		bool anonce;
		bool snonce;
		bool ptk;
		bool gtk;
	} state;
	time_t wpa_time;              /* time when the wpa handshake arrived */

	/** handshake parameters */
	char essid[128];               /* essid of the network         */
	uint8_t stmac[6];              /* supplicant MAC               */
	uint8_t bssid[6];              /* authenticator MAC            */
	uint8_t snonce[32];            /* supplicant nonce             */
	uint8_t anonce[32];            /* authenticator nonce          */
	int keyver;

	/** the keys */
	char psk[64];                  /* shared passphrase among the clients */
	unsigned char pmk[32];         /* pmk derived from the essid and psk */
	union tkip_ptk ptk;
	tkip_gtk gtk;                  /* groupwise transient key      */

	bool valid_ptk;                /* has the PTK been verified to be valid? */
};


enum EapolKeyVer {
	EapolKeyVer_HMAC_MD5_RC4 = 1,
	EapolKeyVer_HMAC_SHA1_AES = 2,
	EapolKeyVer_AES_128_CMAC = 3
};

struct eapol_update {
	uint8_t framenum : 3;
	uint8_t gotptk : 1;
	uint8_t gotgtk : 1;
};

eapol_update check_eapol_handshake(eapol_sta_info *sta, uint8_t *buf, size_t len);


#endif // EAPOL_H__
