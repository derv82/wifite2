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
#ifndef __ADF_OS_DEFER_PVT_H
#define __ADF_OS_DEFER_PVT_H

#include <adf_os_types.h>
#include <cmnos_api.h>
#include "Magpie_api.h"

/*
 * Because the real function taked an extra int :(
 */
typedef struct {
    adf_os_defer_fn_t  caller_fn;
    void             *caller_arg;
}__adf_os_defer_ctx_t;

/*
 * wrapper around the real task func
 */
typedef struct {
    //struct task          tsk;
    __adf_os_defer_ctx_t ctx;
}__adf_os_defer_t;

//typedef __adf_os_defer_t    __adf_os_bh_t;
typedef A_tasklet_t         __adf_os_bh_t;
typedef __adf_os_defer_t    __adf_os_work_t;

/*
 * wrapper function
 */
extern void __adf_os_defer_func(void *arg, int pending);

/**
 * @brief initiallize the defer function (work or bh)
 * 
 * @param defer
 * @param func
 * @param arg
 */
static inline void __adf_os_init_defer(__adf_os_defer_t  *defer,
                                       adf_os_defer_fn_t    func, 
                                       void              *arg)
{
    defer->ctx.caller_fn  = func;
    defer->ctx.caller_arg = arg;

    //TASK_INIT(&defer->tsk, 0, __adf_os_defer_func, &defer->ctx);
}

static inline void __adf_os_init_work(adf_os_handle_t  hdl,
									  __adf_os_work_t	*work,
									  adf_os_defer_fn_t	func,
									  void 				*arg)
{
	__adf_os_init_defer(work, func, arg);
}

static inline void	__adf_os_init_bh(adf_os_handle_t  hdl,
									 __adf_os_bh_t		*bh,
									 adf_os_defer_fn_t	func,
									 void				*arg)
{
	//__adf_os_init_defer(bh, func, arg);
	A_TASKLET_INIT_TASK(func, arg, bh);
}
static inline void __adf_os_sched_work(adf_os_handle_t  hdl, 
                                       __adf_os_work_t  * work)
{
    //taskqueue_enqueue(taskqueue_thread, &work->tsk);
}
static inline void __adf_os_disable_work(adf_os_handle_t  hdl, 
                                         __adf_os_work_t  * work)
{
    //taskqueue_drain(taskqueue_thread, &work->tsk);
}

static inline void __adf_os_sched_bh(adf_os_handle_t  hdl, 
                                       __adf_os_bh_t  * bh)
{
    A_TASKLET_SCHEDULE(bh);
}

static inline void __adf_os_disable_bh(adf_os_handle_t  hdl, 
                                       __adf_os_bh_t  * bh)
{
    A_TASKLET_DISABLE(bh);
}

#endif 
