// Level-one interrupt dispatcher (user vectored handler)

// Copyright (c) 1999-2010 Tensilica Inc.
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
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"
#include "interrupt-pri.h"

#if XCHAL_HAVE_EXCEPTIONS && XCHAL_HAVE_INTERRUPTS


	/*
	 *  Macros to slightly reduce the number of #if statements in the code:
	 */

/*  This is set (for #if only) if there is only ONE interrupt configured at level one:  */
# define XTOS_SINGLE_INT	defined(XCHAL_INTLEVEL1_NUM)

/*  Simplify the #if's around saving and restoring of SAR ('#' is a comment char):  */
# if ((XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_LO) || (XTOS_INT_FAIRNESS && XTOS_SUBPRI)) && !XTOS_SINGLE_INT
#  define NEEDSAR		/* need SAR saved early w/ints locked */
#  define LATESAR	#	/* need SAR saved late w/ints unlocked */
# else
#  define NEEDSAR	#	/* need SAR saved early w/ints locked */
#  define LATESAR		/* need SAR saved late w/ints unlocked */
# endif

/*  Simplify the #if's around fairness-specific code ('#' is a comment char):  */
# if XTOS_INT_FAIRNESS
#  define IFFAIR		/* for code enabled only for fairness */
#  define NOFAIR	#	/* for code enabled only without fairness */
# else
#  define IFFAIR	#	/* for code enabled only for fairness */
#  define NOFAIR		/* for code enabled only without fairness */
# endif


	//  NOTE:  something equivalent to the following vector is executed
	//  before entering this handler (see user-vector.S).
//_UserExceptionVector:
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

	.text
	.align	4
	.global	_xtos_l1int_handler
_xtos_l1int_handler:
	//  HERE:  a2, a3, a4 have been saved to exception stack frame allocated with a1 (sp).

	s32i	a5, a1, UEXC_a5		// a5 will get clobbered by ENTRY after pseudo-CALL4
					//   (a4..a15 spilled as needed; save if modified)

# if XCHAL_HAVE_XEA2

	//  Set PS fields:
	//	EXCM     = 0
	//	WOE      = __XTENSA_CALL0_ABI__ ? 0 : 1
	//	UM       = 1
	//	INTLEVEL = EXCM_LEVEL
	//	CALLINC  = __XTENSA_CALL0_ABI__ ? 0 : 1
	//	OWB      = 0  (actual value is a don't care)

#  ifdef __XTENSA_CALL0_ABI__
	movi	a2, PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)
#  else
	movi	a2, PS_UM|PS_INTLEVEL(XCHAL_EXCM_LEVEL)|PS_WOE|PS_CALLINC(1)	// CALL4 emulation
#  endif
	rsr	a3, EPC_1
	xsr	a2, PS

#  ifdef __XTENSA_WINDOWED_ABI__
	//  HERE:  window overflows enabled, but NOT SAFE because we're not quite
	//	in a valid windowed context (haven't restored a1 yet);
	//	so don't cause any (by accessing only a0..a3) until we've saved critical state
	//	and restored a1 (note: critical state already saved in a2 and a3):
	//  NOTE:  saved EPC1 before causing any overflows, because overflows corrupt EPC1.
#  endif

	s32i	a3, a1, UEXC_pc
	s32i	a2, a1, UEXC_ps

# else /*if XEA1:*/

	//  Would need to save & clear LCOUNT only with protection.  None here.
	//  No need to save EXCVADDR or EXCCAUSE for low-priority interrupts.
#  if 1
	rsr	a2, INTERRUPT			// read INTERRUPT while PS.INTLEVEL is 1 and INTENABLE is intact
	rsilft	a3, 1, XTOS_LOCKLEVEL		// lockout
	s32i	a2, a1, UEXC_vpri		// save for interrupt computation
	rsr	a2, INTENABLE
	movi	a3, XTOS_UNLOCKABLE_MASK	// mask out level one, and high levels covered by XTOS_LOCKLEVEL if any,
						//  so we can run at PS.INTLEVEL=0 while manipulating INTENABLE
	s32i	a2, a1, UEXC_sar		// save old INTENABLE, to handle the spurious interrupt case
	and	a3, a2, a3			// mask out selected interrupts
	wsr	a3, INTENABLE			// disable all interrupts up to and including XTOS_LOCKLEVEL
