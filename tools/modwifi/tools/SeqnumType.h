#ifndef JAMMER_SEQNUMTYPE_H
#define JAMMER_SEQNUMTYPE_H

#include <stdint.h>
#include <stddef.h>

#include "MacAddr.h"

class SeqnumType {
public:
	// factory functions
	static SeqnumType frombuf(void *buf, size_t buflen);

	// hash function
	std::size_t operator()(const SeqnumType &type) const;
	// compare function
	bool operator()(const SeqnumType &type1, const SeqnumType &type2) const { return type1 == type2; }
	// comparison operator
	bool operator==(const SeqnumType &type) const;

private:
	MacAddr macsrc;
	MacAddr macdst;
	uint8_t type;
	uint8_t subtype;
	uint8_t priority;
};

#endif // JAMMER_SEQNUMTYPE_H
