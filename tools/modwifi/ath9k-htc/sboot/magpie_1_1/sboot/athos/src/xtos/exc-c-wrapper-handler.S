// exc-c-wrapper-handler.S - General Exception Handler that Dispatches C Handlers

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
#ifdef SIMULATOR
#include <xtensa/simcall.h>
#endif

#if XCHAL_HAVE_EXCEPTIONS


/*
 *  This assembly-level handler causes the associated exception (usually causes 12-15)
 *  to be handled as if it were exception cause 3 (load/store error exception).
 *  This provides forward-compatibility with a possible future split of the
 *  load/store error cause into multiple more specific causes.
 */
	.align	4
	.global	_xtos_cause3_handler
_xtos_cause3_handler:
	movi	a2, EXCCAUSE_LOAD_STORE_ERROR
	j	_xtos_c_wrapper_handler
	.size	_xtos_cause3_handler, . - _xtos_cause3_handler



/*
 *  This is the general exception assembly-level handler that dispatches C handlers.
 */
	.align	4
	.global	_xtos_c_wrapper_handler
_xtos_c_wrapper_handler:

	//  HERE:  a2, a3, a4 have been saved to exception stack frame allocated with a1 (sp).
	//  a2 contains EXCCAUSE.
	s32i	a5, a1, UEXC_a5		// a5 will get clobbered by ENTRY after the pseudo-CALL4
					//   (a4..a15 spilled as needed; save if modified)

	//NOTA:  Possible future improvement:
	//	keep interrupts disabled until we get into the handler, such that
	//	we don't have to save other critical state such as EXCVADDR here.
	//rsr	a3, EXCVADDR
	s32i	a2, a1, UEXC_exccause
	//s32i	a3, a1, UEXC_excvaddr

#if XCHAL_HAVE_XEA1
# if XCHAL_HAVE_INTERRUPTS
	rsilft	a3, 1, XTOS_LOCKLEVEL	// lockout
	rsr	a2, INTENABLE
	//movi	a3, ~XCHAL_EXCM_MASK
	movi	a3, ~XTOS_LOCKOUT_MASK	// mask out low and medium priority levels, and high priority levels covered by
					//  XTOS_LOCKLEVEL if any, so we can run at PS.INTLEVEL=0 while manipulating INTENABLE
	s32i	a2, a1, UEXC_sar	// (temporary holding place for INTENABLE value to restore after pseudo-CALL4 below)
	and	a3, a2, a3		// mask out selected interrupts
	wsr	a3, INTENABLE		// disable all interrupts up to and including XTOS_LOCKLEVEL
# endif
	movi	a3, PS_WOE|PS_CALLINC(1)|PS_UM	// WOE=1, UM=1, INTLEVEL=0, CALLINC=1 (call4 emul), OWB=(dontcare)=0

	//  NOTE:  could use XSR here if targeting T1040 or T1050 hardware (requiring slight sequence adjustment as for XEA2):
	rsr	a2, PS
	rsync	//NOT-ISA-DEFINED	// wait for WSR to INTENABLE to complete before clearing PS.INTLEVEL
	wsr	a3, PS			// PS.INTLEVEL=0, effective INTLEVEL (via INTENABLE) is XTOS_LOCKLEVEL

	//  HERE:  window overflows enabled, but NOT SAFE because we're not quite
	//	in a valid windowed context (haven't restored a1 yet...);
	//	so don't cause any (keep to a0..a3) until we've saved critical state and restored a1:

	//  NOTE:  MUST SAVE EPC1 before causing any overflows, because overflows corrupt EPC1.
	rsr	a3, EPC_1
	s32i	a2, a1, UEXC_ps
	s32i	a3, a1, UEXC_pc

#else /* !XEA1 */

	//  Set PS fields:
	//	EXCM     = 0
	//	WOE      = __XTENSA_CALL0_ABI__ ? 0 : 1
	//	UM       = 1
	//	INTLEVEL = EXCM_LEVEL = 1
	//	CALLINC  = __XTENSA_CALL0_ABI__ ? 0 : 1
	//	OWB      = 0 (really, a dont care if !__XTENSA_CALL0_ABI__)

#  ifdef __XTENSA_CALL0_ABI__
	movi	a2, PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)
#  else
	movi	a2, PS_WOE|PS_CALLINC(1)|PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)  // CALL4 emulation
