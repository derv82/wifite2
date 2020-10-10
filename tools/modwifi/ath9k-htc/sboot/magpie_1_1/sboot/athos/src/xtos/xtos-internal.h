/*
 * xtos-internal.h  --  internal definitions for single-threaded run-time
 *
 * Copyright (c) 2003-2010 Tensilica Inc.
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

#ifndef XTOS_INTERNAL_H
#define XTOS_INTERNAL_H

#include <xtensa/config/core.h>
#include <xtensa/xtruntime.h>
#include <xtensa/xtruntime-frames.h>
#include <xtensa/xtensa-versions.h>
#ifndef XTOS_PARAMS_H	/* this to allow indirect inclusion of this header from the outside */
#include "xtos-params.h"
#endif

/*  Relative ordering of subpriorities within an interrupt level (or vector):  */
#define XTOS_SPO_ZERO_LO	0	/* lower (eg. zero) numbered interrupts are lower  priority than higher numbered interrupts */
#define XTOS_SPO_ZERO_HI	1	/* lower (eg. zero) numbered interrupts are higher priority than higher numbered interrupts */


/*  Sanity check some parameters from xtos-params.h:  */
#if XTOS_LOCKLEVEL < XCHAL_EXCM_LEVEL || XTOS_LOCKLEVEL > 15
# error Invalid XTOS_LOCKLEVEL value, must be >= EXCM_LEVEL and <= 15, please fix xtos-params.h
#endif

/*  Mask of interrupts locked out at XTOS_LOCKLEVEL:  */
#define XTOS_LOCKOUT_MASK	XCHAL_INTLEVEL_ANDBELOW_MASK(XTOS_LOCKLEVEL)
/*  Mask of interrupts that can still be enabled at XTOS_LOCKLEVEL:  */
#define XTOS_UNLOCKABLE_MASK	(0xFFFFFFFF-XTOS_LOCKOUT_MASK)

/*  Don't set this:  */
#define XTOS_HIGHINT_TRAMP	0	/* mapping high-pri ints to low-pri not auto-supported */
#define XTOS_VIRTUAL_INTERRUPT	XTOS_HIGHINT_TRAMP	/* partially-virtualized INTERRUPT register not currently supported */
#if XTOS_HIGHINT_TRAMP
# error Automatically-generated high-level interrupt trampolines are not presently supported.
#endif

/*
 *  If single interrupt at level-one, sub-prioritization is irrelevant:
 */
#if defined(XCHAL_INTLEVEL1_NUM)
# undef XTOS_SUBPRI
# define XTOS_SUBPRI 0			/* override - only one interrupt */
#endif

/*
 *  In XEA1, the INTENABLE special register must be virtualized to provide
 *  standard XTOS functionality.
 *  In XEA2, this is only needed for software interrupt prioritization.
 */
#if XTOS_SUBPRI || XCHAL_HAVE_XEA1
#define XTOS_VIRTUAL_INTENABLE	1
#else
#define XTOS_VIRTUAL_INTENABLE	0
#endif

/*
 *  If single interrupt per priority, then fairness is irrelevant:
 */
#if (XTOS_SUBPRI && !XTOS_SUBPRI_GROUPS) || defined(XCHAL_INTLEVEL1_NUM)
# undef XTOS_INT_FAIRNESS
# define XTOS_INT_FAIRNESS	0
#endif

/*  Identify special case interrupt handling code in int-lowpri-dispatcher.S:  */
#define XTOS_INT_SPECIALCASE	(XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_HI && XTOS_INT_FAIRNESS == 0 && XTOS_SUBPRI_GROUPS == 0)

/*
 *  Determine whether to extend the interrupt entry array:
 */
#define XIE_EXTEND		(XTOS_VIRTUAL_INTENABLE && !XTOS_INT_SPECIALCASE)

/*  If we have the NSAU instruction, ordering of interrupts is reversed in _xtos_interrupt_table[]:  */
#if XCHAL_HAVE_NSA
# define MAPINT(n)	((XCHAL_NUM_INTERRUPTS-1)-(n))
# ifdef _ASMLANGUAGE
	.macro	mapint  an
	neg	\an, \an
	addi	\an, \an, XCHAL_NUM_INTERRUPTS-1
	.endm
