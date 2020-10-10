// High-Priority Interrupt Handler Template
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/int-highpri-template.S#3 $

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
// This file provides skeleton code for writing high-priority interrupt
// handlers in assembler for performance.
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
#define SINGLE_INTERRUPT	(INTERRUPT_MASK & (INTERRUPT_MASK - 1) == 0)
#define SINGLE_INT_NUM		XCHAL_INTLEVEL_NUM(_INTERRUPT_LEVEL)


//  NOTE:  It is strongly recommended that high-priority
//  interrupt handlers be written in assembly.
//
//  High-priority interrupt handlers can be written in C,
//  but only at the cost of an unreasonable amount of state
//  save and restore (including the entire physical address
//  register file and others, see int-highpri-dispatcher.S)
//  that makes high-priority interrupt dispatching much slower
//  than for low and medium priority interrupts.
//  (Low and medium priority interrupts are masked by atomic
//   register window operations, so they take advantage of a
//   coherent window state for fast entry.  High priority
//   interrupts are not masked by window operations so they
//   can interrupt them, leading to a potentially incoherent
//   window state at the time of the interrupt.  Given that
//   high priority handlers must save and restore everything
//   they touch, they end up needing to save and restore the
//   entire window state [physical address register file etc.]
//   and all exception state which they can also interrupt.)
//  See also the Microprocessor Programmer's Guide.

//  High-priority interrupts are designed to be very fast and with
//  very low latency.
//  Typical high-priority interrupt service routines are kept
//  relatively small and fast.  Either there is little to do,
//  or the routine handles only the necessary high priority
//  activities related to a device and leaves the rest
//  (other more complex and time-consuming activities)
//  to be scheduled later, eg. by triggering a level-one
//  (low-priority) or medium-priority software interrupt whose
//  handler can be written in C for the more extensive processing.

//  NOTE:  The following handler is just skeleton example
//  code.  It is NOT a functional handler.  For software, edge-
//  triggered and write-error interrupts, it simply does nothing
//  and return.  For other types (timer and level-triggered),
//  this code does not clear the source(s) of interrupt,
//  hence if any interrupt at this priority level are both enabled
//  and triggered, the processor repeatedly takes the interrupt
//  in a loop.  This is all okay as a default, because
//  XTOS (and other operating systems) clears the INTENABLE
//  register at startup, requiring the application to
//  enable specific interrupts before they can be taken.
//  So as long as you don't enable any interrupt of this
//  priority level, this example handler will never execute.

// Exports
.global	LABEL(_Level,FromVector)

	.data
	.align	4
LABEL(int,save):
	.space	4	// save area

	.text
	.align	4
LABEL(_Level,FromVector):
	//  The vectoring code has already saved a2 in EXCSAVEn.
	//  Save any other registers we'll use:
	movi	a2, LABEL(int,save)
	s32i	a1, a2, 0
	//  ... add more as needed (increase save area accordingly) ...

	//  WRITE YOUR INTERRUPT HANDLING CODE HERE...

	//  If multiple interrupts are mapped to this priority level,
	//  you'll probably need to distinguish which interrupt(s)
	//  occurred by reading the INTERRUPT (INTREAD) and
	//  INTENABLE registers, and'ing them together, and
	//  looking at what bits are set in both.
	//  If any of the interrupts are level-triggered, be ready
	//  to handle the case where no interrupts are to be handled
	//  -- this is called a spurious interrupt, and can happen
	//  when the level-triggered interrupt line goes inactive
	//  after the interrupt is taken but before the INTERRUPT
	//  register is read.

	//  You'll also normally want to clear the source of
	//  the interrupt before returning, to avoid getting
	//  the same interrupt again immediately.  For illustration,
	//  this code clears all software, edge-triggered, and
	//  write-error interrupts at this priority level (if any).
	//  NOTE: Timer interrupts must be cleared by writing to
	//  the corresponding CCOMPAREn register; and level-sensitive
	//  interrupts can only be cleared externally, usually by
	//  requesting the associated device to do so (in a
	//  device-specific manner).
	//
	movi	a1, INTERRUPT_MASK
	wsr	a1, INTCLEAR

	//  Restore registers:
	l32i	a1, a2, 0
#if HAVE_XSR
	movi	a2, LABEL(_Level,FromVector)	// restore handler address
	xsr	a2, EXCSAVE_LEVEL
#else
	rsr	a2, EXCSAVE_LEVEL
#endif
	//  ... add more if more are saved above ...

	//  Return:
	rfi	_INTERRUPT_LEVEL

	.size	LABEL(_Level,FromVector), . - LABEL(_Level,FromVector)

#endif /* XCHAL_HAVE_INTERRUPTS */