#  endif
	rsr	a3, EPC_1
	xsr	a2, PS

	//  HERE:  window overflows enabled, but NOT SAFE because we're not quite
	//	in a valid windowed context (haven't restored a1 yet...);
	//	so don't cause any (keep to a0..a3) until we've saved critical state and restored a1:

	//  NOTE:  MUST SAVE EPC1 before causing any overflows, because overflows corrupt EPC1.
	s32i	a3, a1, UEXC_pc
	s32i	a2, a1, UEXC_ps
#endif

#ifdef __XTENSA_CALL0_ABI__

	s32i	a0, a1, UEXC_a0		// save the rest of the registers
	s32i	a6, a1, UEXC_a6
	s32i	a7, a1, UEXC_a7
	s32i	a8, a1, UEXC_a8
	s32i	a9, a1, UEXC_a9
	s32i	a10, a1, UEXC_a10
	s32i	a11, a1, UEXC_a11
	s32i	a12, a1, UEXC_a12
	s32i	a13, a1, UEXC_a13
	s32i	a14, a1, UEXC_a14
	s32i	a15, a1, UEXC_a15
#  if XTOS_DEBUG_PC
	// TODO: setup return PC for call traceback through interrupt dispatch
#  endif

	rsync				// wait for WSR to PS to complete

#else  /* ! __XTENSA_CALL0_ABI__ */

# if XTOS_CNEST
	l32i	a2, a1, ESF_TOTALSIZE-20	// save nested-C-func call-chain ptr
# endif
	addi	a1, a1, ESF_TOTALSIZE	// restore sp (dealloc ESF) for sane stack again
	rsync				// wait for WSR to PS to complete

	/*  HERE:  we can SAFELY get window overflows.
	 *
	 *  From here, registers a4..a15 automatically get spilled if needed.
	 *  They become a0..a11 after the ENTRY instruction.
	 *  Currently, we don't check whether or not these registers
	 *  get spilled, so we must save and restore any that we
	 *  modify.  We've already saved a4 and a5
	 *  which we modify as part of the pseudo-CALL.
	 *
	 *  IMPLEMENTATION NOTE:
	 *
	 *	The pseudo-CALL below effectively saves registers a2..a3 so
	 *	that they are available again after the corresponding
	 *	RETW when returning from the exception handling.  We
	 *	could choose to put something like EPC1 or PS in
	 *	there, so they're available more quickly when
	 *	restoring.  HOWEVER, exception handlers may wish to
	 *	change such values, or anything on the exception stack
	 *	frame, and expect these to be restored as modified.
	 *
	 *	NOTA: future: figure out what's the best thing to put
	 *	in a2 and a3.  (candidate: a4 and a5 below; but what
	 *	if exception handler manipulates ARs, as in a syscall
	 *	handler.... oh well)
	 *
	 *
	 *  Now do the pseudo-CALL.
	 *  Make it look as if the code that got the exception made a
	 *  CALL4 to the exception handling code.  (We call
	 *  this the "pseudo-CALL".)
	 *
	 *  This pseudo-CALL is important and done this way:
	 *
	 *	1. There are only three ways to safely update the stack pointer
	 *	   in the windowed ABI, such that window exceptions work correctly:
	 *	   (a) spill all live windows to stack then switch to a new stack
	 *	       (or, save the entire address register file and window
	 *	        registers, which is likely even more expensive)
	 *	   (b) use MOVSP (or equivalent)
	 *	   (c) use ENTRY/RETW
	 *	   Doing (a) is excessively expensive, and doing (b) here requires
	 *	   copying 16 bytes back and forth which is also time-consuming;
	 *	   whereas (c) is very efficient, so that's what we do here.
	 *
	 *	2. Normally we cannot do a pseudo-CALL8 or CALL12 here.
	 *	   According to the
	 *	   windowed ABI, a function must allocate enough space
	 *	   for the largest call that it makes.  However, the
	 *	   pseudo-CALL is executed in the context of the
	 *	   function that happened to be executing at the time
	 *	   the interrupt was taken, and that function might or
	 *	   might not have allocated enough stack space for a
	 *	   CALL8 or a CALL12.  If we try doing a pseudo-CALL8
	 *	   or -CALL12 here, we corrupt the stack if the
	 *	   interrupted function happened to not have allocated
	 *	   space for such a call.
	 *
	 *	3. We set the return PC, but it's not strictly
	 *         necessary for proper operation.  It does make
	 *         debugging, ie. stack tracebacks, much nicer if it
	 *         can point to the interrupted code (not always
	 *         possible, eg. if interrupted code is in a different
	 *         GB than the interrupt handling code, which is
	 *         unlikely in a system without protection where
	 *         interrupt handlers and general application code are
	 *         typically linked together).
	 *
	 *  IMPORTANT:  Interrupts must stay disabled while doing the pseudo-CALL,
	 *  or at least until after the ENTRY instruction, because SP has been
	 *  restored to its original value that does not reflect the exception
	 *  stack frame's allocation.  An interrupt taken here would
	 *  corrupt the exception stack frame (ie. allocate another over it).
	 *  (High priority interrupts can remain enabled, they save and restore
	 *  all of their state and use their own stack or save area.)
	 *  For the same reason, we mustn't get any exceptions in this code
	 *  (other than window exceptions where noted) until ENTRY is done.
	 */

	//  HERE:  may get a single window overflow (caused by the following instruction).