# endif
#else /* no NSA */
# define MAPINT(n)	(n)
# ifdef _ASMLANGUAGE
	.macro	mapint  an
	.endm
# endif
#endif


#if defined(_ASMLANGUAGE) || defined(__ASSEMBLER__)

/***********   Useful macros   ***********/

/*
 *  A useful looping macro:
 *  'iterate' invokes 'what' (an instruction, pseudo-op or other macro)
 *  multiple times, passing it a numbered parameter from 'from' to 'to'
 *  inclusively.  Does not invoke 'what' at all if from > to.
 *  Maximum difference between 'from' and 'to' is 99 minus nesting depth
 *  (GNU 'as' doesn't allow nesting deeper than 100).
 */
	.macro	iterate		from, to, what
	.ifeq	((\to-\from) & ~0xFFF)
	\what	\from
	iterate	"(\from+1)", \to, \what
	.endif
	.endm	// iterate



	//  rsilft
	//
	//  Execute RSIL \ar, \tolevel if \tolevel is different than \fromlevel.
	//  This way the RSIL is avoided if we know at assembly time that
	//  it will not change the level.  Typically, this means the \ar register
	//  is ignored, ie. RSIL is used only to change PS.INTLEVEL.
	//
	.macro	rsilft	ar, fromlevel, tolevel
#if XCHAL_HAVE_INTERRUPTS
	.if \fromlevel - \tolevel
	rsil	\ar, \tolevel
	.endif
#endif
	.endm


	//  Save LOOP and MAC16 registers, if configured, to the exception stack
	//  frame pointed to by address register \esf, using \aa and \ab as temporaries.
	//
	//  This macro essentially saves optional registers that the compiler uses by
	//  default when present.
	//  Note that the acclo/acchi subset of MAC16 may be used even if others
	//  multipliers are present (e.g. mul16, mul32).
	//
	//  Only two temp registers required for this code to be optimal (no interlocks) in both
	//  T10xx (Athens) and Xtensa LX microarchitectures (both 5 and 7 stage pipes):
	//
	.macro	save_loops_mac16	esf, aa, ab
#if XCHAL_HAVE_LOOPS
	rsr	\aa, LCOUNT
	rsr	\ab, LBEG
	s32i	\aa, \esf, UEXC_lcount
	rsr	\aa, LEND
	s32i	\ab, \esf, UEXC_lbeg
	s32i	\aa, \esf, UEXC_lend
#endif
#if XCHAL_HAVE_MAC16
	rsr	\aa, ACCLO
	rsr	\ab, ACCHI
	s32i	\aa, \esf, UEXC_acclo
	s32i	\ab, \esf, UEXC_acchi
# if XTOS_SAVE_ALL_MAC16
	rsr	\aa, M0
	rsr	\ab, M1
	s32i	\aa, \esf, UEXC_mr + 0
	s32i	\ab, \esf, UEXC_mr + 4
	rsr	\aa, M2
	rsr	\ab, M3
	s32i	\aa, \esf, UEXC_mr + 8
	s32i	\ab, \esf, UEXC_mr + 12
# endif
#endif
	.endm

	//  Restore LOOP and MAC16 registers, if configured, from the exception stack
	//  frame pointed to by address register \esf, using \aa, \ab and \ac as temporaries.
	//
	//  Three temp registers are required for this code to be optimal (no interlocks) in
	//  Xtensa LX microarchitectures with 7-stage pipe; otherwise only two
	//  registers would be needed.
	//
	.macro	restore_loops_mac16	esf, aa, ab, ac
#if XCHAL_HAVE_LOOPS
	l32i	\aa, \esf, UEXC_lcount
	l32i	\ab, \esf, UEXC_lbeg
	l32i	\ac, \esf, UEXC_lend
	wsr	\aa, LCOUNT
	wsr	\ab, LBEG
	wsr	\ac, LEND
#endif
#if XCHAL_HAVE_MAC16
	l32i	\aa, \esf, UEXC_acclo
	l32i	\ab, \esf, UEXC_acchi
