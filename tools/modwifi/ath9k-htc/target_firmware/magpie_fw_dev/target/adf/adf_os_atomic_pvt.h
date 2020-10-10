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
#ifndef __ADF_OS_ATOMIC_PVT_H
#define __ADF_OS_ATOMIC_PVT_H

//#include <sys/types.h>
//#include <machine/atomic.h>

#include <adf_os_types.h>

typedef a_uint32_t  __adf_os_atomic_t;

/**
 * @brief This initiallizes the varriable to zero
 * 
 * @param __adf_os_atomic_t (int pointer)
 * 
 */
static inline void
__adf_os_atomic_init(__adf_os_atomic_t *v)
{
	//atomic_store_rel_int(v,0);
}
static inline a_uint32_t
__adf_os_atomic_read(__adf_os_atomic_t *v)
{
	//return (atomic_load_acq_int(v));
	return *v;
}

static inline void
__adf_os_atomic_inc(__adf_os_atomic_t *v)
{
	//atomic_add_int(v,1);
	(*v)++;
}

static inline void
__adf_os_atomic_dec(__adf_os_atomic_t *v)
{
	//atomic_subtract_int(v,1);
	(*v)--;
}
/*
static inline void
__adf_os_atomic_write(__adf_os_atomic_t *v,a_uint32_t p)
{
	atomic_store_rel_int(v,(int)p);
} 
 */

#endif
