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
#ifndef __ATHOS_API_H__
#define __ATHOS_API_H__

/*
 * This file contains wrappers to OS operating system functions
 * that are available in the Athos version of the operating system.
 *
 * Target software must always use these wrappers to access OS
 * services -- it may not access any OS services directly.
 *
 * These wrappers are intended to provide OS-independence for applications.
 * Using this header file, an application should be able to compile and
 * fully link without any other OS header files, source files, or
 * binary files.
 */

#include <osapi.h>
#include "dt_defs.h"
#include "cmnos_api.h"
#include "Magpie_api.h"

/* ROM Patch API */

/* save the ROM printf function point */
extern int (* save_cmnos_printf)(const char * fmt, ...);

extern unsigned int _data_start_in_rom;
extern unsigned int _data_start;
extern unsigned int _data_end;
extern unsigned int _bss_start;
extern unsigned int _bss_end;
extern unsigned int _stack_sentry;
extern unsigned int __stack;
extern unsigned int _fw_image_end;

#if defined(__XTENSA__)
#define START_DATA      _data_start
#define END_DATA        _data_end
#define START_BSS       _bss_start
#define END_BSS         _bss_end

#define STACK_START  _stack_sentry
#define STACK_END    __stack
#endif

struct _A_os_linkage_check {
	int version;
	int table;
};

/* 
 * A_INIT() handles any initialization needed by the OS abstraction,
 * and it clears the application's BSS, if necessary.  (Application BSS
 * is not cleared if the application is linked into a single image that
 * includes AthOS.)
 *
 * A_INIT() must be called first thing in the application (from app_start)
 * in order to guarantee that BSS has been cleared properly.
 */
static INLINE int
A_INIT(void)
{
	struct _A_os_linkage_check link_check;
	unsigned int *clrptr;
    
	if (&START_BSS != _A_MAGPIE_INDIRECTION_TABLE->cmnos.start_bss) {
		/* Clear BSS */
		for (clrptr = &START_BSS; clrptr < &END_BSS; clrptr++) {
			*clrptr = 0;
		}
	}

	/* Copy writable data from flash to RAM.  */
	unsigned int *srcptr, *destptr;

	/*
	 * The _data_start symbol points to the start of data IN FLASH.
	 * It is defined by flash.ld at application link time.  If flash.ld
	 * is not used, it is defined (on the link line) as 0.
	 */
	static int *data_start_addr = &_data_start;

	if (data_start_addr != 0) {
		for (srcptr = &_data_start, destptr = &START_DATA;
		     destptr < &END_DATA;
		     srcptr++, destptr++) {
			*destptr = *srcptr;
		}
	}

#define OS_LINKAGE_VERSION 4
	link_check.version = OS_LINKAGE_VERSION;
	link_check.table = _A_MAGPIE_INDIRECTION_TABLE_SIZE;

	return A_CMN(hal_linkage_check(sizeof(link_check), &link_check));
}

#endif /* __ATHOS_API_H__ */