#  else
	//  Using this alternate code requires extensive changes elsewhere;
	//  its only advantage is potentially lowered latency of interrupts
	//  of priority levels 2 thru XTOS_LOCKLEVEL:
	movi	a2, _xtos_intstruct		// address of interrupt management globals
	rsilft	a3, 1, XTOS_LOCKLEVEL		// lockout
	l32i	a3, a2, XTOS_VPRI_ENABLED_OFS	// read previous _xtos_vpri_enabled
	//interlock
	s32i	a3, a1, UEXC_vpri		// save previous vpri
	movi	a3, ~XCHAL_EXCM_MASK		// mask out all low-priority interrupts
						//  so we can run at PS.INTLEVEL=0 while ESF allocation not reflected in SP
	//interlock
	s32i	a3, a2, XTOS_VPRI_ENABLED_OFS	// set new _xtos_vpri_enabled (mask all low-priority interrupts)
	l32i	a2, a2, XTOS_ENABLED_OFS	// read _xtos_enabled
	//interlock
	and	a3, a2, a3			// mask out selected interrupts
	wsr	a3, INTENABLE			// disable all low-priority interrupts
#  endif
	movi	a3, PS_WOE|PS_CALLINC(1)|PS_UM	// WOE=1, UM=1, INTLEVEL=0, CALLINC=1 (call4 emul), OWB=(dontcare)=0

	//  NOTE:  could use XSR here if targeting T1040 or T1050 hardware (requiring slight sequence adjustment as for XEA2):
	rsr	a2, PS
	rsync	//NOT-ISA-DEFINED		// wait for WSR to INTENABLE to complete before clearing PS.INTLEVEL
	wsr	a3, PS				// PS.INTLEVEL=0, effective INTLEVEL (via INTENABLE) is XTOS_LOCKLEVEL (NOTA: LOWPRI_LEVELS)

	//  HERE:  window overflows enabled, but NOT SAFE because we're not quite
	//	in a valid windowed context (haven't restored a1 yet...);
	//	so don't cause any (keep to a0..a3) until we've saved critical state and restored a1:

	//  NOTE:  MUST SAVE EPC1 before causing any overflows, because overflows corrupt EPC1.
	rsr	a3, EPC_1
	s32i	a2, a1, UEXC_ps
	s32i	a3, a1, UEXC_pc

# endif /* XEA1 */


# ifdef __XTENSA_CALL0_ABI__

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

# else  /* ! __XTENSA_CALL0_ABI__ */

#  if XTOS_CNEST
	l32i	a2, a1, ESF_TOTALSIZE-20	// save nested-C-func call-chain ptr
#  endif
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
	 *	The pseudo-CALL below effectively saves registers a2..a3
	 *	so that they are available again after the corresponding
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

#  if XTOS_DEBUG_PC
	movi	a4, 0xC0000000		// [for debug] for return PC computation below
	or	a3, a4, a3		// [for debug] set upper two bits of return PC
	addx2	a4, a4, a3		// [for debug] clear upper bit
#  else
	movi	a4, 0			// entry cannot cause overflow, cause it here
#  endif

	.global	_LevelOneInterrupt
_LevelOneInterrupt:			// this label makes tracebacks through interrupts look nicer

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
	 */

#  if 0 /*... non-nested interrupt ...*/
	mov	...some address register..., a1		// save ptr to original ESF
	movi	a1, _interrupt_stack			// switch stack
#  endif