# if XTOS_DEBUG_PC
	movi	a4, 0xC0000000		// [for debug] for return PC computation below
	or	a3, a4, a3		// [for debug] set upper two bits of return PC
	addx2	a4, a4, a3		// [for debug] clear upper bit
# else
	movi	a4, 0			// entry cannot cause overflow, cause it here
# endif

	.global	_GeneralException
_GeneralException:			// this label makes tracebacks through exceptions look nicer

	_entry	a1, ESF_TOTALSIZE	// as if after a CALL4 (PS.CALLINC set to 1 above)

	/*
	 *  The above ENTRY instruction does a number of things:
	 *
	 *	1. Because we're emulating CALL4, the ENTRY rotates windows
	 *	   forward by 4 registers (as per 'ROTW +1'), so that
	 *	   a4-a15 became a0-a11.  So now: a0-a11 are part of
	 *	   the interrupted context to be preserved.  a0-a1
	 *	   were already saved above when they were a4-a5.
	 *	   a12-a15 are free to use as they're NOT part of the
	 *	   interrupted context.  We don't need to save/restore
	 *	   them, and they will get spilled if needed.
	 *
	 *	2. Updates SP (new a1), allocating the exception stack
	 *	   frame in the new window, preserving the old a1 in
	 *	   the previous window.
	 *
	 *	3. The underscore prefix prevents the assembler from
	 *	   automatically aligning the ENTRY instruction on a
	 *	   4-byte boundary, which could create a fatal gap in
	 *	   the instruction stream.
	 *
	 *  At this point, ie. before we re-enable interrupts, we know the caller is
	 *  always live so we can safely modify a1 without using MOVSP (we can use MOVSP
	 *  but it will never cause an ALLOCA or underflow exception here).
	 *  So this is a good point to modify the stack pointer if we want eg. to
	 *  switch to an interrupt stack (if we do, we need to save the current SP
	 *  because certain things have been saved to that exception stack frame).
	 *  We couldn't do this easily before ENTRY, where the caller wasn't
	 *  necessarily live.
	 *
	 *  NOTE:  We don't switch to an interrupt stack here, because exceptions
	 *  are generally caused by executing code -- so we handle exceptions in
	 *  the context of the thread that cause them, and thus remain on the same
	 *  stack.  This means a thread's stack must be large enough to handle
	 *  the maximum level of nesting of exceptions that the thread can cause.
	 */

	//  NOTA:  exception handlers for certain causes may need interrupts to be kept
	//  disabled through their dispatch, so they can turn them off themselves at
	//  the right point (if at all), eg. to save critical state unknown to this
	//  code here, or for some recovery action that must be atomic with respect
	//  to interrupts....
	//
	//  Perhaps two versions of this assembly-level handler are needed, one that restores
	//  interrupts to what they were before the exception was taken (as here)
	//  and one that ensures at least low-priority interrupts are kept disabled?
	//  NOTA:  For now, always enable interrupts here.

	/*
	 *  Now we can enable interrupts.
	 *  (Pseudo-CALL is complete, and SP reflects allocation of exception stack frame.)
	 */

#endif  /* __XTENSA_CALL0_ABI__ */


#if XCHAL_HAVE_INTERRUPTS
# if XCHAL_HAVE_XEA1
	//... recompute and set INTENABLE ...
	l32i	a13, a1, UEXC_sar	// (temporary holding place for INTENABLE value saved before pseudo-CALL4 above)
	rsr	a12, SAR
	wsr	a13, INTENABLE		// restore INTENABLE as it was on entry
