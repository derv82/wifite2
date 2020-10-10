#ifndef JAMMER_SEQNUMINFO_H
#define JAMMER_SEQNUMINFO_H

#include <stdint.h>
#include <time.h>

class SeqnumInfo
{
public:
	SeqnumInfo(uint16_t seqnum) : seqnum(seqnum) {
		clock_gettime(CLOCK_MONOTONIC, &tsf);
	}
	bool operator<(const SeqnumInfo &other) const {
		return this->seqnum < other.seqnum;
	}
	// changing time isn't considered to modify the object
	void updatetime() const {
		clock_gettime(CLOCK_MONOTONIC, (struct timespec*)&tsf);
	}
	uint16_t getnum() const { return seqnum; }
	const struct timespec & gettsf() const { return tsf; }

public:
	uint16_t seqnum;
	struct timespec tsf;
};

#endif // JAMMER_SEQNUMINFO_H
