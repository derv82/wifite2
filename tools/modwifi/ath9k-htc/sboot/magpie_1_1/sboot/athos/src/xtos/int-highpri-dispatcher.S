// High-Priority Interrupt Dispatcher Template
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/int-highpri-dispatcher.S#4 $

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
// This file allows writing high-priority interrupt handlers in C,
// providing convenience at a significant cost in performance.
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


#define INTLEVEL_N_MASK		INTERRUPT_MASK	// mask of interrupts at this priority
#define INTLEVEL_N_NUM		SINGLE_INT_NUM	// interrupt number if there is only one
#define INTLEVEL_N_BELOW_MASK	XCHAL_INTLEVEL_ANDBELOW_MASK(_INTERRUPT_LEVEL)

/*  Indicates whether there are multiple interrupts at this interrupt
 *  priority, ie. mapped to this interrupt vector.
 *  If there is only one, its number is INTLEVEL_N_NUM
 */
#define MULTIPLE_INTERRUPTS	(!SINGLE_INTERRUPT)

/*
 *  High priority interrupt stack frame:
 */
STRUCT_BEGIN
STRUCT_FIELD (long,4,HESF_,SAR)
STRUCT_FIELD (long,4,HESF_,WINDOWSTART)
STRUCT_FIELD (long,4,HESF_,WINDOWBASE)
STRUCT_FIELD (long,4,HESF_,EPC1)
STRUCT_FIELD (long,4,HESF_,EXCCAUSE)
STRUCT_FIELD (long,4,HESF_,EXCVADDR)
STRUCT_FIELD (long,4,HESF_,EXCSAVE1)
STRUCT_FIELD (long,4,HESF_,VPRI)	/* (XEA1 only) */
#if XCHAL_HAVE_MAC16
STRUCT_FIELD (long,4,HESF_,ACCLO)
STRUCT_FIELD (long,4,HESF_,ACCHI)
/*STRUCT_AFIELD(long,4,HESF_,MR, 4)*/
#endif
#if XCHAL_HAVE_LOOPS
STRUCT_FIELD (long,4,HESF_,LCOUNT)
STRUCT_FIELD (long,4,HESF_,LBEG)
STRUCT_FIELD (long,4,HESF_,LEND)
#endif
STRUCT_AFIELD(long,4,HESF_,AREG, 64)	/* address registers ar0..ar63 */
#define HESF_AR(n)	HESF_AREG+((n)*4)
STRUCT_END(HighPriFrame)
#define HESF_TOTALSIZE	HighPriFrameSize+32	/* 32 bytes for interrupted code's save areas under SP */


#if XCHAL_HAVE_XEA1 && HAVE_XSR		/* could be made true for T1040 and T1050 */
# error "high-priority interrupt stack frame needs adjustment if HAVE_XSR is allowed with XEA1"
#endif


#define PRI_N_STACK_SIZE	1024	/* default to 1 kB stack for each level-N handling */


	//  Allocate save area and stack:
	//  (must use .bss, not .comm, because the subsequent .set does not work otherwise)
	.section .bss, "aw"
	.align	16
LABEL(_Pri_,_Stack):	.space	PRI_N_STACK_SIZE + HESF_TOTALSIZE

#if HAVE_XSR
	.data
	.global	LABEL(_Pri_,_HandlerAddress)
LABEL(_Pri_,_HandlerAddress):	.space 4
#endif


	.text
	.align	4
	.global	LABEL(_Level,FromVector)
LABEL(_Level,FromVector):
	movi	a2, LABEL(_Pri_,_Stack) + PRI_N_STACK_SIZE	// get ptr to save area
	// interlock

	//  Save a few registers so we can do some work:
	s32i	a0,  a2, HESF_AR(0)
#if HAVE_XSR
	//movi	a0, LABEL(_Level,FromVector)		// this dispatcher's address
	movi	a0, LABEL(_Pri_,_HandlerAddress)	// dispatcher address var.
	s32i	a1,  a2, HESF_AR(1)
	l32i	a0, a0, 0				// get dispatcher address
	s32i	a3,  a2, HESF_AR(3)
	xsr	a0, EXCSAVE_LEVEL	// get saved a2, restore dispatcher address
