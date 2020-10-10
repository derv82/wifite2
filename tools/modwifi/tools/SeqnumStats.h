#ifndef JAMMER_SEQNUMSTATS_H
#define JAMMER_SEQNUMSTATS_H

#include <stdint.h>
#include <stddef.h>

#include <unordered_map>
#include <set>

#include "SeqnumType.h"
#include "SeqnumInfo.h"

class SeqnumStats {
public:
	static int test_new_seqnums();
	bool is_new(void *buf, size_t buflen);
	void reset() { map.clear(); };

private:
	void remove_old_seqnums(std::set<SeqnumInfo> &seqnums);
	bool is_new_seqnum(std::set<SeqnumInfo> &seqnums, uint16_t seqnum);

	std::unordered_map<SeqnumType, std::set<SeqnumInfo>, SeqnumType, SeqnumType> map;
};

#endif // JAMMER_SEQNUMSTATS_H