# endif /* __XTENSA_CALL0_ABI__ */

	/*
	 *  Now we can enable interrupts of higher virtual priority than the one(s)
	 *  being dispatched/processed here.  This may entail some software prioritization,
	 *  if so configured.
	 *  (Pseudo-CALL is complete, and SP reflects allocation of exception stack frame
	 *  or switch to new stack.)
	 */

# if XCHAL_HAVE_XEA2
	rsilft	a15, XCHAL_EXCM_LEVEL, 1	// INTERRUPT reg *must* be read at PS.INTLEVEL<=1
						// (otherwise it might get higher pri ints)
#  define CUR_INTLEVEL	1
# else
#  define CUR_INTLEVEL	0
# endif
	/*  At this point, PS.INTLEVEL is:  0 if XEA1, 1 if XEA2  (per CUR_INTLEVEL)  */


	/*****************  Dispatch low-priority interrupts to service  *****************/

	/* HERE: We may get up to 3 window overflows on the following instruction.
	 *
	 *    The worst case is 3 overflows, two 4-register overflows and one
	 *    12-register overflow.
	 */


# if XTOS_VIRTUAL_INTENABLE
	/*
	 *  The INTENABLE register is virtualized, because it serves two purposes:
	 *  controlling which interrupts are active (eg. enabled once a handler
	 *  is registered) as reflected in _xtos_enabled, and what is the current
	 *  effective interrupt level as reflected in _xtos_vpri_enabled.
	 *
	 *  The INTENABLE register always contains (_xtos_enabled & _xtos_vpri_enabled).
	 *  NOTE:  It is important that INTENABLE, _xtos_enabled and _xtos_vpri_enabled
	 *  only be modified when interrupts at XTOS_LOCK_LEVEL and below are disabled,
	 *  that they never be modified by interrupts at levels above XTOS_LOCK_LEVEL,
	 *  and that they be consistent and never modified when the current interrupt
	 *  level is below XTOS_LOCK_LEVEL.
	 *
	 *  NOTE:  Reading the INTERRUPT register *must* be done at PS.INTLEVEL <= 1
	 *  otherwise we might incorrectly see higher priority interrupts.
	 */


	movi	a14, _xtos_intstruct		// address of interrupt management globals
#  if XCHAL_HAVE_XEA1
	l32i	a15, a1, UEXC_vpri		// read saved INTERRUPT register value
	l32i	a13, a14, XTOS_VPRI_ENABLED_OFS	// read previous _xtos_vpri_enabled
	l32i	a12, a14, XTOS_ENABLED_OFS	// read _xtos_enabled
	and	a15, a15, a13			// don't handle ints already being handled
#  else
	rsr	a15, INTERRUPT			// interrupts pending
	rsr	a12, INTENABLE			// interrupts enabled (already should equal _xtos_enabled & _xtos_vpri_enabled)
	l32i	a13, a14, XTOS_VPRI_ENABLED_OFS	// read previous _xtos_vpri_enabled
#  endif
	and	a15, a15, a12			// a15 = INTERRUPT & (interrupts we can consider processing)
NEEDSAR	rsr	a12, SAR
	s32i	a13, a1, UEXC_vpri		// save previous vpri

	_beqz	a15, spurious_int		// no interrupt to handle (spurious interrupt)
NEEDSAR	s32i	a12, a1, UEXC_sar		// note: in XEA1, UEXC_sar must be set *after* beqz above

IFFAIR	s32i	a2, a1, UEXC_exccause		// save a2 (interrupted code's a6)
IFFAIR	movi	a2, -1				// initial fairness mask

.L1_loop0:
	//  a15 = non-zero mask of interrupt bits to consider handling

#  if XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_HI && !XTOS_INT_FAIRNESS && !XTOS_SUBPRI_GROUPS
	//  Special case that can be handled a bit more efficiently:

	neg	a12, a15			// find lsbit in a15 ...
	and	a12, a12, a15			// ...
	//  a12 = single bit corresponding to interrupt to be processed (highest pri pending+enabled).

	//  Compute a13 = new virtual priority based on this selected highest priority interrupt:
	movi	a15, ~XCHAL_LOWPRI_MASK		// mask of all low-priority interrupts
	addi	a13, a12, -1			// mask of interrupts enabled at this new priority
	or	a13, a13, a15			// also leave medium- and high-priority interrupts enabled

