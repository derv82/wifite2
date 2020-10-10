// exit.S
//
// For hardware / boards, this is the default _exit routine called by the
// C library exit() function.  If the program ever exits, we eventually
// end up here after all C library cleanup (such as closing open files,
// calling exit callbacks and C++ destructors, etc) is complete.

// Copyright (c) 1998-2010 Tensilica Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining
// a copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to
// permit persons to whom the Software is furnished to do so, subject to
// the following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
// IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
// CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
// TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
// SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#include <xtensa/coreasm.h>
#include <xtensa/config/core-isa.h>
#include "xtos-internal.h"

// Macros to abstract away ABI differences
#if __XTENSA_CALL0_ABI__
# define CALL	call0
#else
# define CALL	call4
#endif


	.text
	.align 4
	.global _exit
	.type	_exit, @function
_exit:
	abi_entry 0, 4

	// sync dirty data to memory before terminating
#if XCHAL_DCACHE_IS_COHERENT
	CALL	xthal_cache_coherence_optout
#elif XCHAL_DCACHE_IS_WRITEBACK
	CALL	xthal_dcache_all_writeback
#endif

	// sync queues (if any, only for LX and later):
#if XCHAL_HW_MIN_VERSION >= XTENSA_HWVERSION_RA_2004_1	/* LX or later? */
	extw
#endif
	// can break to debug monitor, go to sleep with waiti, or just spin in a loop
.L0:
#if XCHAL_HAVE_DEBUG
	break	0, 0		// back to debugger, if one is attached
#elif XCHAL_HAVE_INTERRUPTS
	waiti	15
#elif XCHAL_HAVE_HALT
	halt
#endif
	j	.L0
	//abi_exit

	.size	_exit, . - _exit

