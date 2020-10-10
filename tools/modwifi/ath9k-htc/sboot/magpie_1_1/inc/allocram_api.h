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
#ifndef __ALLOCRAM_API_H__
#define __ALLOCRAM_API_H__

/* API for Target-side startup-time RAM allocations */

struct allocram_api {
    /*
     * Initialize allocram, providing it with a block of RAM
     * (an "arena") from which to allocate.
     *
     * If arena_start is 0, a default start -- the end of
     * the application's text & data -- is used.
     *
     * If arena_sz is 0, a default size -- which uses most
     * of physical RAM beyond arena_start -- is used.
     *
     * Return value is reserved for future use -- it's an arena handle.
     */
    void *(* cmnos_allocram_init)(void *arena_start, A_UINT32 arena_sz);

    /*
     * Allocate nbytes of memory, returning a pointer to the start
     * of the allocated block.  Allocation size is rounded up to the
     * nearest A_CACHE_LINE_SIZE and the returned address similarly
     * aligned.
     *
     * There is no need to check the return value from this function.
     * A failure to satisfy a RAM allocation request is treated as a
     * fatal error.
     *
     * Allocations are expected to occur only during startup; this
     * API does not, for instance, guarantee atomicity with respect
     * to allocations that might (foolishly) be attempted from
     * interrupt handlers.
     *
     * The "which_arena" parameter is currently unused, and should
     * be set to 0 -- only a single arena is currently supported.
     */
    void *(* cmnos_allocram)(void *which_arena, A_UINT32 nbytes);
    
    void (* cmnos_allocram_debug)(void);
};

extern void allocram_module_install(struct allocram_api *api);


#endif /* __ALLOCRAM_API_H__ */