#  else /* special case */

	//  Entry:
	//	a12 = (undefined)
	//	a13 = (undefined)
	//	a14 = &_xtos_intstruct  --or--  interrupt table adjusted base
	//	a15 = non-zero mask of interrupt bits to consider handling
	//  Exit:
	//	a12 = index
	//	a13 = (clobbered)
	//	a14 = (preserved)
	//	a15 = single bit corresponding to index
	//
	indexmask_int	a12, a15, a14, a13

	//  a12 = index of highest priority pending+enabled interrupt, to be processed.
	//  a15 = (1 << a12), ie. bit corresponding to interrupt to be processed.
IFFAIR	xor	a2, a2, a15		// update fairness mask - mask out this interrupt until recycling mask
	movi	a13, _xtos_interrupt_table - IFNSA( (32-XCHAL_NUM_INTERRUPTS)*XIE_SIZE, 0 )
	wsr	a15, INTCLEAR		// clear interrupt (if software or external edge-triggered or write-error)
	addx8	a12, a12, a13		// a12 = address in interrupt table for given interrupt number

.L1_loop1:
	//  a12 now contains pointer to interrupt table entry for interrupt to be processed
	l32i	a13, a12, XIE_VPRIMASK	// a13 = new vpri (mask of interrupts enabled at this interrupt's priority)
#  endif /* !special case */

	//  a13 = new virtual priority based on the selected highest priority interrupt

	rsilft	a15, 1*XCHAL_HAVE_XEA2, XTOS_LOCKLEVEL	// lockout

	//  Now do the equivalent of:   prev = _xtos_set_vpri( a13 );

	l32i	a15, a14, XTOS_ENABLED_OFS	// a15 = _xtos_enabled
	s32i	a13, a14, XTOS_VPRI_ENABLED_OFS	// update new _xtos_vpri_enabled
	and	a15, a15, a13			// a15 = _xtos_enabled & _xtos_vpri_enabled
	//NOTE: Here, do:  a15 &= ~_xtos_pending  if XTOS_VIRTUAL_INTERRUPT is set.
	wsr	a15, INTENABLE
	//interlock
	//interlock
	rsync	// NOTA - not ISA defined	// wait for INTENABLE write to complete before we set PS.INTLEVEL to zero


	//  Okay, we've updated INTENABLE to reflect the new virtual priority (vpri)
	//  according to the highest priority pending+enabled (low-priority) interrupt.

	//  IMPLEMENTATION NOTE - Before we unlock (enable interrupts), we could
	//  switch stacks here, now that we have enough free registers through the unlock.

	//  Now we can enable interrupts via PS.INTLEVEL.  (Already done for XEA1.)

	rsil	a15, 0				// unlock
#  undef CUR_INTLEVEL
#  define CUR_INTLEVEL	0

	//  HERE:  interrupts are enabled again (those interrupts of
	//	higher virtual priority than the one we're currently processing).

	//  HERE:
	//	a12 = pointer to interrupt entry in table, or
	//		mask of interrupt bit to process (special case only)
	//	a13, a15 = available for use
	//	a14 = available for use if virtual INTENABLE, else is pointer to interrupt table

#  if XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_HI && !XTOS_INT_FAIRNESS && !XTOS_SUBPRI_GROUPS
	/*  In this special case, we moved as much as possible where interrupts are enabled again:  */
	//  a12 is bit corresponding to interrupt, convert to ptr to interrupt table entry...
	movi		a14, _xtos_interrupt_table - IFNSA( (32-XCHAL_NUM_INTERRUPTS)*XIE_SIZE, 0 )
	wsr		a12, INTCLEAR	// clear interrupt (if software or external edge-triggered or write-error)
