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
 * @file adf_os_lock.h
 * This file abstracts locking operations.
 */

#ifndef _ADF_OS_LOCK_H
#define _ADF_OS_LOCK_H

#include <adf_os_types.h>
#include <adf_os_lock_pvt.h>

/**
 * @brief Platform spinlock object
 */
typedef __adf_os_spinlock_t        adf_os_spinlock_t;

/**
 * @brief Platform mutex object
 */
typedef __adf_os_mutex_t        adf_os_mutex_t;

/**
 * @brief Initialize a mutex
 *
 * @param[in] m mutex to initialize
 */
static inline void adf_os_init_mutex(adf_os_mutex_t *m)
{
    __adf_os_init_mutex(m);
}

/**
 * @brief Take the mutex
 *
 * @param[in] m mutex to take
 */
static inline int adf_os_mutex_acquire(adf_os_mutex_t *m)
{
    return (__adf_os_mutex_acquire(m));
}

/**
 * @brief Give the mutex
 *
 * @param[in] m mutex to give
 */
static inline void adf_os_mutex_release(adf_os_mutex_t *m)
{
    __adf_os_mutex_release(m);
}

/**
 * @brief Initialize a spinlock
 *
 * @param[in] lock spinlock object pointer
 */
static inline void
adf_os_spinlock_init(adf_os_spinlock_t *lock)
{
    __adf_os_spinlock_init(lock);
}


/**
 * @brief Acquire a spinlock by disabling the interrupts
 *
 * @param[in]  lock     spinlock object pointer
 * @param[out] flags    flags used to hold interrupt state
 */
static inline void
adf_os_spin_lock_irq(adf_os_spinlock_t *lock, a_uint32_t *flags)
{
    __adf_os_spin_lock_irq(lock,flags);
}


/**
 * @brief Release a spinlock & restore the irq
 *
 * @param[in] lock  spinlock object pointer
 * @param[in] flags flags filled in by @ref adf_os_spin_lock_irq
 */
static inline void
adf_os_spin_unlock_irq(adf_os_spinlock_t *lock, a_uint32_t *flags)
{
    __adf_os_spin_unlock_irq(lock,flags);
}


/**
 * @brief locks the spinlock mutex in soft irq context
 * 
 * @param[in] lock  spinlock object pointer
 */
static inline void
adf_os_spin_lock_bh(adf_os_spinlock_t   *lock)
{
    __adf_os_spin_lock_bh(lock);
}


/**
 * @brief unlocks the spinlock mutex in soft irq context
 * 
 * @param[in] lock  spinlock object pointer
 */
static inline void
adf_os_spin_unlock_bh(adf_os_spinlock_t *lock)
{
    __adf_os_spin_unlock_bh(lock);
}


/**
 * @brief Execute the input function with spinlock held and interrupt disabled.
 *
 * @param[in] hdl       OS handle
 * @param[in] lock      spinlock to be held for the critical region
 * @param[in] func      critical region function that to be executed
 * @param[in] context   context of the critical region function
 * 
 * @return Boolean status returned by the critical region function
 */
static inline a_bool_t
adf_os_spinlock_irq_exec(adf_os_handle_t           hdl,
                         adf_os_spinlock_t        *lock,
                         adf_os_irqlocked_func_t  func,
                         void                     *arg)
{
    return __adf_os_spinlock_irq_exec(hdl, lock, func, arg);
}

#endif
