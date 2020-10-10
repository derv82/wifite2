// Medium-Priority Interrupt Dispatcher Template
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/int-medpri-dispatcher.S#4 $

// Copyright (c) 2004-2010 Tensilica Inc.
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

//
// By default, this file is included by inth-template.S .
// The default Makefile defines _INTERRUPT_LEVEL when assembling
// inth-template.S for each medium and high priority interrupt level.
//
// To use this template file, define a macro called _INTERRUPT_LEVEL
// to be the interrupt priority level of the vector, then include this file.


#include <xtensa/coreasm.h>
#include "xtos-internal.h"


#if XCHAL_HAVE_INTERRUPTS

#define INTERRUPT_MASK		XCHAL_INTLEVEL_MASK(_INTERRUPT_LEVEL)
#define SINGLE_INTERRUPT	((INTERRUPT_MASK & (INTERRUPT_MASK - 1)) == 0)
#define SINGLE_INT_NUM		XCHAL_INTLEVEL_NUM(_INTERRUPT_LEVEL)


//  Strict non-preemptive prioritization


	.text
	.align	4
	.global	LABEL(_Level,FromVector)
LABEL(_Level,FromVector):

/* Allocate an exception stack frame, save a2, a4, and a5, and fix PS as:
 *
 *   if not Call0 ABI
 *	- enable windowing for 'entry' (ps.woe=1, ps.excm=0)
 *	- setup ps.callinc to simulate call4
 *   endif
 *	- preserve user mode
 *	- mask all interrupts at EXCM_LEVEL and lower
 *
 * Then deallocate the stack, 'rsync' for the write to PS, then use
 * 'entry' to re-allocate the stack frame and rotate the register
 * window (like a call4, preserving a0..a3). */

#if HAVE_XSR
	xsr	a2, EXCSAVE_LEVEL
#else
	rsr	a2, EXCSAVE_LEVEL
#endif
	addi	a1, a1, -ESF_TOTALSIZE
	s32i	a2, a1, UEXC_a2
#ifdef __XTENSA_CALL0_ABI__
	movi	a2, PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)
#else
	movi	a2, PS_WOE|PS_CALLINC(1)|PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)
#endif
	s32i	a4, a1, UEXC_a4
	s32i	a5, a1, UEXC_a5
	wsr	a2, PS
	rsync

#ifdef __XTENSA_CALL0_ABI__
	s32i	a0, a1, UEXC_a0
	s32i	a3, a1, UEXC_a3
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
	movi	a0, 0			/* terminate stack frames */
#  if XTOS_DEBUG_PC
	// TODO: setup return PC for call traceback through interrupt dispatch
#  endif
#else
#  if XTOS_CNEST
	l32i	a2, a1, ESF_TOTALSIZE-20	// save nested-C-func call-chain ptr
#  endif
	addi	a1, a1, ESF_TOTALSIZE
#  if XTOS_DEBUG_PC
	rsr	a4, EPC+_INTERRUPT_LEVEL // [for debug] get return PC
	movi	a5, 0xC0000000		// [for debug] setup call size...
	or	a4, a5, a4		// [for debug] set upper two bits of return PC
	addx2	a4, a5, a4		// [for debug] clear upper bit
#  else
	movi	a4, 0			/* terminate stack frames, overflow check */
#  endif
	_entry	a1, ESF_TOTALSIZE
#endif

/* Reset the interrupt level to mask all interrupts at the current
 * priority level and lower.  Note the current priority level may be
 * less than or equal to EXCM_LEVEL. */

	rsil	a15, _INTERRUPT_LEVEL

#if SINGLE_INTERRUPT  /* if only one interrupt at this priority level... */

/* Preserve the SAR, loop, and MAC16 regs.  Also, clear the interrupt. */

	rsr	a14, SAR
	movi	a12, INTERRUPT_MASK
	s32i	a14, a1, UEXC_sar
	wsr	a12, INTCLEAR	// clear if edge-trig or s/w or wr/err (else no effect)
	save_loops_mac16	a1, a13, a14

