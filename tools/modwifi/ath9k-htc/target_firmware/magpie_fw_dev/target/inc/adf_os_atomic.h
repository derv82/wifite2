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
 * @file adf_os_atomic.h
 * This file abstracts an atomic counter.
 */
 
#ifndef _ADF_OS_ATOMIC_H
#define _ADF_OS_ATOMIC_H

#include <adf_os_atomic_pvt.h>
/**
 * @brief Atomic type of variable.
 * Use this when you want a simple resource counter etc. which is atomic
 * across multiple CPU's. These maybe slower than usual counters on some
 * platforms/OS'es, so use them with caution.
 */
typedef __adf_os_atomic_t    adf_os_atomic_t;

/** 
 * @brief Initialize an atomic type variable
 * @param[in] v a pointer to an opaque atomic variable
 */
static inline void
adf_os_atomic_init(adf_os_atomic_t *v)
{
    __adf_os_atomic_init(v);
}

/**
 * @brief Read the value of an atomic variable.
 * @param[in] v a pointer to an opaque atomic variable
 *
 * @return the current value of the variable
 */
static inline a_uint32_t
adf_os_atomic_read(adf_os_atomic_t *v)
{
    return (__adf_os_atomic_read(v));
}

/**
 * @brief Increment the value of an atomic variable.
 * @param[in] v a pointer to an opaque atomic variable
 */
static inline void
adf_os_atomic_inc(adf_os_atomic_t *v)
{
    return (__adf_os_atomic_inc(v));
}

/**
 * @brief Decrement the value of an atomic variable.
 * @param v a pointer to an opaque atomic variable
 */
static inline void
adf_os_atomic_dec(adf_os_atomic_t *v)
{
    return (__adf_os_atomic_dec(v));
}

#endif
