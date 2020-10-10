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
#ifndef _ADF_OS_TIMER_PVT_H
#define _ADF_OS_TIMER_PVT_H

#include <cmnos_api.h>
#include "Magpie_api.h"


typedef struct 
{
	A_timer_t 				*magpie_timer;
	adf_os_timer_func_t 	timer_func;
}__adf_os_timer_t;

//typedef A_timer_t 	__adf_os_timer_t;

void
__adf_os_timer_func(A_HANDLE timer_handle, void *arg);

/* 
 * Initialize a timer
 */
static inline void
__adf_os_timer_init(adf_os_handle_t  hdl, __adf_os_timer_t   *timer,
                    adf_os_timer_func_t  func, void *arg)
{
    timer->timer_func = func;
    A_INIT_TIMER(timer->magpie_timer, __adf_os_timer_func, arg);
}

/* 
 * start a timer 
 */
static inline void
__adf_os_timer_start(__adf_os_timer_t *timer, int msec)
{
    A_TIMEOUT_MS(timer->magpie_timer, msec);
}
/*
 * Cancel a timer
 *
 * Return: TRUE if timer was cancelled and deactived,
 *         FALSE if timer was cancelled but already got fired.
 */
static inline a_bool_t
__adf_os_timer_cancel(__adf_os_timer_t *timer)
{
	A_UNTIMEOUT(timer->magpie_timer);
	return A_TRUE;
}

/*
 * XXX Synchronously canel a timer
 *
 * Return: TRUE if timer was cancelled and deactived,
 *         FALSE if timer was cancelled but already got fired.
 *
 * Synchronization Rules:
 * 1. caller must make sure timer function will not use
 *    adf_os_set_timer to add iteself again.
 * 2. caller must not hold any lock that timer function
 *    is likely to hold as well.
 * 3. It can't be called from interrupt context.
 */
static inline a_bool_t
__adf_os_timer_sync_cancel(__adf_os_timer_t *timer)
{
    // @TODO: IS OK??
    A_UNTIMEOUT(timer->magpie_timer);
    return A_TRUE;
}


#endif