//IFFAIR	xor	a2, a2, a12	// update fairness mask - mask out this interrupt until recycling mask
	msindex_int	a15, a12	// a15 = index of msbit set in a12 (a12 clobbered)
	addx8		a12, a15, a14	// a12 = address in interrupt table for given interrupt number
#  endif /* special case */



# elif XTOS_SINGLE_INT
	/*
	 *  Only one interrupt is configured to map to this vector.
	 *  This simplifies the code considerably -- no checking and resolving of INTERRUPT
	 *  register required.  Just call the handler and exit.
	 *
	 *  (With INTENABLE register virtualization, the simplification is
	 *   not as great, and not implemented separately above.)
	 */


#  define XTOS_SINGLE_INT_NUM	XCHAL_INTLEVEL1_NUM
#  define XTOS_SINGLE_INT_MASK	XCHAL_INTLEVEL1_MASK
#  define XTOS_SINGLE_INT_CLEAR	((XTOS_SINGLE_INT_MASK & XCHAL_INTCLEARABLE_MASK) != 0)
#  if XTOS_SINGLE_INT_CLEAR
	movi	a13, XCHAL_LOWPRI_MASK		// bit to clear in INTERRUPT register
#  endif
	//  Get pointer to interrupt table entry for this vector's only interrupt:
	movi	a12, _xtos_interrupt_table + MAPINT(XTOS_SINGLE_INT_NUM)*XIE_SIZE
#  if XTOS_SINGLE_INT_CLEAR
	wsr	a13, INTCLEAR			// clear interrupt pending bit (if software or external-edge-triggered or write-error)
#  endif



# else /* ie. if !XTOS_VIRTUAL_INTENABLE && !XTOS_SINGLE_INT */
	/*
	 *  Here, the INTENABLE register is NOT virtualized.  There are no _xtos_enabled
	 *  or _xtos_vpri_enabled global variables to track.  INTENABLE simply controls
	 *  which interrupts are active (eg. enabled once a handler is registered).
	 *
	 *  NOTE:  To ensure its coherency, it is still important to only modify the
	 *  INTENABLE register when interrupts at XTOS_LOCK_LEVEL and below are disabled,
	 *  that it never be modified by interrupts at levels above XTOS_LOCK_LEVEL,
	 *  and that it never be modified when the current interrupt level is below
	 *  XTOS_LOCK_LEVEL.  This is because modifications to INTENABLE generally
	 *  require an RSR/modify/WSR sequence to modify only selected bits.
	 *
	 *  NOTE:  Reading the INTERRUPT register *must* be done at PS.INTLEVEL <= 1
	 *  otherwise we might incorrectly see higher priority interrupts.
	 *
	 *  This option implies XEA2, because XEA1 always requires INTENABLE virtualization.
	 *  This option also implies SUBPRI is zero (no interrupt sub-prioritization in software).
	 */


	rsr	a15, INTERRUPT			// interrupts pending
	rsr	a13, INTENABLE			// interrupts enabled (directly; no virtualization)
	movi	a14, _xtos_interrupt_table - IFNSA( (32-XCHAL_NUM_INTERRUPTS)*XIE_SIZE, 0 )
NEEDSAR	rsr	a12, SAR
	and	a15, a15, a13			// a15 = INTERRUPT & INTENABLE

	_beqz	a15, spurious_int		// no interrupt to handle (spurious interrupt)
NEEDSAR	s32i	a12, a1, UEXC_sar

IFFAIR	s32i	a2, a1, UEXC_exccause		// save a2 (interrupted code's a6)
IFFAIR	movi	a2, -1				// initial fairness mask

.L1_loop0:
	//  Entry:
	//	a12 = (undefined)
	//	a13 = (undefined)
	//	a14 = interrupt table adjusted base (not used here)
	//	a15 = non-zero mask of interrupt bits to consider handling
	//  Exit:
	//	a12 = index
	//	a13 = (clobbered)
	//	a14 = (preserved)
	//	a15 = single bit corresponding to index
	//
	indexmask_int	a12, a15, a14_UNUSED, a13

	//  a12 = index of highest priority pending+enabled interrupt, to be processed.
	//  a15 = (1 << a12), ie. bit corresponding to interrupt to be processed.
