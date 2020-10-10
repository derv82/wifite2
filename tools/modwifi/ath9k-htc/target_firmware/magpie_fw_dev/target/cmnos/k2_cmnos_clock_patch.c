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
#include "athos_api.h"
#include "sys_cfg.h"

a_uint32_t ref_clk = 0;
extern a_uint32_t cticks;

// clock change 
//
void cmnos_clock_init_patch(a_uint32_t refclk)
{
    ref_clk = refclk;
}

// retrieve current clock setting
// 
a_uint32_t cmnos_refclk_speed_get_patch(void)
{
    return ref_clk;
}


// software emulate delay function
//
void cmnos_delay_us_patch(int us)
{
    a_uint32_t start_time = NOW();
    unsigned int num_ticks = us*ref_clk; // system_freq == number of ticks per 1us
    
    while ( (NOW() - start_time) < num_ticks) {
        /* busy spin */
        ;
    }
}


// software emulate microsecond ticks
//
void cmnos_tick_patch(void)
{
    static a_uint32_t last_tick = 0;
    a_uint32_t current_tick = NOW();
    a_uint32_t delta_tick;

    delta_tick = (A_UINT32 ) (current_tick - last_tick)/(ref_clk<<10);

    if( delta_tick > 0 )
        last_tick = current_tick;

    cticks += delta_tick;
}

// get current sysmem up time in milliseconds based
// 
a_uint32_t cmnos_milliseconds_patch(void)
{
    cmnos_tick_patch();
    
    return (cticks);
}

