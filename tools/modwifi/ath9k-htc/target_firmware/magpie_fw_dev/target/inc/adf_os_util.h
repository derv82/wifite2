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
 * @file adf_os_util.h
 * This file defines utility functions.
 */

#ifndef _ADF_OS_UTIL_H
#define _ADF_OS_UTIL_H

#include <adf_os_util_pvt.h>

/**
 * @brief Compiler-dependent macro denoting code likely to execute.
 */
#define adf_os_unlikely(_expr)     __adf_os_unlikely(_expr)

/**
 * @brief Compiler-dependent macro denoting code unlikely to execute.
 */
#define adf_os_likely(_expr)       __adf_os_likely(_expr)

/**
 * @brief read memory barrier. 
 */
#define adf_os_wmb()                __adf_os_wmb()

/**
 * @brief write memory barrier. 
 */
#define adf_os_rmb()                __adf_os_rmb()

/**
 * @brief read + write memory barrier. 
 */
#define adf_os_mb()                 __adf_os_mb()

/**
 * @brief return the lesser of a, b
 */ 
#define adf_os_min(_a, _b)          __adf_os_min(_a, _b)

/**
 * @brief return the larger of a, b
 */ 
#define adf_os_max(_a, _b)          __adf_os_max(_a, _b)

/**
 * @brief assert "expr" evaluates to true.
 */ 
#define adf_os_assert(expr)         __adf_os_assert(expr)

/**
 * @brief supply pseudo-random numbers
 */
static inline void adf_os_get_rand(adf_os_handle_t  hdl, 
                                   a_uint8_t       *ptr, 
                                   a_uint32_t       len)
{
    __adf_os_get_rand(hdl, ptr, len);
}

#endif /*_ADF_OS_UTIL_H*/
