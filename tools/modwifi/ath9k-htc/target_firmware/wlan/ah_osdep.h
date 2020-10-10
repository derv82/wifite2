/*-
 * Copyright (c) 2002-2004 Sam Leffler, Errno Consulting, Atheros
 * Communications, Inc.  All rights reserved.
 *
 * Redistribution and use in source and binary forms are permitted
 * provided that the following conditions are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following NO
 *    ''WARRANTY'' disclaimer below (''Disclaimer''), without
 *    modification.
 * 2. Redistributions in binary form must reproduce at minimum a
 *    disclaimer similar to the Disclaimer below and any redistribution
 *    must be conditioned upon including a substantially similar
 *    Disclaimer requirement for further binary redistribution.
 * 3. Neither the names of the above-listed copyright holders nor the
 *    names of any contributors may be used to endorse or promote
 *    product derived from this software without specific prior written
 *    permission.
 *
 * NO WARRANTY
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF NONINFRINGEMENT,
 * MERCHANTIBILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE
 * FOR SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGES.
 *
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/wlan/target/hal/main/linux/ah_osdep.h#1 $
 */
#ifndef _ATH_AH_OSDEP_H_
#define _ATH_AH_OSDEP_H_
/*
 * Atheros Hardware Access Layer (HAL) OS Dependent Definitions.
 */

/*
 * Starting with 2.6.4 the kernel supports a configuration option
 * to pass parameters in registers.  If this is enabled we must
 * mark all function interfaces in+out of the HAL to pass parameters
 * on the stack as this is the convention used internally (for
 * maximum portability).
 *
 * XXX A lot of functions have __ahdecl in their definition but not declaration
 * So compile breaks.
 * Since This is only an issue for i386 which has regparam enabled, instead of
 * changing the vanilla FC3 kernel, for now, remove the regparm
 * disabling.
 */

#include <adf_os_types.h>
#include <adf_os_dma.h>
#include <adf_os_timer.h>
#include <adf_os_time.h>
#include <adf_os_lock.h>
#include <adf_os_io.h>
#include <adf_os_mem.h>
#include <adf_os_module.h>
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>

/* CONFIG_REGPARM has been removed from 2.6.20 onwards.
 * Since this is relevant only for i386 architectures, changing check to
 * i386.
 */

#ifdef __adf_i386__
#define __ahdecl    __attribute__((regparm(0)))
#else
#define __ahdecl
#endif
#ifndef adf_os_packed
#define adf_os_packed    __attribute__((__packed__))
#endif
#ifdef __FreeBSD__
/*
 * When building the HAL proper we use no GPL-contaminated include
 * files and must define these types ourself.  Beware of these being
 * mismatched against the contents of <linux/types.h>
 */
/* NB: arm defaults to unsigned so be explicit */
/* cometothis later when seperating os deps */
typedef __va_list va_list;
// typedef void *va_list;
#define	va_start(ap, last) \
	__builtin_stdarg_start((ap), (last))

#define	va_end(ap) \
	__builtin_va_end(ap)
#endif

/*
 * Linux/BSD gcc compatibility shims.
 */
#ifdef TODO //freebsd has definition
#define __printflike(_a,_b) \
    __attribute__ ((__format__ (__printf__, _a, _b)))
#endif
#ifndef __va_list
#define __va_list   va_list
#endif
#ifdef TODO //freebsd has definition
#define OS_INLINE   __inline
#endif

typedef void* HAL_SOFTC;
typedef a_int32_t HAL_BUS_TAG;
typedef void* HAL_BUS_HANDLE;
typedef a_uint32_t HAL_BUS_ADDR;         /* XXX architecture dependent */

/*
 * Delay n microseconds.
 */
extern  void __ahdecl ath_hal_delay(a_int32_t);
#define OS_DELAY(_n)    ath_hal_delay(_n)

extern  void* __ahdecl ath_hal_ioremap(a_uint32_t addr, a_uint32_t len);
#define OS_REMAP(_addr, _len)       ath_hal_ioremap(_addr, _len)

#define OS_MEMCPY(_d, _s, _n)   ath_hal_memcpy(_d,_s,_n)
extern void * __ahdecl ath_hal_memcpy(void *, const void *, size_t);

#ifndef abs
#define abs(_a)     __builtin_abs(_a)
#endif

struct ath_hal;
extern  a_uint32_t __ahdecl ath_hal_getuptime(struct ath_hal *);
#define OS_GETUPTIME(_ah)   ath_hal_getuptime(_ah)

#ifndef __bswap32
#define __bswap32(_x)	(_x)
#endif
#ifndef __bswap16
#define __bswap16(_x)	(_x)
#endif

#define AH_USE_EEPROM     0x00000001
extern  struct ath_hal *_ath_hal_attach_tgt( a_uint32_t, HAL_SOFTC, adf_os_device_t,
       a_uint32_t flags, void* status);
#endif /* _ATH_AH_OSDEP_H_ */
