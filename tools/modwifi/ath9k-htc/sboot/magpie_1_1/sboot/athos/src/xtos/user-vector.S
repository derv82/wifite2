// user-vector.S  -  User Vector for General Exceptions
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/user-vector.S#3 $

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
#include <xtensa/config/system.h>
#include "xtos-internal.h"

#if XCHAL_HAVE_EXCEPTIONS

	// Vector code
	.section		.UserExceptionVector.text, "ax"
	.align 4
	.global _UserExceptionVector
_UserExceptionVector:
# if ((XSHAL_USER_VECTOR_SIZE >= 28) && XCHAL_HAVE_ADDX) || (XSHAL_USER_VECTOR_SIZE >= 36) || XSHAL_VECTORS_PACKED
	//  There is space to dispatch right at the vector:

	addi	a1, a1, -ESF_TOTALSIZE	// allocate exception stack frame, etc.
	s32i	a2, a1, UEXC_a2
	s32i	a3, a1, UEXC_a3
	movi	a3, _xtos_exc_handler_table
	rsr	a2, EXCCAUSE		// get exception cause
	//interlock
	addx4	a3, a2, a3
	l32i	a3, a3, 0
	s32i	a4, a1, UEXC_a4
	jx	a3			// jump to cause-specific handler

	.size	_UserExceptionVector, . - _UserExceptionVector

# else
	//  The vector may be as small as 12 bytes:

	addi	a1, a1, -ESF_TOTALSIZE		// allocate exception stack frame, etc.
	s32i	a2, a1, UEXC_a2
	movi	a2, _UserExceptionFromVector	// load user exception handler address
	//interlock
	jx	a2				// jump to handler

	.size	_UserExceptionVector, . - _UserExceptionVector

	//  Dispatch outside vector:
	.text
	//.subsection 2
	.align	4
	.global	_UserExceptionFromVector
_UserExceptionFromVector:
	s32i	a3, a1, UEXC_a3
	movi	a3, _xtos_exc_handler_table
	rsr	a2, EXCCAUSE		// get exception cause
	s32i	a4, a1, UEXC_a4
	addx4	a3, a2, a3
	l32i	a3, a3, 0
	jx	a3			// jump to cause-specific handler

	.size	_UserExceptionFromVector, . - _UserExceptionFromVector

# endif /*XEA2*/


	.weak	_xtos_cause3_handler

	/*
	 *  Table of assembly-level general-exception handlers
	 *  (quickly entered) for user vectored exceptions.
	 *  Provides entries for all possible 64 exception causes
	 *  currently allowed for in the EXCCAUSE register.
	 *
	 *  NOTE:  entries that have a corresponding C handler
	 *  (registered at run-time) point to _xtos_c_wrapper_handler;
	 *  entries that have no handler point to _xtos_unhandled_exception.
	 */
	.data
	.global	_xtos_exc_handler_table
	.align 4
_xtos_exc_handler_table:
	.word	_xtos_unhandled_exception	// 0 IllegalInstruction
	.word	_xtos_syscall_handler		// 1 Syscall
	.word	_xtos_unhandled_exception	// 2 InstructionFetchError
	.word	_xtos_unhandled_exception	// 3 LoadStoreError
# if XCHAL_HAVE_INTERRUPTS
	.word	_xtos_l1int_handler		// 4 Level1Interrupt
# else
	.word	_xtos_unhandled_exception	// 4 Level1Interrupt (not configured)
# endif
	.word	_xtos_alloca_handler		// 5 Alloca (MOVSP)
	.word	_xtos_unhandled_exception	// 6 IntegerDivideByZero
	.word	_xtos_unhandled_exception	// 7 Speculation
	.word	_xtos_unhandled_exception	// 8 Privileged
	.word	_xtos_unhandled_exception	// 9 Unaligned
	.word	_xtos_unhandled_exception	//10 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//11 (reserved for Tensilica)
	.word	_xtos_cause3_handler		//12 PIF data error on fetch
	.word	_xtos_cause3_handler		//13 PIF data error on ld/st
	.word	_xtos_cause3_handler		//14 PIF address error on fetch
	.word	_xtos_cause3_handler		//15 PIF address error on ld/st
	.word	_xtos_unhandled_exception	//16 InstTLBMiss
	.word	_xtos_unhandled_exception	//17 InstTLBMultiHit
	.word	_xtos_unhandled_exception	//18 InstFetchPrivilege
	.word	_xtos_unhandled_exception	//19 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//20 InstFetchProhibited
	.word	_xtos_unhandled_exception	//21 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//22 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//23 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//24 LoadStoreTLBMiss
	.word	_xtos_unhandled_exception	//25 LoadStoreTLBMultiHit
	.word	_xtos_unhandled_exception	//26 LoadStorePrivilege
	.word	_xtos_unhandled_exception	//27 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//28 LoadProhibited
	.word	_xtos_unhandled_exception	//29 StoreProhibited
	.word	_xtos_unhandled_exception	//30 (reserved for Tensilica)
	.word	_xtos_unhandled_exception	//31 (reserved for Tensilica)
	.rept	8
	.word	_xtos_unhandled_exception	//32-39 Coprocessor<n>Disabled (n = 0..7)
	.endr

	.rept	XCHAL_EXCCAUSE_NUM-40
	.word	_xtos_unhandled_exception	//40-63 (reserved for TIE)
	.endr

	.text


	//  NOTES:
	//
	//  Here are alternative vectors.  They will NOT work with
	//  the handlers currently provided with XTOS.  However they
	//  might be useful to someone writing their own handlers
	//  from scratch.  Note that XSR is only available on T1040
	//  and later hardware.
	//
//***  The typical tiny 9-byte vector:  ***
//	wsr	a3, EXCSAVE_1			// save user a3
//	movi	a3, _UserExceptionFromVector	// load user exception handler address
//	jx	a3
//
//***  Minimizing EXCCAUSE-dispatch delay, not assuming valid SP:  ***
//	wsr	a0, DEPC	// save a0 (double exceptions fatal here, so not expected)
//	rsr	a0, EXCCAUSE
//	xsr	a1, EXCSAVE_1	// EXCSAVE_1 always contains &exception_handlers[0]
//	//interlock
//	addx4	a0, a0, a1
//	l32i	a0, a0, TABLE_OFS + EXC_CODE_KERNEL*4
//	xsr	a1, EXCSAVE_1	// restore a1 (DEPC contains original a0)
//	jx	a0		// jump to cause-specific handler
//
//***  Doing EXCCAUSE-dispatch with table in EXCSAVE_1:  ***
//	addi	a1, a1, -ESF_TOTALSIZE	// allocate exception stack frame, etc.
//	s32i	a2, a1, UEXC_a2
//	rsr	a2, EXCCAUSE
//	xsr	a4, EXCSAVE_1	// EXCSAVE_1 always contains &exception_handlers[0]
//	s32i	a3, a1, UEXC_a3
//	addx4	a2, a2, a4
//	l32i	a2, a2, TABLE_OFS + EXC_CODE_KERNEL*4
//	xsr	a4, EXCSAVE_1	// restore a1 (DEPC contains original a0)
//	jx	a2		// jump to cause-specific handler

#endif /* XCHAL_HAVE_EXCEPTIONS */

