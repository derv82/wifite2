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
#ifndef _ADF_OS_TIME_PVT_H
#define _ADF_OS_TIME_PVT_H

#include <cmnos_api.h>
#include "Magpie_api.h"

/**
 * @brief this code is modified version of tvtohz(9) which
 *        returns signed int which we don't require, hence we
 *        got rid of the type casting thing
 * 
 * @return unsigned long
 */
static inline unsigned long
__adf_os_ticks(void)
{
    return MSEC_TO_TICK(A_MILLISECONDS());
}
static inline a_uint32_t
__adf_os_ticks_to_msecs(unsigned long ticks)
{
	return TICK_TO_MSEC(ticks);
}
static inline unsigned long
__adf_os_msecs_to_ticks(a_uint32_t msecs)
{
	return MSEC_TO_TICK(msecs);
}
static inline unsigned long
__adf_os_getuptime(void)
{
    return MSEC_TO_TICK(A_MILLISECONDS());;      
}

static inline void
__adf_os_udelay(int usecs)
{
    A_DELAY_USECS(usecs);
}

static inline void
__adf_os_mdelay(int msecs)
{
    A_DELAY_USECS(msecs*1000);
}

#endif