IFFAIR	xor	a2, a2, a15		// update fairness mask - mask out this interrupt until recycling mask
	wsr	a15, INTCLEAR		// clear interrupt (if software or external edge-triggered or write-error)

	addx8	a12, a12, a14		// a12 = address in interrupt table for given interrupt number

.L1_loop1:
	//  a12 now contains pointer to interrupt table entry for interrupt to be processed

	//  HERE:
	//	a12 = pointer to interrupt entry in table
	//	a13, a15 = available for use
	//	a14 = available for use if virtual INTENABLE, else is pointer to interrupt table


# endif /* !XTOS_VIRTUAL_INTENABLE && !XTOS_SINGLE_INT */
	/*  At this point, PS.INTLEVEL is:  1 if XEA2 and (XTOS_SINGLE_INT || !XTOS_VIRTUAL_INTENABLE), 0 otherwise  */

	//  HERE:  a12 = pointer to interrupt entry in table

	// (Possible enhancement: do at higher-level, to avoid doing it all the time? !?!?!?)
	save_loops_mac16	a1, a13, a15	// save LOOP & MAC16 regs, if configured

LATESAR	rsr	a15, SAR

# if 0
	/* ... alternate code to allow context-switching would go here ... */
# else
	l32i	a13, a12, XIE_HANDLER	// a13 = address of interrupt handler
LATESAR	s32i	a15, a1, UEXC_sar
# endif

# ifdef __XTENSA_CALL0_ABI__
	l32i	a2, a12, XIE_ARG	// first arg
	mov	a3, a1			// second arg, exception stack frame
	callx0  a13			// call interrupt handler
# else
	mov	a15, a1			// second arg, exception stack frame
	l32i	a14, a12, XIE_ARG	// first argument passed to interrupt handler (relayed by context-dispatcher, if non-nested)
	callx12	a13			// execute interrupt handler, directly or via context-dispatcher (clobbers a12-a15)
# endif

	// (Possible enhancement: do at higher-level, to avoid doing it all the time? !?!?!?)
	restore_loops_mac16	a1, a13, a14, a15	// restore LOOP & MAC16 regs, if configured

LATESAR	l32i	a12, a1, UEXC_sar


# if XTOS_VIRTUAL_INTENABLE
	/*  Here, INTENABLE register is virtualized.  */

	movi	a14, _xtos_intstruct		// address of interrupt management globals
LATESAR	wsr	a12, SAR
#  if XCHAL_HAVE_XEA1
	movi	a12, XTOS_UNLOCKABLE_MASK	// mask out levels covered by XTOS_LOCKLEVEL
						//  so we can run at PS.INTLEVEL=0 (for the RETW below)
						//  while manipulating virtual INTENABLE
#  endif
	rsr	a15, INTERRUPT
	rsil	a13, XTOS_LOCKLEVEL
	l32i	a13, a14, XTOS_ENABLED_OFS	// a13 = _xtos_enabled
#  if XCHAL_HAVE_XEA1
	and	a12, a12, a13			// compute new INTENABLE
	wsr	a12, INTENABLE			// mask out at XTOS_LOCKLEVEL via INTENABLE
#  endif
	l32i	a12, a1, UEXC_vpri		// read saved vpri
	//interlock
	and	a13, a13, a12			// a13 = old-vpri & _xtos_enabled (INTENABLE value to restore)
	and	a15, a15, a13			// what's pending among what we can handle?


	//  a15 now contains the remaining pending+enabled interrupts.
	//  NOTE:  we MUST NOT consider interrupts potentially already being handled
	//  by another interrupt handler that we pre-empted.
	//  So we masked with saved vpri, ie. the set of interrupts enabled when we entered
	//  this handler, ie. the set of interrupts that can pre-empt the previous context.