#else
	rsr	a0, EXCSAVE_LEVEL	// get saved a2
	s32i	a1,  a2, HESF_AR(1)
	s32i	a3,  a2, HESF_AR(3)
#endif
	s32i	a4,  a2, HESF_AR(4)
	s32i	a0,  a2, HESF_AR(2)

	//  Save/restore all exception state
	//  (IMPORTANT:  this code assumes no general exceptions occur
	//   during the execution of this dispatcher until this state
	//   is completely saved and from the point it is restored.)
	//
	//  Exceptions that may normally occur within the C handler
	//  include window exceptions (affecting EPC1), alloca exceptions
	//  (affecting EPC1/EXCCAUSE and its handling uses EXCSAVE1),
	//  and possibly others depending on the particular C handler
	//  (possibly needing save/restore of EXCVADDR; and EXCVADDR
	//   is also possibly corrupted by any access thru an auto-refill
	//   way on a processor with a full MMU).
	//
	rsr	a3, EPC1
	rsr	a4, EXCCAUSE
	s32i	a3, a2, HESF_EPC1
	s32i	a4, a2, HESF_EXCCAUSE
#if !XCHAL_HAVE_XEA1
	rsr	a3, EXCVADDR
	s32i	a3, a2, HESF_EXCVADDR
#endif
	rsr	a4, EXCSAVE1
	s32i	a4, a2, HESF_EXCSAVE1

#ifdef __XTENSA_WINDOWED_ABI__
	//  Save remainder of entire address register file (!):
	movi	a0, XCHAL_NUM_AREGS - 8		// how many saved so far
#endif

	s32i	a5,  a2, HESF_AR(5)
	s32i	a6,  a2, HESF_AR(6)
	s32i	a7,  a2, HESF_AR(7)

1:	s32i	a8,  a2, HESF_AR(8)
	s32i	a9,  a2, HESF_AR(9)
	s32i	a10, a2, HESF_AR(10)
	s32i	a11, a2, HESF_AR(11)
	s32i	a12, a2, HESF_AR(12)
	s32i	a13, a2, HESF_AR(13)
	s32i	a14, a2, HESF_AR(14)
	s32i	a15, a2, HESF_AR(15)

#ifdef __XTENSA_WINDOWED_ABI__
	addi	a8, a0, -8
	addi	a10, a2, 8*4
	rotw	2
	bnez	a0, 1b			// loop until done

	rotw	2
	// back to original a2 ...

	//  Save a few other registers required for C:
	rsr	a3, WINDOWSTART
	rsr	a4, WINDOWBASE
	s32i	a3, a2, HESF_WINDOWSTART
	s32i	a4, a2, HESF_WINDOWBASE

	//  Setup window registers for first caller:
	movi	a3, 1
	movi	a4, 0
	wsr	a3, WINDOWSTART
	wsr	a4, WINDOWBASE
	rsync

	//  Note:  register window has rotated, ie. a0..a15 clobbered.

#endif /* __XTENSA_WINDOWED_ABI__ */

	movi	a1, LABEL(_Pri_,_Stack) + PRI_N_STACK_SIZE	// get ptr to save area (is also initial stack ptr)
	movi	a0, 0		// mark start of call frames in stack

	//  Critical state saved, a bit more to do to allow window exceptions...

	//  We now have a C-coherent stack and window state.
	//  Still have to fix PS while making sure interrupts stay disabled
	//  at the appropriate level (ie. level 2 and below are disabled in this case).

