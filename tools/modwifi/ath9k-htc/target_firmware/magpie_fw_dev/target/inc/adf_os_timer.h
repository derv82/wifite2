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
 * @file adf_os_timer.h
 * This file abstracts OS timers.
 */

#ifndef _ADF_OS_TIMER_H
#define _ADF_OS_TIMER_H

#include <adf_os_types.h>
#include <adf_os_timer_pvt.h>


/**
 * @brief Platform timer object
 */
typedef __adf_os_timer_t           adf_os_timer_t;


/**
 * @brief Initialize a timer
 * 
 * @param[in] hdl       OS handle
 * @param[in] timer     timer object pointer
 * @param[in] func      timer function
 * @param[in] context   context of timer function
 */
static inline void
adf_os_timer_init(adf_os_handle_t      hdl,
                  adf_os_timer_t      *timer,
                  adf_os_timer_func_t  func,
                  void                *arg)
{
    __adf_os_timer_init(hdl, timer, func, arg);
}

/**
 * @brief Start a one-shot timer
 * 
 * @param[in] timer     timer object pointer
 * @param[in] msec      expiration period in milliseconds
 */
static inline void
adf_os_timer_start(adf_os_timer_t *timer, int msec)
{
    __adf_os_timer_start(timer, msec);
}

/**
 * @brief Cancel a timer
 *
 * @param[in] timer     timer object pointer
 * 
 * @retval    TRUE      timer was cancelled and deactived
 * @retval    FALSE     timer was cancelled but already got fired.
 */
static inline a_bool_t
adf_os_timer_cancel(adf_os_timer_t *timer)
{
    return __adf_os_timer_cancel(timer);
}

#endif