# if XTOS_SAVE_ALL_MAC16
	l32i	\ac, \esf, UEXC_mr + 0
	wsr	\aa, ACCLO
	wsr	\ab, ACCHI
	wsr	\ac, M0
	l32i	\aa, \esf, UEXC_mr + 4
	l32i	\ab, \esf, UEXC_mr + 8
	l32i	\ac, \esf, UEXC_mr + 12
	wsr	\aa, M1
	wsr	\ab, M2
	wsr	\ac, M3
# else
	wsr	\aa, ACCLO
	wsr	\ab, ACCHI
# endif
#endif
	.endm


/*  Offsets from _xtos_intstruct structure:  */
	.struct 0
#if XTOS_VIRTUAL_INTENABLE
XTOS_ENABLED_OFS:	.space	4	/* _xtos_enabled variable */
XTOS_VPRI_ENABLED_OFS:	.space	4	/* _xtos_vpri_enabled variable */
#endif
#if XTOS_VIRTUAL_INTERRUPT
XTOS_PENDING_OFS:	.space	4	/* _xtos_pending variable */
#endif
	.text


#if XTOS_VIRTUAL_INTENABLE
	// Update INTENABLE register, computing it as follows:
	//	INTENABLE = _xtos_enabled & _xtos_vpri_enabled
	// 			[ & ~_xtos_pending ]
	//
	// Entry:
	//	register ax = &_xtos_intstruct
	//	register ay, az undefined (temporaries)
	//	PS.INTLEVEL set to XTOS_LOCKLEVEL or higher (eg. via xtos_lock)
	//	window overflows prevented (PS.WOE=0, PS.EXCM=1, or overflows
	//		already done for registers ax, ay, az)
	//
	// Exit:
	//	registers ax, ay, az clobbered
	//	PS unchanged
	//	caller needs to SYNC (?) for INTENABLE changes to take effect
	//
	// Note: in other software prioritization schemes/implementations,
	// the term <_xtos_vpri_enabled> in the above expression is often
	// replaced with another expression that computes the set of
	// interrupts allowed to be enabled at the current software virtualized
	// interrupt priority.
	//
	// For example, a simple alternative implementation of software
	// prioritization for XTOS might have been the following:
	//	INTENABLE = _xtos_enabled & (vpri_enabled | UNLOCKABLE_MASK)
	// which removes the need for the interrupt dispatcher to 'or' the
	// UNLOCKABLE_MASK bits into _xtos_vpri_enabled, and lets other code
	// disable all lockout level interrupts by just clearing _xtos_vpri_enabled
	// rather than setting it to UNLOCKABLE_MASK.
	// Other implementations sometimes use a table, eg:
	//	INTENABLE = _xtos_enabled & enable_table[current_vpri]
	// The HAL (used by some 3rd party OSes) uses essentially a table-driven
	// version, with other tables enabling run-time changing of priorities.
	//
	.macro	xtos_update_intenable	ax, ay, az
	//movi	\ax, _xtos_intstruct
	l32i	\ay, \ax, XTOS_VPRI_ENABLED_OFS		// ay = _xtos_vpri_enabled
	l32i	\az, \ax, XTOS_ENABLED_OFS		// az = _xtos_enabled
	//interlock
	and	\az, \az, \ay		// az = _xtos_enabled & _xtos_vpri_enabled
# if XTOS_VIRTUAL_INTERRUPT
	l32i	\ay, \ax, XTOS_PENDING_OFS		// ay = _xtos_pending
	movi	\ax, -1
	xor	\ay, \ay, \ax		// ay = ~_xtos_pending
	and	\az, \az, \ay		// az &= ~_xtos_pending
# endif
	wsr	\az, INTENABLE
	.endm
#endif /* VIRTUAL_INTENABLE */

	.macro	xtos_lock	ax
	rsil    \ax, XTOS_LOCKLEVEL	// lockout
	.endm

	.macro	xtos_unlock	ax
	wsr     \ax, PS			// unlock
	rsync
	.endm

