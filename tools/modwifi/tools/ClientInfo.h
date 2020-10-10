#ifndef JAMMER_CLIENTINFO_H
#define JAMMER_CLIENTINFO_H

#include <set>
#include <string.h>

#include "SeqnumInfo.h"
#include "eapol.h"

/**
 * Used to store connected clients, new/old sequence numbers, and EAPOL handshake
 */
class ClientInfo
{
public:
	static int test_new_seqnums();

	ClientInfo();
	ClientInfo(const uint8_t mac[6]);
	ClientInfo(const uint8_t mac[6], const uint8_t bssid[6], const char *pw, const char *essid);
	bool is_new_seqnum(uint16_t seqnum);
	void set_key_info(const uint8_t bssid[6], const char *passphrase, const char *essid);

private:
	void remove_old_seqnums();
	void remove_all_seqnums();

public:
	// MAC address of client
	uint8_t mac[6];
	// Latest captured sequence numbers
	std::set<SeqnumInfo> seqnums;
	// EAPOL handshake info
	eapol_sta_info keys;
};

#endif // JAMMER_CLIENTINFO_H
