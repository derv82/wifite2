// exc-return.S - Shared exception/interrupt return code

// Copyright (c) 2002-2004, 2006-2007, 2010 Tensilica Inc.
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
#include <xtensa/corebits.h>
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"

#if XCHAL_HAVE_EXCEPTIONS

	.text
	.align	4
	.global	_xtos_return_from_exc
_xtos_return_from_exc:

#ifdef __XTENSA_CALL0_ABI__

	l32i	a0, a1, UEXC_a0		// restore general registers, pc, ps
	l32i	a4, a1, UEXC_a4
	l32i	a5, a1, UEXC_a5
	l32i	a6, a1, UEXC_a6
	l32i	a7, a1, UEXC_a7
	l32i	a8, a1, UEXC_a8
	l32i	a9, a1, UEXC_a9
	l32i	a10, a1, UEXC_a10
	l32i	a11, a1, UEXC_a11
	l32i	a12, a1, UEXC_a12
	l32i	a13, a1, UEXC_a13
	l32i	a14, a1, UEXC_a14
	l32i	a15, a1, UEXC_a15

	l32i	a2, a1, UEXC_pc
	l32i	a3, a1, UEXC_ps
	wsr	a2, EPC_1
	wsr	a3, PS

	l32i	a2, a1, UEXC_a2
	l32i	a3, a1, UEXC_a3
	
	rsync				// wait for WSR to PS to complete

	addi	a1, a1, ESF_TOTALSIZE	// restore sp

	rfe

#else /* ! __XTENSA_CALL0_ABI__ */
	
	
	//  Here we rotated back by N registers, to the interrupted code's register window.
	//  NOTA: a2 and a3 might contain something useful, but we haven't determined
	//  what that might be yet (for now, a2 contains nested-C-func call-chain ptr).

	//  NOTE:  a5 still contains the exception window's exception stack frame pointer.

# if XTOS_CNEST
	s32i	a2, a5, ESF_TOTALSIZE-20	// restore nested-C-func call-chain ptr
# endif
	l32i	a2, a5, UEXC_ps
	l32i	a3, a5, UEXC_pc
	wsr	a2, PS		// for XEA2, this sets EXCM; for XEA1, this sets INTLEVEL to 1; ...

# if XCHAL_HAVE_XEA1 && XCHAL_HAVE_INTERRUPTS
	l32i	a4, a5, UEXC_sar	// load INTENABLE value that restores original vpri
	l32i	a2, a5, UEXC_a2
	rsync				// wait for WSR to PS to complete
	wsr	a4, INTENABLE		// update INTENABLE to restore original vpri (PS.INTLEVEL=1 here)
	l32i	a4, a5, UEXC_a4
# else
	l32i	a2, a5, UEXC_a2
	l32i	a4, a5, UEXC_a4
	rsync				// wait for WSR to PS to complete
# endif

	/* FIXME: Enabling this here may break task-engine builds
	 * because task engines have exceptions (sort of), but they do
	 * not have the EPC_1 special register.  XCHAL_HAVE_INTERRUPTS
	 * is incorrect for normal configs without interrupts but with
	 * exceptions (we still need to restore EPC_1).  The correct
	 * solution is to define XCHAL_HAVE_EXCEPTIONS more strictly
	 * to mean something like "Have exceptions with
	 * user/kernel/double vectors" so that task engines are
	 * excluded. This would be a change to
	 * <xtensa/config/core.h>.  */

	wsr	a3, EPC_1
	//  HERE:
	//	- we cannot get window overflows anymore -- we're NOT in a valid windowed context
	//	- low-priority interrupts are still disabled

	//  NOTE:  we don't restore EXCCAUSE or EXCVADDR, not needed.

	//  Restore a3, a5:
	l32i	a3, a5, UEXC_a3
	l32i	a5, a5, UEXC_a5

	rfe_rfue

#endif /* __XTENSA_CALL0_ABI__ */

	.size	_xtos_return_from_exc, . - _xtos_return_from_exc

#endif /* XCHAL_HAVE_EXCEPTIONS */

