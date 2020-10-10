// user-vector-min.S  -  Minimal User Vector for General Exceptions
//	Takes less table space, but does not allow registering new handlers.
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/user-vector-min.S#3 $

// Copyright (c) 2003-2004, 2006-2007, 2010 Tensilica Inc.
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
#include <xtensa/config/system.h>
#include "xtos-internal.h"

#if XCHAL_HAVE_EXCEPTIONS

	//  Vector code
	.begin	literal_prefix	.UserExceptionVector
	.section		.UserExceptionVector.text, "ax"
	.align 4
	.global _UserExceptionVector
_UserExceptionVector:
# if ((XSHAL_USER_VECTOR_SIZE >= 28) && XCHAL_HAVE_DENSITY) || XSHAL_VECTORS_PACKED

	addi	a1, a1, -ESF_TOTALSIZE	// allocate exception stack frame, etc.
	s32i	a2, a1, UEXC_a2
	s32i	a3, a1, UEXC_a3
	rsr	a2, EXCCAUSE		// get exception cause
	movi	a3, _xtos_min_handler_table
	bgeui	a2, 6, 1f		// causes 6 and above map to zero
	addx4	a3, a2, a3		// index by cause if 1 .. 5
1:	l32i	a3, a3, 0
	s32i	a4, a1, UEXC_a4
	jx	a3			// jump to cause-specific handler

	.size	_UserExceptionVector, . - _UserExceptionVector
	.end	literal_prefix

# else /*vector as small as 12 bytes:*/

	addi	a1, a1, -ESF_TOTALSIZE		// allocate exception stack frame, etc.
	s32i	a2, a1, UEXC_a2
	movi	a2, _UserExceptionFromVector	// load user exception handler address
	//interlock
	jx	a2				// jump to handler

	.size	_UserExceptionVector, . - _UserExceptionVector
	.end	literal_prefix

	//  Dispatch outside vector:
	.text
	.align	4
	.global	_UserExceptionFromVector
_UserExceptionFromVector:
	rsr	a2, EXCCAUSE		// get exception cause
	s32i	a3, a1, UEXC_a3
	movi	a3, _xtos_min_handler_table
	bgeui	a2, 6, 1f		// causes 6 and above map to zero
	addx4	a3, a2, a3		// index by cause if 1 .. 5
1:	l32i	a3, a3, 0
	s32i	a4, a1, UEXC_a4
	jx	a3			// jump to cause-specific handler
	.size	_UserExceptionFromVector, . - _UserExceptionFromVector

# endif /*XEA2*/


	/*
	 *  Read-only minimal table of assembly-level exception handlers
	 *  for user vectored exceptions.
	 *  Only provides entries for SYSCALL, MOVSP, and level-1 interrupt causes.
	 */
	.section .rodata, "a"
	.global	_xtos_min_handler_table
	.align 4
_xtos_min_handler_table:
	.word	_xtos_unhandled_exception	// 0 Illegal Instruction, and causes > 5
	.word	_xtos_syscall_handler		// 1 SYSCALL Instruction
	.word	_xtos_unhandled_exception	// 2 Instruction Fetch Error
	.word	_xtos_unhandled_exception	// 3 Load/Store Error
# if XCHAL_HAVE_INTERRUPTS
	.word	_xtos_l1int_handler		// 4 Level-1 Interrupt
# else
	.word	_xtos_unhandled_exception	// 4 Level-1 Interrupt (not configured)
# endif
	.word	_xtos_alloca_handler		// 5 Alloca (MOVSP Instruction)
	.text

#endif /* XCHAL_HAVE_EXCEPTIONS */