#if XCHAL_HAVE_XEA1
	movi	a7, _xtos_intstruct		// address of interrupt management globals
	rsilft	a3, _INTERRUPT_LEVEL, XTOS_LOCKLEVEL	// lockout
	movi	a4, ~INTLEVEL_N_BELOW_MASK	// mask out all interrupts at this level or lower
	l32i	a3, a7, XTOS_VPRI_ENABLED_OFS	// read previous _xtos_vpri_enabled
	l32i	a5, a7, XTOS_ENABLED_OFS	// read _xtos_enabled
	s32i	a4, a7, XTOS_VPRI_ENABLED_OFS	// set new _xtos_vpri_enabled (mask interrupts as if at _INTERRUPT_LEVEL)
	s32i	a3, a1, HESF_VPRI		// save previous vpri
	movi	a2, 0x50020			// WOE=1, UM=1, INTLEVEL=0
	and	a3, a5, a4			// mask out selected interrupts
	wsr	a3, INTENABLE			// disable all low-priority interrupts
#else
	//  Load PS for C code, clear EXCM (NOTE: this step is different for XEA1):
# ifdef __XTENSA_CALL0_ABI__
	movi	a2, 0x00020 + _INTERRUPT_LEVEL	// WOE=0, CALLINC=0, UM=1, INTLEVEL=N, EXCM=0, RING=0
# else
	movi	a2, 0x50020 + _INTERRUPT_LEVEL	// WOE=1, CALLINC=1, UM=1, INTLEVEL=N, EXCM=0, RING=0
# endif

#endif
	wsr	a2, PS				// update PS to enable window exceptions, etc as per above
	rsync

	//  Okay, window exceptions can now happen (although we have to call
	//  deep before any will happen because we've reset WINDOWSTART).

	//  Save other state that might get clobbered by C code:

//////////////////  COMMON DISPATCH CODE BEGIN

	rsr	a14, SAR
	s32i	a14, a1, HESF_SAR
#if XCHAL_HAVE_LOOPS
	rsr	a14, LCOUNT
	s32i	a14, a1, HESF_LCOUNT
	rsr	a14, LBEG
	s32i	a14, a1, HESF_LBEG
	rsr	a14, LEND
	s32i	a14, a1, HESF_LEND
#endif
#if XCHAL_HAVE_MAC16
	rsr	a14, ACCLO
	s32i	a14, a1, HESF_ACCLO
	rsr	a14, ACCHI
	s32i	a14, a1, HESF_ACCHI
#endif

#if MULTIPLE_INTERRUPTS		/* > 1 interrupts at this priority */	// _split_ multi_setup
#define TABLE_OFS	0

	rsr	a15, INTERRUPT		// mask of pending interrupts
# if XCHAL_HAVE_XEA1
	l32i	a12, a7, XTOS_ENABLED_OFS	// mask of enabled interrupts
# else
	rsr	a12, INTENABLE		// mask of enabled interrupts
# endif
	movi	a13, INTLEVEL_N_MASK	// mask of interrupts at this priority level
	and	a15, a15, a12
	and	a15, a15, a13		// enabled & pending interrupts at this priority
	_beqz	a15, LABEL(Pri_,_spurious)	// handle spurious interrupts (eg. level-trig.)
LABEL(Pri_,_loop):				// handle all enabled & pending interrupts
	neg	a14, a15
	and	a14, a14, a15		// single-out least-significant bit set in mask
	wsr	a14, INTCLEAR		// clear if edge-trig. or s/w or wr/err (else no effect)

	//  Compute pointer to interrupt table entry, given mask a14 with single bit set:

# if XCHAL_HAVE_NSA
	movi	a12, _xtos_interrupt_table - (32-XCHAL_NUM_INTERRUPTS)*8
	nsau	a14, a14		// get index of bit in a14, numbered from msbit
	addx8	a12, a14, a12
# else /* XCHAL_HAVE_NSA */
	movi	a12, _xtos_interrupt_table	// pointer to interrupt table
	bltui	a14, 0x10000, 1f	// in 16 lsbits? (if so, check them)
	addi	a12, a12, 16*8		// no, index is at least 16 entries further
	// (the above ADDI expands to an ADDI+ADDMI sequence, +128 is outside its range)
	extui	a14, a14, 16,16		// shift right upper 16 bits
1:	bltui	a14, 0x100, 1f		// in 8 lsbits? (if so, check them)
	addi	a12, a12, 8*8		// no, index is at least 8 entries further
	srli	a14, a14, 8		// shift right upper 8 bits