# else
	rsr	a12, SAR
	rsil	a13, 0
# endif
#else
	rsr	a12, SAR
#endif

	movi	a13, _xtos_c_handler_table	// &table
	l32i	a15, a1, UEXC_exccause		// arg2: exccause

	s32i	a12, a1, UEXC_sar
	save_loops_mac16	a1, a12, a14	// save LOOP & MAC16 regs, if configured

	addx4	a12, a15, a13		// a12 = table[exccause]
	l32i	a12, a12, 0		// ...
#ifdef __XTENSA_CALL0_ABI__
	mov	a2, a1			// arg1: exception parameters
	mov	a3, a15			// arg2: exccause
	beqz	a12, 1f			// null handler => skip call
	callx0	a12			// call C exception handler for this exception
#else
	mov	a14, a1			// arg1: exception parameters
	// mov	a15, a15		// arg2: exccause, already in a15
	beqz	a12, 1f			// null handler => skip call
	callx12	a12			// call C exception handler for this exception
#endif
1:
	//  Now exit the handler.


	// Restore special registers

	restore_loops_mac16	a1, a13, a14, a15	// restore LOOP & MAC16 regs, if configured
	l32i	a14, a1, UEXC_sar

	/*
	 *  Disable interrupts while returning from the pseudo-CALL setup above,
	 *  for the same reason they were disabled while doing the pseudo-CALL:
	 *  this sequence restores SP such that it doesn't reflect the allocation
	 *  of the exception stack frame, which we still need to return from
	 *  the exception.
	 */

#if XCHAL_HAVE_INTERRUPTS
# if XCHAL_HAVE_XEA1
	//  Must disable interrupts via INTENABLE, because PS.INTLEVEL gets zeroed
	//  by any window exception exit, eg. the window underflow that may happen
	//  upon executing the RETW instruction.
	//  Also, must disable at XTOS_LOCKLEVEL, not just EXCM_LEVEL, because this
	//  code effectively manipulates virtual INTENABLE state up to the point
	//  INTENABLE is written in _xtos_return_from_exc.
	//
	rsilft	a12, 1, XTOS_LOCKLEVEL	// lockout
	rsr	a12, INTENABLE
	//movi	a13, ~XCHAL_EXCM_MASK
	movi	a13, ~XTOS_LOCKOUT_MASK	// mask out low and medium priority levels, and high priority levels covered by
					//  XTOS_LOCKLEVEL if any, so we can run at PS.INTLEVEL=0 while manipulating INTENABLE
	s32i	a12, a1, UEXC_sar	// (temporary holding place for INTENABLE value to restore after pseudo-CALL4 below)
	and	a13, a12, a13		// mask out selected interrupts
	wsr	a13, INTENABLE		// disable all interrupts up to and including XTOS_LOCKLEVEL
# else
	rsil	a12, XCHAL_EXCM_LEVEL
# endif
#endif
	wsr	a14, SAR

	movi	a0, _xtos_return_from_exc
#ifdef __XTENSA_CALL0_ABI__
	jx	a0
#else /* ! __XTENSA_CALL0_ABI__ */
	/*  Now return from the pseudo-CALL from the interrupted code, to rotate
	 *  our windows back... */

	movi	a13, 0xC0000000
	//movi	a13, 3
	//slli	a13, a13, 30
# if XCHAL_HAVE_XEA1 && XCHAL_HAVE_INTERRUPTS
	rsync		//NOT-ISA-DEFINED	// wait for WSR to INTENABLE to complete before doing RETW
			// (ie. before underflow exception exit)
			// (not needed, because underflow exception entry does implicit ISYNC ??
			//  but in case underflow not taken, WSR must complete before wsr to PS that lowers PS.INTLEVEL
			//  possibly below XTOS_LOCKLEVEL, in which RETW's jump is not sufficient sync, so a sync
			//  is needed but it can be placed just before WSR to PS -- but here is fine)
# endif
	or	a0, a0, a13		// set upper two bits
	addx2	a0, a13, a0		// clear upper bit
	retw
#endif /* ! __XTENSA_CALL0_ABI__ */

	/* FIXME: what about _GeneralException ? */
	.size	_xtos_c_wrapper_handler, . - _xtos_c_wrapper_handler


#endif /* XCHAL_HAVE_EXCEPTIONS */