/* Load the handler from the table, initialize two args (interrupt
 * number and exception stack frame), then call the interrupt handler.
 * Note: The callx12 preserves the original user task's a4..a15.*/

	movi	a12, _xtos_interrupt_table +  MAPINT(SINGLE_INT_NUM)*XIE_SIZE
	l32i	a13, a12, XIE_HANDLER
# ifdef __XTENSA_CALL0_ABI__
	l32i	a2, a12, XIE_ARG
	mov	a3, a1
	callx0	a13
# else
	l32i	a14, a12, XIE_ARG
	mov	a15, a1
	callx12	a13
# endif

#else /* > 1 interrupts at this priority level */

/* Get bit list of pending interrupts at the current interrupt priority level.
 * If bit list is empty, interrupt is spurious (can happen if a
 * genuine interrupt brings control this direction, but the interrupt
 * goes away before we read the INTERRUPT register).  Also save off
 * sar, loops, and mac16 registers. */

	rsr	a15, INTERRUPT
	rsr	a12, INTENABLE
	movi	a13, INTERRUPT_MASK
	and	a15, a15, a12
	and	a15, a15, a13
	rsr	a14, SAR
	_beqz	a15, LABEL(spurious,int)
	s32i	a14, a1, UEXC_sar
	save_loops_mac16	a1, a13, a14

/* Loop to handle all pending interrupts. */

LABEL(.L1,_loop0):
	neg	a12, a15
	and	a12, a12, a15
	wsr	a12, INTCLEAR	// clear if edge-trig or s/w or wr/err (else no effect)
	movi	a13, _xtos_interrupt_table
	find_ms_setbit	a15, a12, a14, 0
	mapint	a15
	addx8	a12, a15, a13
	l32i	a13, a12, XIE_HANDLER
# ifdef __XTENSA_CALL0_ABI__
	l32i	a2, a12, XIE_ARG
	mov	a3, a1
	callx0	a13
# else
	l32i	a14, a12, XIE_ARG
	mov	a15, a1
	callx12	a13
# endif
	rsr	a15, INTERRUPT
	rsr	a12, INTENABLE
	movi	a13, INTERRUPT_MASK
	and	a15, a15, a12
	and	a15, a15, a13
	_bnez	a15, LABEL(.L1,_loop0)

#endif /* SINGLE_INTERRUPT */

/* Restore everything, and return. */

	restore_loops_mac16	a1, a13, a14, a15
	l32i	a14, a1, UEXC_sar
LABEL(spurious,int):

#ifdef __XTENSA_CALL0_ABI__
	wsr	a14, SAR
	l32i	a0, a1, UEXC_a0
	l32i	a2, a1, UEXC_a2
	l32i	a3, a1, UEXC_a3
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
	addi	a1, a1, ESF_TOTALSIZE	// restore sp
	rfi	_INTERRUPT_LEVEL

#else /* windowed ABI: */

	movi	a0, LABEL(return,from_exc)
	movi	a13, 0xC0000000
	wsr	a14, SAR
	or	a0, a0, a13
	addx2	a0, a13, a0
# if _INTERRUPT_LEVEL < XCHAL_EXCM_LEVEL
/* Raise the interrupt mask before
 * returning to avoid a race condition where we deallocate the
 * exception stack frame but still have more register values to
 * restore from it. */
	rsil	a14, XCHAL_EXCM_LEVEL
# endif
	retw
LABEL(return,from_exc):
# if XTOS_CNEST
	s32i	a2, a5, ESF_TOTALSIZE-20	// restore nested-C-func call-chain ptr
# endif
	l32i	a2, a5, UEXC_a2
	l32i	a4, a5, UEXC_a4
	l32i	a5, a5, UEXC_a5
	rfi	_INTERRUPT_LEVEL
#endif /* windowed ABI */

	.size	LABEL(_Level,FromVector), . - LABEL(_Level,FromVector)

	//  This symbol exists solely for the purpose of being able to pull-in this
	//  dispatcher using _xtos_dispatch_level<n>() routines with the tiny-rt LSP:
	.global	LABEL(_Level,HandlerLabel)
	.set LABEL(_Level,HandlerLabel), 0

#endif /* XCHAL_HAVE_INTERRUPT */

