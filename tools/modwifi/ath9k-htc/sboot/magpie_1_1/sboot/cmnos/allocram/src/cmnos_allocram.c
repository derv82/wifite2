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
#include "sys_cfg.h"
#include "athos_api.h"

#if SYSTEM_MODULE_ALLOCRAM

/*
 * Startup time RAM allocation.
 *
 * Oddly enough, we allow allocation, but not free.
 * The central idea is to restrict compile-time RAM demands
 * of modules to a minimum so that if a module is replaced
 * at run-time large amounts of RAM are not wasted.
 *
 * Addresses returned are A_CACHE_LINE_SIZE aligned.
 */

LOCAL A_UINT32 allocram_current_addr;
LOCAL A_UINT32 allocram_remaining_bytes;

LOCAL void *
cmnos_allocram_init(void *arena_start, A_UINT32 arena_sz)
{
    A_UINT32 astart = (A_UINT32)arena_start;

#if defined(__XTENSA__)
    /*
     * This hacky line converts from a text or data RAM address
     * into a data RAM address.  (It's all the same on MIPS, but
     * text and data are different address spaces on Xtensa.)
     */
    //astart = TARG_RAM_ADDRS(TARG_RAM_OFFSET(astart));
#endif

#if 0
    if (arena_sz == 0) {
        /* Default arena_sz to most of available RAM */
        arena_sz = TARG_RAM_SZ - (A_UINT32)TARG_RAM_OFFSET(astart);
        arena_sz -= HOST_INTEREST->hi_end_RAM_reserve_sz;
    }
#endif

    /* Clear entire area */
//    A_MEMSET(astart, 0, arena_sz);

    /* Adjust for cache line alignment */
#if 0    
    allocram_current_addr = A_ROUND_UP(astart, A_CACHE_LINE_SIZE);
    arena_sz -= (allocram_current_addr-astart);
#else
    allocram_current_addr = astart;
#endif    
    allocram_remaining_bytes = arena_sz;

    //A_DCACHE_FLUSH();

    //A_PRINTF("cmnos_allocram_init: start=0x%x size=%d\n",
    //    allocram_current_addr, allocram_remaining_bytes);

    return NULL; /* Future implementation may return an arena handle */
}

/*
 * Allocate nbytes from the arena.  At this point, which_arena should
 * be set to 0 for the default (and only) arena.  A future allocation
 * module may support multiple separate arenas.
 */
LOCAL void *
cmnos_allocram(void * which_arena, A_UINT32 nbytes)
{
    void *ptr = (void *)allocram_current_addr;
    //nbytes = A_ROUND_UP(nbytes, A_CACHE_LINE_SIZE);
    nbytes = A_ROUND_UP(nbytes, 4);
    if (nbytes <= allocram_remaining_bytes) {
        allocram_remaining_bytes -= nbytes;
        allocram_current_addr += nbytes;
    } else {
        A_PRINTF("RAM allocation (%d bytes) failed!\n", nbytes);
        //A_ASSERT(0);
        adf_os_assert(0);
    }

    return ptr;
}

void
cmnos_allocram_debug(void)
{
    A_PRINTF("ALLOCRAM Current Addr 0x%x\n", allocram_current_addr);
    A_PRINTF("ALLOCRAM Remaining Bytes %d\n", allocram_remaining_bytes);
}

void
cmnos_allocram_module_install(struct allocram_api *tbl)
{
    tbl->cmnos_allocram_init                 = cmnos_allocram_init;
    tbl->cmnos_allocram                      = cmnos_allocram;
    tbl->cmnos_allocram_debug                = cmnos_allocram_debug;
}

#endif /* SYSTEM_MODULE_ALLOCRAM */

