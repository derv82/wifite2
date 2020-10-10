// exc-unhandled.S - General Exception Handler for unhandled exceptions

// Copyright (c) 2002-2004, 2006, 2010 Tensilica Inc.
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
#ifdef SIMULATOR
#include <xtensa/simcall.h>
#endif

#if XCHAL_HAVE_EXCEPTIONS

/*
 *  Assembly-level exception handler used when no handler was
 *  registered for the specific exception cause.
 *
 *  The BREAK instruction is used to give control to the debugger,
 *  if one is present and active.  (If none is present and active,
 *  the default debug exception handler will typically skip over
 *  this break instruction.)
 *  This code follows the convention documented in the ISA manual
 *  to use BREAK instructions to signal unhandled exceptions to the
 *  debugger.  For the debugger to report or handle this condition
 *  in an OS-independent manner, all processor state (except PC)
 *  must be restored as it was when the unhandled exception just
 *  occurred (ie. as it was at the beginning of the vector).
 *  If execution continues after the BREAK instruction (in which
 *  case any register might have been modified by the debugger),
 *  just return.
 */
	.text
	.align 4 

	// If not pulled-in some other way, define it as unhandled:
	.weak	_xtos_cause3_handler
	.global	_xtos_cause3_handler
_xtos_cause3_handler:

	.global _xtos_unhandled_exception
_xtos_unhandled_exception:
#if XCHAL_HAVE_DEBUG || defined(SIMULATOR)
	l32i	a2, a1, UEXC_a2		// restore a2
	l32i	a3, a1, UEXC_a3		// restore a3
	//  Note:  a4-a5 not clobbered, no need to restore.
	addi	a1, a1, ESF_TOTALSIZE	// restore sp
# if XCHAL_HAVE_DEBUG
	break	1, 1			// give control to the debugger (if any present)
# else
	wsr	a2, EXCSAVE1		// save a2 where simulator expects it
	movi	a2, SYS_unhandled_user_exc
	simcall				// let simulator/debugger report unhandled exception
	rsr	a2, EXCSAVE1		// restore a2
# endif
	rfe_rfue			// if sim/debug resume, just return
#else /* DEBUG or SIMULATOR */
	j	_xtos_unhandled_exception	// just loop forever
#endif /* DEBUG or SIMULATOR */

	.size	_xtos_unhandled_exception, . - _xtos_unhandled_exception


#endif /* XCHAL_HAVE_EXCEPTIONS */

