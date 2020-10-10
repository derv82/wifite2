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
#ifndef __WDT_API_H__
#define __WDT_API_H__

typedef enum {
	WDT_ACTION_NO = 0,      // bit1, bit0: 00
	WDT_ACTION_INTR,        // bit1, bit0: 01
	WDT_ACTION_NMI,         // bit1, bit0: 10
	WDT_ACTION_RESET,     // bit1, bit0: 11

	WDT_ACTION_UNKNOWN
} T_WDT_ACTION_TYPE;

typedef enum {
	WDT_TIMEOUT = 1,
	WDT_ACTION,

	WDT_UNKNOWN
} T_WDT_CMD_TYPE;

typedef struct {
	uint32_t cmd;
	union {
		uint32_t timeout;
		uint32_t action;
	};
}T_WDT_CMD;

typedef enum {
	ENUM_WDT_BOOT = 1,
	ENUM_COLD_BOOT,
	ENUM_SUSP_BOOT,

	// add above here
	ENUM_UNKNOWN_BOOT
} T_BOOT_TYPE;


/*!- interface of watchdog timer
 *
 */
struct wdt_api {
	void (* _wdt_init)(void);
	void (* _wdt_enable)(void);
	void (* _wdt_disable)(void);
	void (* _wdt_set)(T_WDT_CMD);
	void (* _wdt_task)(void);
	void (* _wdt_reset)(void);
	T_BOOT_TYPE (*_wdt_last_boot)(void);
};
#endif /* __WDT_API_H__ */

