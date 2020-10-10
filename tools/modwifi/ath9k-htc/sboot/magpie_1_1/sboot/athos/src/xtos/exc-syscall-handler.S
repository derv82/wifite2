/* exc-syscall-handler.S - XTOS syscall instruction handler */

/*
 * Copyright (c) 1999-2010 Tensilica Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

/*
 * The SYSCALL instruction is typically used to implement system calls.
 * By convention, register a2 identifies the requested system call.
 * Typically, other parameters are passed in registers a3 and up,
 * and results are returned in a2.
 *
 * The Xtensa windowed ABI reserves the value zero of register a2
 * as a request to force register windows to the stack.  The call0 ABI,
 * which has no equivalent operation, reserves this value as a no-op.
 *
 * Generally, only code that traverses the stack in unusual ways needs
 * to force (spill) register windows to the stack.  In generic C or C++,
 * there are four cases, and they all use the standard SYSCALL mechanism:
 *
 * 1. C++ exceptions
 * 2. setjmp and longjmp
 * 3. functions using the GNU extension "__builtin_return_address"
 * 4. functions using the GNU extension "nonlocal goto"
 *
 * NOTE:  Specific operating systems often need to spill register windows
 * to the stack in other situations such as context-switching, passing
 * Unix-like signals to threads, displaying stack tracebacks, etc.
 * They may choose to use the SYSCALL mechanism to do so, or use other
 * means such as calling xthal_window_spill() or other methods.
 *
 * If you want to handle other system calls, you can modify this file, or
 * use the C version of it in exc-syscall-handler.c .  The Xtensa ABIs only
 * define system call zero; the behavior of other system calls is up to you.
 */

#include <xtensa/coreasm.h>
#include "xtos-internal.h"


#if XCHAL_HAVE_EXCEPTIONS

//Vector:
//	addi	a1, a1, -ESF_TOTALSIZE	// allocate exception stack frame, etc.
//	s32i	a2, a1, UEXC_a2
//	s32i	a3, a1, UEXC_a3
//	movi	a3, _xtos_exc_handler_table
//	rsr	a2, EXCCAUSE
//	addx4	a2, a2, a3
//	l32i	a2, a2, 0
//	s32i	a4, a1, UEXC_a4
//	jx	a2		// jump to cause-specific handler

	.global	_need_user_vector_	// pull-in real user vector (tiny LSP)


	/*
	 *  The SYSCALL handler is entered when the processor
	 *  executes the SYSCALL instruction.
	 *  By convention, the system call to execute is specified in a2.
	 */
	.text
	.align	4
	.global	_xtos_syscall_handler
_xtos_syscall_handler:
	//  HERE:  a2, a3, a4 have been saved to the exception stack frame allocated with a1 (sp).
	//  We ignore that a4 was saved, we don't clobber it.

	rsr	a3, EPC_1
#if XCHAL_HAVE_LOOPS
	// If the SYSCALL instruction was the last instruction in the body of
	// a zero-overhead loop, and the loop will execute again, decrement
	// the loop count and resume execution at the head of the loop:
	//
	rsr	a2, LEND
	addi	a3, a3, 3	// increment EPC to skip the SYSCALL instruction
	bne	a2, a3, 1f
	rsr	a2, LCOUNT
	beqz	a2, 1f
	addi	a2, a2, -1
	wsr	a2, LCOUNT
	rsr	a3, LBEG
1:	l32i	a2, a1, UEXC_a2	// get the system call number
#else
	//  No loop registers.
	l32i	a2, a1, UEXC_a2	// get the system call number
	addi	a3, a3, 3	// increment EPC to skip the SYSCALL instruction
#endif
	wsr	a3, EPC_1	// update EPC1 past SYSCALL
	l32i	a3, a1, UEXC_a3	// restore a3
	//  If you want to handle other system calls, check a2 here.

