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
 * @file adf_os_crypto.h
 * This file defines crypto APIs
 */

#ifndef __ADF_OS_CRYPTO_H
#define __ADF_OS_CRYPTO_H

#include <adf_os_crypto_pvt.h>

/**
 * @brief Representation of a cipher context.
 */ 
typedef __adf_os_cipher_t     adf_os_cipher_t;

/**
 * @brief Types of crypto algorithms
 */ 
typedef enum adf_os_crypto_alg{
    ADF_OS_CRYPTO_AES = __ADF_OS_CRYPTO_AES,
    ADF_OS_CRYPTO_OTHER = __ADF_OS_CRYPTO_OTHER,
}adf_os_crypto_alg_t;


/**
 * @brief allocate the cipher context
 * @param[in] type crypto algorithm
 * 
 * @return the new cipher context
 */
static inline adf_os_cipher_t
adf_os_crypto_alloc_cipher(adf_os_crypto_alg_t type)
{
    return __adf_os_crypto_alloc_cipher(type);
}

/**
 * @brief free the cipher context
 * 
 * @param[in] cipher cipher context
 */
static inline void
adf_os_crypto_free_cipher(adf_os_cipher_t cipher)
{
    __adf_os_crypto_free_cipher(cipher);
}

/**
 * @brief set the key for cipher context with length keylen
 * 
 * @param[in] cipher    cipher context
 * @param[in] key       key material
 * @param[in] keylen    length of key material
 * 
 * @return a_uint32_t
 */
static inline a_uint32_t
adf_os_crypto_cipher_setkey(adf_os_cipher_t cipher, const a_uint8_t *key, a_uint8_t keylen)
{
    return __adf_os_crypto_cipher_setkey(cipher, key, keylen);
}

/**
 * @brief encrypt the data with AES
 * 
 * @param[in]   cipher  cipher context
 * @param[in]   src     unencrypted data
 * @param[out]  dst     encrypted data
 */
static inline void
adf_os_crypto_rijndael_encrypt(adf_os_cipher_t cipher, const void *src, void *dst)
{
    __adf_os_crypto_rijndael_encrypt(cipher, src, dst);
}
#endif