/*  Offsets to XtosIntHandlerEntry structure fields (see below):  */
# define XIE_HANDLER	0
# define XIE_ARG	4
# define XIE_SIZE	8
# if XIE_EXTEND
#  define XIE_VPRIMASK	(XIE_SIZE*XCHAL_NUM_INTERRUPTS+0)	/* if VIRTUAL_INTENABLE [SUBPRI||XEA1] && !SPECIALCASE */
#  define XIE_LEVELMASK	(XIE_SIZE*XCHAL_NUM_INTERRUPTS+4)	/* [fairness preloop]  if FAIRNESS && SUBPRI [&& SUBPRI_GROUPS] */
# endif

/*  To simplify code:  */
# if XCHAL_HAVE_NSA
#  define IFNSA(a,b)	a
# else
#  define IFNSA(a,b)	b
# endif

#else /* !_ASMLANGUAGE && !__ASSEMBLER__ */

/*
 *  Interrupt handler table entry.
 *  Unregistered entries have 'handler' point to _xtos_unhandled_interrupt().
 */
typedef struct XtosIntHandlerEntry {
    _xtos_handler	handler;
    void *		arg;
} XtosIntHandlerEntry;
# if XIE_EXTEND
typedef struct XtosIntMaskEntry {
    unsigned		vpri_mask;	/* mask of interrupts enabled when this interrupt is taken */
    unsigned		level_mask;	/* mask of interrupts at this interrupt's level */
} XtosIntMaskEntry;
# endif

#endif /* !_ASMLANGUAGE && !__ASSEMBLER__ */

/*
 *  Notes...
 *
 *  XEA1 and interrupt-SUBPRIoritization both imply virtualization of INTENABLE.
 *  Synchronous trampoloines imply partial virtualization of the INTERRUPT
 *  register, which in turn also implies virtualization of INTENABLE register.
 *  High-level interrupts manipulating the set of enabled interrupts implies
 *  at least a high XTOS_LOCK_LEVEL, although not necessarily INTENABLE virtualization.
 *
 *  With INTENABLE register virtualization, at all times the INTENABLE
 *  register reflects the expression:
 *	(set of interrupts enabled) & (set of interrupts enabled by current
 *					virtual priority)
 *
 *  Unrelated (DBREAK semantics):
 *
 *	A[31-6] = DBA[3-6]
 *	---------------------
 *	A[5-0] & DBC[5-C] & szmask
 *
 *	= DBA[5-0] & szmask
 *			^___  ???
 */


/*  Report whether the XSR instruction is available (conservative):  */
#define HAVE_XSR	(XCHAL_HAVE_XEA2 || !XCHAL_HAVE_EXCEPTIONS)
/*
 *  This is more accurate, but not a reliable test in software releases prior to 6.0
 *  (where the targeted hardware parameter was not explicit in the XPG):
 *
 *#define HAVE_XSR	(XCHAL_HW_MIN_VERSION >= XTENSA_HWVERSION_T1040_0)
 */



/* Macros for supporting hi-level and medium-level interrupt handling. */

#if XCHAL_NUM_INTLEVELS > 6
#error Template files (*-template.S) limit support to interrupt levels <= 6
#endif

#if  defined(__XTENSA_WINDOWED_ABI__) && XCHAL_HAVE_CALL4AND12 == 0
#error CALL8-only is not supported!
#endif

#define INTERRUPT_IS_HI(level)  \
	( XCHAL_HAVE_INTERRUPTS && \
	 (XCHAL_EXCM_LEVEL < level) && \
	 (XCHAL_NUM_INTLEVELS >= level) && \
	 (XCHAL_HAVE_DEBUG ? XCHAL_DEBUGLEVEL != level : 1))

#define INTERRUPT_IS_MED(level) \
	(XCHAL_HAVE_INTERRUPTS && (XCHAL_EXCM_LEVEL >= level))


#define _JOIN(x,y)	x ## y
#define JOIN(x,y)	_JOIN(x,y)

#define _JOIN3(a,b,c)	a ## b ## c
#define JOIN3(a,b,c)	_JOIN3(a,b,c)

#define LABEL(x,y)		JOIN3(x,_INTERRUPT_LEVEL,y)
#define EXCSAVE_LEVEL		JOIN(EXCSAVE_,_INTERRUPT_LEVEL)
#define INTLEVEL_VSIZE		JOIN3(XSHAL_INTLEVEL,_INTERRUPT_LEVEL,_VECTOR_SIZE)



#endif /* XTOS_INTERNAL_H */