1:	bltui	a14, 0x10, 1f		// in 4 lsbits? (if so, check them)
	addi	a12, a12, 4*8		// no, index is at least 4 entries further
	srli	a14, a14, 4		// shift right 4 bits
1:	bltui	a14, 0x4, 1f		// in 2 lsbits? (if so, check them)
	addi	a12, a12, 2*8		// no, index is at least 2 entries further
	srli	a14, a14, 2		// shift right 2 bits
1:	bltui	a14, 0x2, 1f		// is it the lsbit?
	addi	a12, a12, 1*8		// no, index is one entry further
1:					// done! a12 points to interrupt's table entry
# endif /* XCHAL_HAVE_NSA */

#else /* !MULTIPLE_INTERRUPTS */

# if XCHAL_HAVE_NSA
#  define TABLE_OFS	8 * (XCHAL_NUM_INTERRUPTS - 1 - INTLEVEL_N_NUM)
# else
#  define TABLE_OFS	8 * INTLEVEL_N_NUM
# endif

	movi	a13, INTLEVEL_N_MASK	// (if interrupt is s/w or edge-triggered or write/err only)
	movi	a12, _xtos_interrupt_table	// get pointer to its interrupt table entry
	wsr	a13, INTCLEAR		// clear the interrupt (if s/w or edge or wr/err only)

#endif /* ifdef MULTIPLE_INTERRUPTS */

	l32i	a13, a12, TABLE_OFS + 0	// get pointer to handler from table entry
#ifdef __XTENSA_CALL0_ABI__
	l32i	a2, a12, TABLE_OFS + 4	// pass single argument to C handler
	callx0	a13			// call interrupt's C handler
#else
	l32i	a6, a12, TABLE_OFS + 4	// pass single argument to C handler
	callx4	a13			// call interrupt's C handler
#endif

#if XCHAL_HAVE_XEA1
	movi	a7, _xtos_intstruct	// address of interrupt management globals
#endif
#if MULTIPLE_INTERRUPTS		/* > 1 interrupts at this priority */
	rsr	a15, INTERRUPT		// get pending interrupts
# if XCHAL_HAVE_XEA1
	l32i	a12, a7, XTOS_ENABLED_OFS	// get enabled interrupts
# else
	rsr	a12, INTENABLE		// get enabled interrupts
# endif
	movi	a13, INTLEVEL_N_MASK	// get mask of interrupts at this priority level
	and	a15, a15, a12
	and	a15, a15, a13		// pending+enabled interrupts at this priority
	_bnez	a15, LABEL(Pri_,_loop)	// if any remain, dispatch one
LABEL(Pri_,_spurious):
#endif /* MULTIPLE_INTERRUPTS */

	//  Restore everything, and return.

	//  Three temp registers are required for this code to be optimal (no interlocks) in
	//  T2xxx microarchitectures with 7-stage pipe; otherwise only two
	//  registers would be needed.
	//
#if XCHAL_HAVE_LOOPS
	l32i	a13, a1, HESF_LCOUNT
	l32i	a14, a1, HESF_LBEG
	l32i	a15, a1, HESF_LEND
	wsr	a13, LCOUNT
	wsr	a14, LBEG
	wsr	a15, LEND
#endif

#if XCHAL_HAVE_MAC16
	l32i	a13, a1, HESF_ACCLO
	l32i	a14, a1, HESF_ACCHI
	wsr	a13, ACCLO
	wsr	a14, ACCHI
#endif
	l32i	a15, a1, HESF_SAR
	wsr	a15, SAR

//////////////////  COMMON DISPATCH CODE END

#if XCHAL_HAVE_XEA1
	//  Here, a7 = address of interrupt management globals
	l32i	a4, a1, HESF_VPRI		// restore previous vpri
	rsil	a3, XTOS_LOCKLEVEL		// lockout
	l32i	a5, a7, XTOS_ENABLED_OFS	// read _xtos_enabled
	s32i	a4, a7, XTOS_VPRI_ENABLED_OFS	// set new _xtos_vpri_enabled
	movi	a2, 0x00020 + _INTERRUPT_LEVEL	// WOE=0, UM=1, INTLEVEL=N
	and	a3, a5, a4			// mask out selected interrupts
	wsr	a3, INTENABLE			// disable all low-priority interrupts
