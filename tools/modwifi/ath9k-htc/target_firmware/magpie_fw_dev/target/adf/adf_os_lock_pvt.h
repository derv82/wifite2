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
#ifndef _ADF_OS_LOCK_PVT_H
#define _ADF_OS_LOCK_PVT_H

typedef int  		__adf_os_spinlock_t;
typedef int  		__adf_os_mutex_t;

static inline void __adf_os_init_mutex(__adf_os_mutex_t *mtx)
{
	
}

static inline int __adf_os_mutex_acquire(__adf_os_mutex_t *mtx)
{
	return 0;
}
static inline void __adf_os_mutex_release(__adf_os_mutex_t *mtx)
{

}
static inline void __adf_os_spinlock_init(__adf_os_spinlock_t *lock)
{

}
/*
 * Synchronous versions - only for OS' that have interrupt disable
 */
static inline void   __adf_os_spin_lock_irq(__adf_os_spinlock_t *lock, a_uint32_t    *flags)
{
    //mtx_lock_spin(lock);
    (*flags)=0;
}

static inline void   __adf_os_spin_unlock_irq(__adf_os_spinlock_t *lock, a_uint32_t    *flags)
{
    //mtx_unlock_spin(lock);
}

static inline void		__adf_os_spin_lock_bh(__adf_os_spinlock_t	*lock)
{
	//mtx_lock_spin(lock);
}
static inline void		__adf_os_spin_unlock_bh(__adf_os_spinlock_t	*lock)
{
	//mtx_unlock_spin(lock);
}
static inline a_bool_t __adf_os_spinlock_irq_exec(adf_os_handle_t  hdl, __adf_os_spinlock_t *lock, 
                                                  adf_os_irqlocked_func_t func, void *arg)
{
    return 0;
}
#endif
