/*
 * Copyright (c) 2013 Qualcomm Atheros, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the
 * disclaimer below) provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *  * Neither the name of Qualcomm Atheros nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
 * GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
 * HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
 * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
 * IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
/**
 * @ingroup adf_os_public
 * @file adf_os_io.h
 * This file abstracts I/O operations.
 */

#ifndef _ADF_OS_IO_H
#define _ADF_OS_IO_H

#include <adf_os_io_pvt.h>

static inline uint8_t ioread8(const volatile uint32_t addr)
{
	return *(const volatile uint8_t *) addr;
}

static inline uint16_t ioread16(const volatile uint32_t addr)
{
	return *(const volatile uint16_t *) addr;
}

static inline uint32_t ioread32(const volatile uint32_t addr)
{
	return *(const volatile uint32_t *) addr;
}

static inline void iowrite8(volatile uint32_t addr, const uint8_t b)
{
	*(volatile uint8_t *) addr = b;
}

static inline void iowrite16(volatile uint32_t addr, const uint16_t b)
{
	*(volatile uint16_t *) addr = b;
}

static inline void iowrite32(volatile uint32_t addr, const uint32_t b)
{
	*(volatile uint32_t *) addr = b;
}

static inline void io8_rmw(volatile uint32_t addr,
			    const uint8_t set, const uint8_t clr)
{
	uint8_t val;

	val = ioread8(addr);
	val &= ~clr;
	val |= set;
	iowrite8(addr, val);
}

static inline void io32_rmw(volatile uint32_t addr,
			    const uint32_t set, const uint32_t clr)
{
	uint32_t val;

	val = ioread32(addr);
	val &= ~clr;
	val |= set;
	iowrite32(addr, val);
}

/* generic functions */
#define io8_set(addr, s)	io8_rmw((addr), (s), 0)
#define io8_clr(addr, c)	io8_rmw((addr), 0, (c))
#define io32_set(addr, s)	io32_rmw((addr), (s), 0)
#define io32_clr(addr, c)	io32_rmw((addr), 0, (c))

/* mac specific functions */
#define ioread32_mac(addr)	ioread32(WLAN_BASE_ADDRESS + (addr))
#define iowrite32_mac(addr, b)	iowrite32(WLAN_BASE_ADDRESS + (addr), (b))

/* usb specific functions */
#define ioread8_usb(addr)	ioread8(USB_CTRL_BASE_ADDRESS | (addr)^3)
#define ioread16_usb(addr)	ioread16(USB_CTRL_BASE_ADDRESS | (addr))
#define ioread32_usb(addr)	ioread32(USB_CTRL_BASE_ADDRESS | (addr))

#define iowrite8_usb(addr, b)	iowrite8(USB_CTRL_BASE_ADDRESS | (addr)^3, (b))
#define iowrite16_usb(addr, b)	iowrite16(USB_CTRL_BASE_ADDRESS | (addr), (b))
#define iowrite32_usb(addr, b)	iowrite32(USB_CTRL_BASE_ADDRESS | (addr), (b))

#define io8_rmw_usb(addr, s, c)	\
		io8_rmw(USB_CTRL_BASE_ADDRESS | (addr)^3, (s), (c))
#define io8_set_usb(addr, s)	\
		io8_rmw(USB_CTRL_BASE_ADDRESS | (addr)^3, (s), 0)
#define io8_clr_usb(addr, c)	\
		io8_rmw(USB_CTRL_BASE_ADDRESS | (addr)^3, 0, (c))

#define io32_rmw_usb(addr, s, c) \
		io32_rmw(USB_CTRL_BASE_ADDRESS | (addr), (s), (c))
#define io32_set_usb(addr, s)	io32_rmw(USB_CTRL_BASE_ADDRESS | (addr), (s), 0)
#define io32_clr_usb(addr, c)	io32_rmw(USB_CTRL_BASE_ADDRESS | (addr), 0, (c))

/**
 * @brief Convert a 16-bit value from network byte order to host byte order
 */
#define adf_os_ntohs(x)                         __adf_os_ntohs(x)

/**
 * @brief Convert a 32-bit value from network byte order to host byte order
 */
#define adf_os_ntohl(x)                         __adf_os_ntohl(x)

/**
 * @brief Convert a 16-bit value from host byte order to network byte order
 */
#define adf_os_htons(x)                         __adf_os_htons(x)

/**
 * @brief Convert a 32-bit value from host byte order to network byte order
 */
#define adf_os_htonl(x)                         __adf_os_htonl(x)

/**
 * @brief Convert a 16-bit value from CPU byte order to little-endian byte order
 */
#define adf_os_cpu_to_le16(x)                   __adf_os_cpu_to_le16(x)

#endif