#ifdef __XTENSA_WINDOWED_ABI__
	bnez	a2, .Lnotzero	// is syscall number zero?

	/*  Spill register windows to the stack.  */

	// Save a2 thru a5 in the nested-C-function area, where an interrupt
	// won't clobber them.  The pseudo-CALL's ENTRY below clobbers a4 and a5.
	//s32i	a2, a1, (ESF_TOTALSIZE - 32) + 0	// a2 is zero, no need to save
	s32i	a3, a1, (ESF_TOTALSIZE - 32) + 4
	s32i	a4, a1, (ESF_TOTALSIZE - 32) + 8
	s32i	a5, a1, (ESF_TOTALSIZE - 32) + 12

	movi	a3, PS_WOE|PS_CALLINC(1)|PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)  // CALL4 emulation
	rsr	a2, PS			// save PS in a2
	wsr	a3, PS			// PS.INTLEVEL=EXCMLEVEL (1 for XEA1)
	//  HERE:  window overflows enabled but NOT SAFE yet, touch only a0..a3 until it's safe.
	rsr	a3, EPC_1		// save EPC1 in a3
	addi	a1, a1, ESF_TOTALSIZE	// restore sp (dealloc ESF) for sane stack again
	rsync				// wait for WSR to PS to complete
	//  HERE:  Window overflows and interrupts are safe, we saved EPC1 and
	//  restored a1, and a4-a15 are unmodified.
	//  Pseudo-CALL:  make it look as if the code that executed SYSCALL
	//  made a CALL4 to here.  See user exc. handler comments for details.
	//  ENTRY cannot cause window overflow; touch a4 to ensure a4-a7
	//  overflow if needed:
	movi	a4, 0			// clears pseudo-CALL's return PC
	//  NOTE:  On XEA1 processors, return from window overflow re-enables
	//  interrupts (by clearing PS.INTLEVEL).  This is okay even though SP
	//  is unallocated because we saved state safe from interrupt dispatch.
	.global	_SyscallException
_SyscallException:			// label makes tracebacks look nicer
	_entry	a1, 64			// as if after a CALL4 (PS.CALLINC==1)
	//  Call deep enough to force spill of entire address register file.
	_call12	.Ldeep
1:	movi	a14, 0x80000000 + .Ldelta_done
	add	a0, a12, a14		// clear a0 msbit (per CALL4), offset
3:	retw				// return from pseudo-CALL4

	//  NOTE:  a5 still contains the exception window's exception stack frame pointer.
.LMdon:	wsr	a2, PS		// for XEA2, this sets EXCM; for XEA1, this sets INTLEVEL to 1; ...
	movi	a2, 0		// indicate successful SYSCALL (?)
	l32i	a4, a5, 32 + 8
	rsync			// complete WSR to PS for safe write to EPC1
	wsr	a3, EPC_1
	l32i	a3, a5, 32 + 4
	l32i	a5, a5, 32 + 12
	rfe_rfue

	.set	.Ldelta_retw, (3b - 1b)
	.set	.Ldelta_done, (.LMdon - 1b)

	.align	4
.Ldeep:	entry	a1, 48
#if XCHAL_NUM_AREGS < 64
	mov	a15, a15		// touch just far enough to overflow 32
#else
	movi	a12, .Ldelta_retw	// use movi/add because of relocation
	add	a12, a0, a12		// set return PC as per CALL12
	_entry	a1, 48			// last call was call12 so PS.CALLINC==3
	mov	a12, a0			// set return PC
	_entry	a1, 48
	mov	a12, a0			// set return PC
	_entry	a1, 16
	mov	a11, a11		// touch just far enough to overflow 64
#endif
	retw

#endif /* __XTENSA_WINDOWED_ABI__ */

.Lnotzero:
	movi	a2, -1 /*ENOSYS*/	// system call not supported
	addi	a1, a1, ESF_TOTALSIZE
	rfe_rfue

	.size	_xtos_syscall_handler, . - _xtos_syscall_handler


#endif /* XCHAL_HAVE_EXCEPTIONS */

