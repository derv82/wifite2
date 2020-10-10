#include <assert.h>
#include <unistd.h>
#include <stdexcept>
#include <iostream>

#include "ieee80211header.h"
#include "util.h"

#include "SeqnumStats.h"

static const uint16_t SEQNUM_DELTA = 20;
static const struct timespec SEQNUM_TIMEOUT = {0, 25 * 1000 * 1000}; // 25ms


/*static*/ int SeqnumStats::test_new_seqnums()
{
#define IS_NEW(x) stats.is_new(&(x), sizeof(x))

#define SHOULD_BE_NEW(x, num, rval) \
	do { \
	(x).sequence.seqnum = num; \
	if (!stats.is_new(&(x), sizeof(x))) return rval; \
	} while (0);

#define SHOULD_BE_OLD(x, num, rval) \
	do { \
	(x).sequence.seqnum = num; \
	if (stats.is_new(&(x), sizeof(x))) return rval; \
	} while (0);

	ieee80211header hdr;
	SeqnumStats stats;

	memset(&hdr, 0, sizeof(hdr));

	// ======================================
	//	Tests from same SeqnumType
	// ======================================

	// Add new seqnums
	SHOULD_BE_NEW(hdr, 10, -1);
	SHOULD_BE_NEW(hdr, 110, -1);
	SHOULD_BE_NEW(hdr, 500, -1);

	// Now these should be old
	SHOULD_BE_OLD(hdr, 10, -2);
	SHOULD_BE_OLD(hdr, 5, -2);
	SHOULD_BE_OLD(hdr, 1, -2);

	SHOULD_BE_OLD(hdr, 110, -3);
	SHOULD_BE_OLD(hdr, 100, -3);

	SHOULD_BE_OLD(hdr, 500, -4);
	SHOULD_BE_OLD(hdr, 499, -4);

	// And these should be new
	SHOULD_BE_NEW(hdr, 11, -5);
	SHOULD_BE_NEW(hdr, 13, -5);
	SHOULD_BE_NEW(hdr, 120, -5);
	SHOULD_BE_NEW(hdr, 505, -5);
	SHOULD_BE_NEW(hdr, 535, -5);

	SHOULD_BE_NEW(hdr, 120 - SEQNUM_DELTA - 10, -6);
	SHOULD_BE_NEW(hdr, 505 - SEQNUM_DELTA - 10, -6);

	// Test automatic expiration - these should be new again
	usleep(100 * 1000);
	SHOULD_BE_NEW(hdr, 10, -7);
	SHOULD_BE_NEW(hdr, 110, -7);
	SHOULD_BE_NEW(hdr, 500, -7);

	// Again test automatic expiration
	usleep(100 * 1000);
	SHOULD_BE_NEW(hdr, 10, -8);
	SHOULD_BE_NEW(hdr, 110, -8);
	SHOULD_BE_NEW(hdr, 500, -8);

	// ========================================
	//	Tests from different SeqnumType
	// ========================================

	stats.reset();
	memset(&hdr, 0, sizeof(hdr));

	SHOULD_BE_NEW(hdr, 10, -9);
	SHOULD_BE_OLD(hdr, 10, -9);
	SHOULD_BE_OLD(hdr, 5, -9);
	SHOULD_BE_NEW(hdr, 20, -9);

	hdr.addr1[5] = '\xff';
	SHOULD_BE_NEW(hdr, 10, -10);
	SHOULD_BE_OLD(hdr, 10, -10);
	SHOULD_BE_OLD(hdr, 5, -10);
	SHOULD_BE_NEW(hdr, 20, -10);

	hdr.addr2[5] = '\xff';
	SHOULD_BE_NEW(hdr, 10, -11);
	SHOULD_BE_OLD(hdr, 10, -11);
	SHOULD_BE_OLD(hdr, 5, -11);
	SHOULD_BE_NEW(hdr, 20, -11);

	hdr.fc.type = 1;
	SHOULD_BE_NEW(hdr, 10, -12);
	SHOULD_BE_OLD(hdr, 10, -12);
	SHOULD_BE_OLD(hdr, 5, -12);
	SHOULD_BE_NEW(hdr, 20, -12);

	hdr.fc.subtype = 1;
	SHOULD_BE_NEW(hdr, 10, -13);
	SHOULD_BE_OLD(hdr, 10, -13);
	SHOULD_BE_OLD(hdr, 5, -13);
	SHOULD_BE_NEW(hdr, 20, -13);

	// ========================================
	//	Tests from different priority
	// ========================================

	uint8_t buf[sizeof(ieee80211header) + sizeof(ieee80211qosheader)];
	ieee80211header *hdr2 = (ieee80211header*)buf;
	ieee80211qosheader *qos = (ieee80211qosheader*)(buf + sizeof(ieee80211header));

	stats.reset();
	memset(buf, 0, sizeof(buf));
	hdr2->fc.type = TYPE_DATA;
	hdr2->fc.subtype = 8;

	hdr2->sequence.seqnum = 10;
	if (!stats.is_new(buf, sizeof(buf))) return -14;
	if (stats.is_new(buf, sizeof(buf))) return -14;
	hdr2->sequence.seqnum = 5;
	if (stats.is_new(buf, sizeof(buf))) return -14;

	qos->tid = 1;
	if (!stats.is_new(buf, sizeof(buf))) return -15;
	if (stats.is_new(buf, sizeof(buf))) return -15;
	hdr2->sequence.seqnum = 5;
	if (stats.is_new(buf, sizeof(buf))) return -15;

	qos->tid = 2;
	if (!stats.is_new(buf, sizeof(buf))) return -16;
	if (stats.is_new(buf, sizeof(buf))) return -16;
	hdr2->sequence.seqnum = 5;
	if (stats.is_new(buf, sizeof(buf))) return -16;

	return 0;
#undef SHOULD_BE_OLD
#undef SHOULD_BE_NEW
#undef IS_NEW
}


bool SeqnumStats::is_new(void *buf, size_t buflen)
{
	ieee80211header *hdr = (ieee80211header*)buf;

	assert(buflen >= sizeof(ieee80211header));

	try {
		// note: list is constructed using default constructor if SeqnumType not present
		std::set<SeqnumInfo> &seqnums = map[SeqnumType::frombuf(buf, buflen)];
		return is_new_seqnum(seqnums, hdr->sequence.seqnum);
	} catch (const std::invalid_argument &ex) {
		std::cerr << "\tWarning: " << ex.what() << std::endl;
		dump_packet((uint8_t*)buf, buflen);
	}

	return false;	
}


bool SeqnumStats::is_new_seqnum(std::set<SeqnumInfo> &seqnums, uint16_t seqnum)
{
	SeqnumInfo seqinfo(seqnum);

	remove_old_seqnums(seqnums);

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


void SeqnumStats::remove_old_seqnums(std::set<SeqnumInfo> &seqnums)
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