NOFAIR	_bnez	a15, .L1_loop0			// more interrupt(s) to handle
IFFAIR	_bnez	a15, preloop			// more interrupt(s) to handle
IFFAIR	l32i	a2, a1, UEXC_exccause		// restore a2 (interrupted code's a6)


	//  NOTE:
	//  Register allocation is why we didn't restore *HERE* the loop regs, MAC16, SAR, etc.
	//  (at least part of the reason)
	//  We only have one registers (a15), however with 7-stage pipe, three registers
	//  are required to avoid interlocks.  We could get 2 more registers at 1 cycle each [now only one?],
	//  but it isn't obvious whether paying these extra cycles are worth it...

	//  Restore vpri as it was before we handled the interrupt(s):
	s32i	a12, a14, XTOS_VPRI_ENABLED_OFS	// restore _xtos_vpri_enabled
NEEDSAR	l32i	a12, a1, UEXC_sar
#  if XCHAL_HAVE_XEA1
	s32i	a13, a1, UEXC_sar		// save new INTENABLE value across RETW
#  else
	wsr	a13, INTENABLE			// update INTENABLE per original vpri

	//  NOTE:  leave locked, disabling only the low- and medium-priority interrupts
	rsilft	a13, XTOS_LOCKLEVEL, XCHAL_EXCM_LEVEL	// lockout
#   undef CUR_INTLEVEL
#   define CUR_INTLEVEL	XCHAL_EXCM_LEVEL
#  endif

# elif XTOS_SINGLE_INT

#  undef NEEDSAR
#  define NEEDSAR

# else /* ie.  if !XTOS_VIRTUAL_INTENABLE && !XTOS_SINGLE_INT */
	/*  Here, INTENABLE register is NOT virtualized (implies XEA2).  */

	rsr	a15, INTERRUPT			// interrupts pending
	rsr	a13, INTENABLE			// interrupts enabled (directly; no virtualization)
	movi	a14, _xtos_interrupt_table - IFNSA( (32-XCHAL_NUM_INTERRUPTS)*XIE_SIZE, 0 )
LATESAR	wsr	a12, SAR
	and	a15, a15, a13			// a15 = INTERRUPT & INTENABLE

	//  a15 now contains the remaining pending+enabled interrupts.
	//  NOTE:  we MUST NOT consider interrupts potentially already being handled
	//  by another interrupt handler that we pre-empted.
	//  So we masked with saved vpri, ie. the set of interrupts enabled when we entered
	//  this handler, ie. the set of interrupts that can pre-empt the previous context.
NOFAIR	_bnez	a15, .L1_loop0			// more interrupt(s) to handle
IFFAIR	_bnez	a15, preloop			// more interrupt(s) to handle
IFFAIR	l32i	a2, a1, UEXC_exccause		// restore a2 (interrupted code's a6)


	//  NOTE:
	//  Register allocation is why we didn't restore *HERE* the loop regs, MAC16, SAR, etc.
	//  (at least part of the reason)
	//  We only have one registers (a15), however with 7-stage pipe, three registers
	//  are required to avoid interlocks.  We could get 2 more registers at 1 cycle each [now only one?],
	//  but it isn't obvious whether paying these extra cycles are worth it...

NEEDSAR	l32i	a12, a1, UEXC_sar
# endif /* !XTOS_VIRTUAL_INTENABLE && !XTOS_SINGLE_INT */


	/***************************/

	//  Now exit the handler.

	/*
	 *  Leave interrupts disabled while returning from the pseudo-CALL setup above,
	 *  for the same reason they were disabled while doing the pseudo-CALL:
	 *  this sequence restores SP such that it doesn't reflect the allocation
	 *  of the exception stack frame, which is still needed to return from
	 *  the exception.
	 */

spurious_int:

	movi	a0, _xtos_return_from_exc
# ifdef __XTENSA_CALL0_ABI__
NEEDSAR	wsr	a12, SAR
	jx	a0
