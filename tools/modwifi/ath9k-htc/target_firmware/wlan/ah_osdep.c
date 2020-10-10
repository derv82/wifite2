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

#include <stdarg.h>
#include <adf_os_types.h>
#include <adf_os_dma.h>
#include <adf_os_timer.h>
#include <adf_os_lock.h>
#include <adf_os_io.h>
#include <adf_os_mem.h>
#include <adf_os_module.h>
#include <adf_os_pci.h>
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>

#include "ah.h"
#include<ah_internal.h>
#include "ah_osdep.h"

a_uint32_t __ahdecl
ath_hal_getuptime(struct ath_hal *ah)
{
	return adf_os_getuptime();
}

struct ath_hal *
_ath_hal_attach_tgt(a_uint32_t devid, HAL_SOFTC sc,
		    adf_os_device_t dev, a_uint32_t flags, void* s)
{
	HAL_STATUS status;
	struct ath_hal *ah = ath_hal_attach_tgt(devid, sc, dev, flags, &status);
	adf_os_print(" ath_hal = %p \n",ah);
	*(HAL_STATUS *)s = status;
	return ah;
}

extern void *global_hdl;

/*
 * Delay n microseconds.
 */
void __ahdecl
ath_hal_delay(a_int32_t n)
{
	adf_os_udelay(n);
}

/*
 * Allocate/free memory.
 */
void * __ahdecl
ath_hal_malloc(adf_os_size_t size)
{
	void *p;

	p = adf_os_mem_alloc(size);
	if (p)
		adf_os_mem_zero(p, size);

	return p;
}

void __ahdecl
ath_hal_free(void* p)
{
	adf_os_mem_free(p);
}

void * __ahdecl
ath_hal_memcpy(void *dst, const void *src, adf_os_size_t n)
{
	adf_os_mem_copy(dst, src, n);
	return 0;
}

enum {
	DEV_ATH     = 9,            /* XXX must match driver */
};

adf_os_module_dep(hal, adf_net);
adf_os_module_dep(hal, hal);
