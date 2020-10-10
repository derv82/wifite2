#ifndef JAMMER_UTIL_H
#define JAMMER_UTIL_H

#include <time.h>
#include <stdint.h>
#include <set>

#include "osal_wi.h"

bool is_empty(const uint8_t *buffer, size_t len);

static inline uint64_t absdiff64(uint64_t x, uint64_t y) {
	return x > y ? x - y : y - x;
}

// Timing functions - TODO: Convert these to C++ classes
/**
 * -1	rhs < lhs
 * 0	rhs = lhs
 * 1	rhs > lhs
 */
int timespec_cmp(const struct timespec *rhs, const struct timespec *lhs);

void timespec_diff(const struct timespec *end, const struct timespec *start,
	struct timespec *result);
void timespec_add(const struct timespec *x, const struct timespec *y,
	struct timespec *result);
void timespec_add_nsec(struct timespec *x, int nsecs);
inline void timespec_add_usec(struct timespec *x, int usecs) {
	timespec_add_nsec(x, usecs * 1000);
}
inline uint64_t timespec_to_64us(struct timespec *x) {
	return (uint64_t)x->tv_sec * 1000000 + x->tv_nsec / 1000;
}

// Debugging
void dump_packet(unsigned char* h80211, int len);

// Other
bool getmac(const char *macaddr, uint8_t mac[6]);

// IEEE 802.11 utility functions
const char * frametype(int type);
const char * framesubtype(int type, int subtype);

size_t add_qos_hdr(uint8_t *buf, size_t len, size_t maxlen);

// Beacon functions
int get_beacon(wi_dev *ap, uint8_t *buf, size_t len, char *ssid, const MacAddr &mac);
bool beacon_get_ssid(uint8_t *buf, size_t len, char *outssid, size_t outlen);
bool beacon_set_ssid(uint8_t *buf, size_t *len, size_t maxlen, char *newssid);
int beacon_get_chan(uint8_t *buf, size_t len);
bool beacon_set_chan(uint8_t *buf, size_t len, uint8_t chan);

// Template shit
template<class T> typename std::set<T>::iterator upper_inclusive(std::set<T> &cont, T value)
{
	// Returns an iterator to the first element which goes after val
	auto it = cont.upper_bound(value);

	if (it != cont.end()) {
		//printf("Upper bound %d = %d\n", value.getnum(), it->getnum());
	} else {
		//printf("%d has no upper bound (cont size %d)\n",
		//	value.getnum(), cont.size());
	}

	auto prev = it;
	if (it != cont.begin()) --prev;

	// a == b iff !(a < b || b < a)
	if ( !(*prev < value || *prev < value) ) {
		//printf("\tgoing to previous element %d\n", prev->getnum());
		it = prev;
	} else {
		//printf("\tprevious element is smaller\n");
	}

	return it;
};

#endif // JAMMER_UTIL_H


