#ifndef JAMMER_MACADDR_H
#define JAMMER_MACADDR_H

#include <stdint.h>
#include <string.h>
#include <string>
//#include <cstddef>
//#include <iostream>

class MacAddr {
	public:
		/** throws std::invalid_argument if invalid mac */
		static MacAddr parse(const char *strmac);
		static MacAddr random();

		// hash function
		std::size_t operator()(const MacAddr &mac) const;
		// compare function
		bool operator()(const MacAddr &mac1, const MacAddr &mac2) const;
		// subscript
		uint8_t & operator[](const size_t index);
		const uint8_t & operator[](const size_t index) const;
		// equality
		bool operator==(const MacAddr &other) const { return memcmp(macaddr, other.macaddr, 6) == 0; }
		bool operator!=(const MacAddr &other) const { return !(*this == other); }

		MacAddr() {}
		MacAddr(const uint8_t mac[6]) { memcpy(macaddr, mac, 6); }
		std::string tostring() const;
		void setbuf(uint8_t mac[6]) const { memcpy(mac, macaddr, 6); }
		bool empty() const;
		bool multicast() const { return (macaddr[0] & 1); }

	private:
		friend std::ostream & operator<<(std::ostream &os, const MacAddr &mac);
		uint8_t macaddr[6];
};

#endif // JAMMER_MACADDR_H