# else /* ! __XTENSA_CALL0_ABI__ */
	//  Now return from the pseudo-CALL from the interrupted code, to rotate
	//  our windows back...

	movi	a13, 0xC0000000
NEEDSAR	wsr	a12, SAR
	or	a0, a0, a13		// set upper two bits
	addx2	a0, a13, a0		// clear upper bit

#  if XCHAL_HAVE_XEA2
	//  Disable ints during unalloc'ed live stack after RETW below.
	rsil	a13, XCHAL_EXCM_LEVEL	// might come here via spurious_int, so always rsil
#  endif

	retw
# endif /* __XTENSA_CALL0_ABI__ */



# if XTOS_INT_FAIRNESS
preloop:
	//  Lowering priority or recycling fairness-mask bits ...
	//  a14 = &_xtos_intstruct *or* interrupt table ptr
	//  a15 = non-zero mask of interrupt bits to consider handling

#  if !XTOS_SUBPRI
	and	a13, a15, a2		// a13 = interrupt bits to consider handling, masked for fairness
	movi	a12, -1			// (new fairness mask, all one's)
	moveqz	a2, a12, a13		// recycle fairness mask if all bits to consider are masked by fairness, and leave a15 intact
	movnez	a15, a13, a13		// otherwise set a15 = a13, ie. mask out bits for fairness (a15 is still non-zero)
	j	.L1_loop0
#  else /* XTOS_SUBPRI */
	//  NOTE:  In this case, with SUBPRI, XTOS_VIRTUAL_INTENABLE is always set.
	//  So:  a14 = &_xtos_intstruct

	//  Compute a13 = index of highest priority interrupt in a15 (a13 is reversed if NSA present)
	//  (a14, a15 preserved; a12 is a temporary):
	index_int	a13, a15, a14, a12

	//  a12 = (available)
	//  a13 = index
	//  a14 = &_xtos_intstruct
	//  a15 = mask of candidates
	movi	a12, _xtos_interrupt_table - IFNSA( (32-XCHAL_NUM_INTERRUPTS)*XIE_SIZE, 0 )
	//slot
	addx8	a12, a13, a12		// a12 = address in interrupt table for given interrupt number
	l32i	a14, a12, XIE_LEVELMASK	// a14 = mask of all interrupts at selected interrupt's level
	and	a15, a15, a2		// mask out for fairness
	and	a15, a15, a14		// only consider interrupts at highest pending level
	movi	a14, _xtos_intstruct	// needed at loop0, and below
	_bnez	a15, .L1_loop0		// interrupts are allowed by current fairness mask, redo indexing with proper mask (a15, a14 = ...)

	//  a12 = ptr to interrupt entry
	//  a13 = index
	//  a14 = &_xtos_intstruct
	//  a15 = (available)

	//  Compute bitmask of interrupt to be processed...
#   if XCHAL_HAVE_NSA
	movi	a15, 0x80000000
	ssr	a13
	srl	a13, a15
#   else
	movi	a15, 1
	ssl	a13
	sll	a13, a15
#   endif
	//  a13 = single bit set corresponding to interrupt to be processed...
	l32i	a15, a12, XIE_LEVELMASK	// a15 = mask of all interrupts at selected interrupt's level
	wsr	a13, INTCLEAR		// clear interrupt (if software or external edge-triggered or write-error)
	or	a2, a2, a15		// recycle fairness mask for selected interrupt level
	xor	a2, a2, a13		// update fairness mask - mask out this interrupt until recycling mask
	j	.L1_loop1		// handle selected interrupt (a12 = interrupt entry, a14 = &_xtos_intstruct)

#  endif /* XTOS_SUBPRI */
# endif /* XTOS_INT_FAIRNESS */

	/* FIXME: what about _LevelOneInterrupt ? */
	.size	_xtos_l1int_handler, . - _xtos_l1int_handler

#endif /* XCHAL_HAVE_EXCEPTIONS && XCHAL_HAVE_INTERRUPTS */

