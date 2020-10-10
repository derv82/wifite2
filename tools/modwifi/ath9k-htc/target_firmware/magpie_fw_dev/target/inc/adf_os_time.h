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
 * @file adf_os_time.h
 * This file abstracts time related functionality.
 */
#ifndef _ADF_OS_TIME_H
#define _ADF_OS_TIME_H

#include <adf_os_time_pvt.h>

/**
 * @brief count the number of ticks elapsed from the time when
 *        the system booted
 * 
 * @return ticks
 */
static inline unsigned long
adf_os_ticks(void)
{
	return __adf_os_ticks();
}

/**
 * @brief convert ticks to milliseconds
 *
 * @param[in] ticks number of ticks
 * @return time in milliseconds
 */ 
static inline a_uint32_t
adf_os_ticks_to_msecs(unsigned long ticks)
{
	return (__adf_os_ticks_to_msecs(ticks));
}

/**
 * @brief convert milliseconds to ticks
 *
 * @param[in] time in milliseconds
 * @return number of ticks
 */ 
static inline unsigned long
adf_os_msecs_to_ticks(a_uint32_t msecs)
{
	return (__adf_os_msecs_to_ticks(msecs));
}

/**
 * @brief Return a monotonically increasing time. This increments once per HZ ticks
 */
static inline unsigned long
adf_os_getuptime(void)
{
    return (__adf_os_getuptime());
}

/**
 * @brief Delay in microseconds
 *
 * @param[in] microseconds to delay
 */
static inline void
adf_os_udelay(int usecs)
{
    __adf_os_udelay(usecs);
}

/**
 * @brief Delay in milliseconds.
 *
 * @param[in] milliseconds to delay
 */
static inline void
adf_os_mdelay(int msecs)
{
    __adf_os_mdelay(msecs);
}

/**
 * @brief Check if _a is later than _b.
 */ 
#define adf_os_time_after(_a, _b)       __adf_os_time_after(_a, _b)

/**
 * @brief Check if _a is prior to _b.
 */ 
#define adf_os_time_before(_a, _b)      __adf_os_time_before(_a, _b)

/**
 * @brief Check if _a atleast as recent as _b, if not later.
 */ 
#define adf_os_time_after_eq(_a, _b)    __adf_os_time_after_eq(_a, _b)

#endif
    