#else
	//  Load PS for interrupt exit, set EXCM:
	movi	a2, 0x00030 + _INTERRUPT_LEVEL	// WOE=0, CALLINC=0, UM=1, INTLEVEL=N, EXCM=1, RING=0
#endif
	wsr	a2, PS				// update PS to disable window exceptions, etc as per above
	rsync

	//  NOTE:  here for XEA1, restore INTENABLE etc...

#ifdef __XTENSA_WINDOWED_ABI__
	//  Restore window registers:
	l32i	a2, a1, HESF_WINDOWSTART
	l32i	a3, a1, HESF_WINDOWBASE
	wsr	a2, WINDOWSTART
	wsr	a3, WINDOWBASE
	rsync
	//  Note:  register window has rotated, ie. a0..a15 clobbered.

	//  Reload initial stack pointer:
	movi	a1, LABEL(_Pri_,_Stack) + PRI_N_STACK_SIZE	// - 16
	movi	a6, XCHAL_NUM_AREGS - 8		// how many saved so far
	addi	a7, a1, -8*4

	//  Restore entire register file (!):

1:
	addi	a14, a6, -8
	addi	a15, a7, 8*4
  	l32i	a4, a15, HESF_AR(4)
	l32i	a5, a15, HESF_AR(5)
	l32i	a6, a15, HESF_AR(6)
	l32i	a7, a15, HESF_AR(7)
  	l32i	a8, a15, HESF_AR(8)
	l32i	a9, a15, HESF_AR(9)
	l32i	a10,a15, HESF_AR(10)
	l32i	a11,a15, HESF_AR(11)
	rotw	2
	bnez	a6, 1b			// loop until done

	l32i	a4, a7, HESF_AR(12)
	l32i	a5, a7, HESF_AR(13)
	l32i	a6, a7, HESF_AR(14)
	l32i	a7, a7, HESF_AR(15)
	rotw	2

	// back to original a1 ...

#else  /* Call0 ABI: */

  	l32i	a4, a1, HESF_AR(4)	// restore general registers
	l32i	a5, a1, HESF_AR(5)
	l32i	a6, a1, HESF_AR(6)
	l32i	a7, a1, HESF_AR(7)
  	l32i	a8, a1, HESF_AR(8)
	l32i	a9, a1, HESF_AR(9)
	l32i	a10, a1, HESF_AR(10)
	l32i	a11, a1, HESF_AR(11)
	l32i	a12, a1, HESF_AR(12)
	l32i	a13, a1, HESF_AR(13)
	l32i	a14, a1, HESF_AR(14)
	l32i	a15, a1, HESF_AR(15)

#endif  /* __XTENSA_WINDOWED_ABI__ */

	//  Restore exception state:
	l32i	a2, a1, HESF_EPC1
	l32i	a3, a1, HESF_EXCCAUSE
	wsr	a2, EPC1
	wsr	a3, EXCCAUSE
#if !XCHAL_HAVE_XEA1
	l32i	a2, a1, HESF_EXCVADDR
	wsr	a2, EXCVADDR
#endif
	l32i	a3, a1, HESF_EXCSAVE1
	wsr	a3, EXCSAVE1

	l32i	a0,  a1, HESF_AR(0)
	l32i	a2,  a1, HESF_AR(2)
	l32i	a3,  a1, HESF_AR(3)
	l32i	a1,  a1, HESF_AR(1)
	rfi	_INTERRUPT_LEVEL

	.size	LABEL(_Level,FromVector), . - LABEL(_Level,FromVector)

	//  This symbol exists solely for the purpose of being able to pull-in this
	//  dispatcher using _xtos_dispatch_level<n>() routines with the tiny-rt LSP:
	.global	LABEL(_Level,HandlerLabel)
	.set LABEL(_Level,HandlerLabel), 0

#endif /* XCHAL_HAVE_INTERRUPTS */

