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
#ifndef __CLOCK_API_H__
#define __CLOCK_API_H__

#define TICK_MSEC_RATIO			1
#define TICK_TO_MSEC(tick)		((tick)/TICK_MSEC_RATIO)
#define MSEC_TO_TICK(msec)		((msec)* TICK_MSEC_RATIO)

typedef struct date_s {
	uint16_t miliseconds;
	uint16_t seconds;
	uint16_t minutes;
	uint16_t hours;
} A_DATE_T;

struct clock_api {
	void (* _clock_init)(A_UINT32 ref_clk);
	void (* _clockregs_init)(void);
	A_UINT32 (* _uart_frequency)(void);
	void (* _delay_us)(int);
	void (* _wlan_band_set)(int);
	A_UINT32 (* _refclk_speed_get)(void);
	A_UINT32 (* _milliseconds)(void);
	void (* _sysclk_change)(uint32_t sys_clk);
	A_UINT32 (* _sysclk_get)(void);

	void (* _clock_tick)(void);
};

#endif /* __CLOCK_API_H__ */
