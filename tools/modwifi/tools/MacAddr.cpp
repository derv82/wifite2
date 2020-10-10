#include <string.h>
#include <stdlib.h>

#include <iostream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include "util.h"
#include "MacAddr.h"


/*static*/ MacAddr MacAddr::parse(const char *strmac)
{
	char normaddr[32];
	int intmac[6];
	uint8_t mac[6];
	int i, len;

	if (strmac == NULL)
		throw std::invalid_argument("strmac is NULL");

	len = strlen(strmac);
	if (len < 11 || len > 17)
		throw std::invalid_argument("MAC must be between 11 and 17 chars");

	// Normalize the input
	strncpy(normaddr, strmac, sizeof(normaddr));
	for (i = 0; normaddr[i] != '\x0'; ++i) {
		if (normaddr[i] == '-')
			normaddr[i] = ':';
	}

	// Parse normalized mac address
	// FIXME: errors in last octet not detected.
	// FIXME: too large numbers can be given.
	if (sscanf(normaddr, "%x:%x:%x:%x:%x:%x", &intmac[0], &intmac[1],
		&intmac[2], &intmac[3], &intmac[4], &intmac[5]) != 6) {
		throw std::invalid_argument("Unable to parse MAC address");
	}

	// Copy to output
	for (i = 0; i < 6; ++i) {
		mac[i] = intmac[i];
	}

	return MacAddr(mac);
}


/*static*/ MacAddr MacAddr::random()
{
	MacAddr mac;

	mac.macaddr[0] = 0;
	for (size_t i = 1; i < sizeof(mac.macaddr); ++i)
		mac.macaddr[i] = rand();

	return mac;
}


std::size_t MacAddr::operator()(const MacAddr &mac) const
{
	uint64_t intmac = 0;

	for (int i = 5; i >= 0; --i)
		intmac = (intmac << 8) + mac.macaddr[i];

	// this is a prime
	return intmac % 0xFFFFFFFB;
}

bool MacAddr::operator()(const MacAddr &mac1, const MacAddr &mac2) const
{
	return memcmp(mac1.macaddr, mac2.macaddr, 6) == 0;
}

uint8_t & MacAddr::operator[](const size_t index)
{
	if (index >= sizeof(macaddr))
		throw std::out_of_range("Invalid subscript to MAC address");

	return macaddr[index];
}

const uint8_t & MacAddr::operator[](const size_t index) const
{
	if (index >= sizeof(macaddr))
		throw std::out_of_range("Invalid subscript to MAC address");

	return macaddr[index];
}


std::string MacAddr::tostring() const
{
	std::ostringstream ss;
	std::ios state(NULL);
	size_t i;

	state.copyfmt(std::cout);

	ss << std::hex << std::setfill('0');
	for (i = 0; i < sizeof(macaddr) - 1; ++i) {
		ss << std::setw(2) << (int)macaddr[i] << ':';
	}
	ss << std::setw(2) << (int)macaddr[i];

	std::cout.copyfmt(state);

	return ss.str();
}


bool MacAddr::empty() const
{
	return is_empty(macaddr, 6);
}


/*friend*/ std::ostream & operator<<(std::ostream &os, const MacAddr &mac)
{
	return os << mac.tostring();
}


