#ifndef JAMMER_CRC_H
#define JAMMER_CRC_H

#include <stdint.h>
#include <stddef.h>

uint32_t calc_crc(void *buf, size_t len);
bool endswith_valid_crc(void *buf, size_t len);

#endif // JAMMER_CRC_H
