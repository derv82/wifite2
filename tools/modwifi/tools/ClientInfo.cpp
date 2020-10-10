#include <unistd.h>

#include "util.h"

#include "ClientInfo.h"


static const uint16_t SEQNUM_DELTA = 20;
static const struct timespec SEQNUM_TIMEOUT = {0, 500 * 1000};

ClientInfo::ClientInfo()
{
	memset(mac, 0, sizeof(mac));
	memset(&keys, 0, sizeof(keys));
}


ClientInfo::ClientInfo(const uint8_t mac[6])
{ 
	memcpy(this->mac, mac, 6);

	memset(&keys, 0, sizeof(keys));
	memcpy(keys.stmac, mac, 6);
}


ClientInfo::ClientInfo(const uint8_t mac[6], const uint8_t bssid[6], const char *pw, const char *essid)
	: ClientInfo(mac)
{
	set_key_info(bssid, pw, essid);
}

/*static*/ int ClientInfo::test_new_seqnums()
{
	ClientInfo client;

	// Add new seqnums
	if (!client.is_new_seqnum(10)) return -1;
	if (!client.is_new_seqnum(110)) return -1;
	if (!client.is_new_seqnum(500)) return -1;

	// Now these should be old
	if (client.is_new_seqnum(10)) return -2;
	if (client.is_new_seqnum(5)) return -2;
	if (client.is_new_seqnum(1)) return -2;

	if (client.is_new_seqnum(110)) return -3;
	if (client.is_new_seqnum(100)) return -3;

	if (client.is_new_seqnum(500)) return -4;
	if (client.is_new_seqnum(499)) return -4;

	// And these should be new
	if (!client.is_new_seqnum(11)) return -5;
	if (!client.is_new_seqnum(13)) return -5;
	if (!client.is_new_seqnum(120)) return -5;
	if (!client.is_new_seqnum(505)) return -5;
	if (!client.is_new_seqnum(535)) return -5;

	if (!client.is_new_seqnum(120 - SEQNUM_DELTA - 10)) return -6;
	if (!client.is_new_seqnum(505 - SEQNUM_DELTA - 10)) return -6;

	// Test automatic expiration - these should be new again
	sleep(1);
	if (!client.is_new_seqnum(10)) return -7;
	if (!client.is_new_seqnum(110)) return -7;
	if (!client.is_new_seqnum(500)) return -7;

	// Again test automatic expiration
	sleep(1);
	if (!client.is_new_seqnum(10)) return -8;
	if (!client.is_new_seqnum(110)) return -8;
	if (!client.is_new_seqnum(500)) return -8;

	return 0;
}


bool ClientInfo::is_new_seqnum(uint16_t seqnum)
{
	SeqnumInfo seqinfo(seqnum);

	remove_old_seqnums();

	// if we don't return, then (seqinfo <= it)
	auto it = upper_inclusive(seqnums, seqinfo);
	if (it == seqnums.end()) {
		// no upper bound? Then it is new (we ignore conside  overflow).
		seqnums.insert(seqinfo);
		//printf("Added %d\n", seqinfo.getnum());
		return true;
	}

	// if this is true, then (it - SEQNUM_DELTA < seqinfo <= it)
	if (it->getnum() - SEQNUM_DELTA < seqnum)
	{
		//printf("Updating time of %d\n", it->getnum());
		it->updatetime();
		return false;
	}

	// we have a new seqnum. Erase the one before it, if it exists
	if (it != seqnums.begin() && (--it)->getnum() + SEQNUM_DELTA > seqnum) {
		//printf("Erasing %d\n", it->getnum());
		seqnums.erase(it);
	}

	// finally insert the new seqnum
	seqnums.insert(seqinfo);
	//printf("Added %d\n", seqinfo.getnum());

	return true;
}


void ClientInfo::set_key_info(const uint8_t bssid[6], const char *passphrase, const char *essid)
{
	memcpy(keys.bssid, bssid, 6);
	strncpy(keys.psk, passphrase, sizeof(keys.psk));
	strncpy(keys.essid, essid, sizeof(keys.essid));
}


void ClientInfo::remove_old_seqnums()
{
	struct timespec now, oldest;
	clock_gettime(CLOCK_MONOTONIC, &now);
	timespec_diff(&now, &SEQNUM_TIMEOUT, &oldest);

	auto it = seqnums.begin();
	while (it != seqnums.end())
	{
		if (timespec_cmp(&it->gettsf(), &oldest) < 0) {
			auto todel = it;
			++it;
			seqnums.erase(todel);
		} else {
			++it;
		}
	}
}


void ClientInfo::remove_all_seqnums()
{
	seqnums.clear();
}


