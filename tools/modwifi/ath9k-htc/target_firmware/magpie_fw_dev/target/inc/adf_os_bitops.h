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
 * @file adf_os_bitops.h
 * This file abstracts bit-level operations on a stream of bytes.
 */

#ifndef _ADF_OS_BITOPS_H
#define _ADF_OS_BITOPS_H

#include <adf_os_types.h>

/**
 * @brief Set a bit atomically
 * @param[in] nr    Bit to change
 * @param[in] addr  Address to start counting from
 *
 * @note its atomic and cannot be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_set_bit_a(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_set_bit_a(nr, addr);
}

/**
 * @brief Set a bit
 * @param[in] nr    Bit to change
 * @param[in] addr  Address to start counting from
 *
 * @note its not atomic and can be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_set_bit(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_set_bit(nr, addr);
}

/**
 * @brief Clear a bit atomically
 * @param[in] nr    Bit to change
 * @param[in] addr  Address to start counting from
 *
 * @note its atomic and cannot be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_clear_bit_a(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_clear_bit_a(nr, addr);
}

/**
 * @brief Clear a bit
 * @param[in] nr    Bit to change
 * @param[in] addr  Address to start counting from
 *
 * @note its not atomic and can be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_clear_bit(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_clear_bit(nr, addr);
}

/**
 * @brief Toggle a bit atomically
 * @param[in] nr    Bit to change
 * @param[in] addr  Address to start counting from
 *
 * @note its atomic and cannot be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_change_bit_a(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_change_bit_a(nr, addr);
}

/**
 * @brief Toggle a bit
 * @param[in] nr    Bit to change
 * @param[in] addr  Address to start counting from
 *
 * @note its not atomic and can be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_change_bit(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_change_bit(nr, addr);
}

/**
 * @brief Test and Set a bit atomically
 * @param[in] nr    Bit to set
 * @param[in] addr  Address to start counting from
 *
 * @note its atomic and cannot be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_test_and_set_bit_a(a_uint32_t nr, 
                                          volatile a_uint32_t *addr)
{
    __adf_os_test_and_set_bit_a(nr, addr);
}

/**
 * @brief Test and Set a bit
 * @param[in] nr    Bit to set
 * @param[in] addr  Address to start counting from
 *
 * @note its not atomic and can be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_test_and_set_bit(a_uint32_t nr, 
                                          volatile a_uint32_t *addr)
{
    __adf_os_test_and_set_bit(nr, addr);
}

/**
 * @brief Test and clear a bit atomically
 * @param[in] nr    Bit to set
 * @param[in] addr  Address to start counting from
 *
 * @note its atomic and cannot be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_test_and_clear_bit_a(a_uint32_t nr, 
                                          volatile a_uint32_t *addr)
{
    __adf_os_test_and_clear_bit_a(nr, addr);
}

/**
 * @brief Test and clear a bit
 * @param[in] nr    Bit to set
 * @param[in] addr  Address to start counting from
 *
 * @note its not atomic and can be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_test_and_clear_bit(a_uint32_t nr, 
                                          volatile a_uint32_t *addr)
{
    __adf_os_test_and_clear_bit(nr, addr);
}

/**
 * @brief Test and change a bit atomically
 * @param[in] nr    Bit to set
 * @param[in] addr  Address to start counting from
 *
 * @note its atomic and cannot be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_test_and_change_bit_a(a_uint32_t nr, 
                                          volatile a_uint32_t *addr)
{
    __adf_os_test_and_change_bit_a(nr, addr);
}

/**
 * @brief Test and clear a bit
 * @param[in] nr    Bit to set
 * @param[in] addr  Address to start counting from
 *
 * @note its not atomic and can be re-ordered.
 * Note that nr may be almost arbitrarily large; this function is not
 * restricted to acting on a single-word quantity.
 */
static inline void adf_os_test_and_change_bit(a_uint32_t nr, 
                                          volatile a_uint32_t *addr)
{
    __adf_os_test_and_change_bit(nr, addr);
}

/**
 * @brief test_bit - Determine whether a bit is set
 * @param[in] nr    bit number to test
 * @param[in] addr  Address to start counting from
 *
 * @return 1 if set, 0 if not
 */
static inline int adf_os_test_bit(a_uint32_t nr, volatile a_uint32_t *addr)
{
    __adf_os_test_bit(nr, addr);
}


#endif /**_AOD_BITOPS_H*/
