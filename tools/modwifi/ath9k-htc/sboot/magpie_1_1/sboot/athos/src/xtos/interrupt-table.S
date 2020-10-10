// interrupt-table.S - Interrupt handler table and default handler

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

#include <xtensa/coreasm.h>
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"
#ifdef SIMULATOR
#include <xtensa/simcall.h>
#endif


#if XCHAL_HAVE_INTERRUPTS

	.data

	.global	_xtos_intstruct
	.align	8
_xtos_intstruct:
# if XTOS_VIRTUAL_INTENABLE
	.global	_xtos_enabled
	.type	_xtos_enabled,@object
	.size	_xtos_enabled,4
	.global	_xtos_vpri_enabled
	.type	_xtos_vpri_enabled,@object
	.size	_xtos_vpri_enabled,4
_xtos_enabled:		.word	0
_xtos_vpri_enabled:	.word	0xFFFFFFFF
# endif
# if XTOS_VIRTUAL_INTERRUPT
#  error Virtualized INTERRUPT register not yet supported.
	.global	_xtos_pending
	.type	_xtos_pending,@object
	.size	_xtos_pending,4
_xtos_pending:		.word	0
# endif

	/*
	 *  Table of C-level interrupt handlers (and args, etc) for each interrupt.
	 *  NOTE:  if the NSA/NSAU instructions are configured, then to save a few
	 *  cycles in the interrupt dispatcher code, this table is filled in reverse.
	 *  C code uses the MAPINT() macro defined in xtos-internal.h to index entries.
	 *  NOTE:  Under some conditions (turned off by default in xtos-params.h),
	 *  this table gets properly initialized by the _xtos_init() function in
	 *  init.c .  NOTA:  A future enhancement may be to always configure
	 *  and build this table at build-time rather than ever doing it at run-time.
	 */
#define i	.Li	/* workaround a silly GDB testsuite regression */
	.data
	.global	_xtos_interrupt_table
	.align	8
_xtos_interrupt_table:
	.set	i, XCHAL_HAVE_NSA*(XCHAL_NUM_INTERRUPTS-1)
	.rept	XCHAL_NUM_INTERRUPTS
	 .word	_xtos_unhandled_interrupt
	 .word	i			// parameter: interrupt number
	 .set	i, i+1-(XCHAL_HAVE_NSA*2)
	.endr

# if XIE_EXTEND
	/*  MUST *IMMEDIATELY* follow _xtos_interrupt_table:  */
	.global	_xtos_interrupt_mask_table
_xtos_interrupt_mask_table:
	.set	i, XCHAL_HAVE_NSA*(XCHAL_NUM_INTERRUPTS-1)
	.rept	XCHAL_NUM_INTERRUPTS
	/*  Default to all low-priority (level-one) interrupts at their own virtual priority:  */
#  if XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_HI
	 .word	((1<<i)-1) | ~XCHAL_LOWPRI_MASK	// vpri_mask default - lower-numbered ints (and high/medium-pri ints) pre-empt other low-pri ints
#  else
	 .word	(-2*(1<<i)) | ~XCHAL_LOWPRI_MASK // vpri_mask default - higher-numbered ints (and high/medium-pri ints) pre-empt other low-pri ints
#  endif
	 .word	(1<<i)		// level_mask default - each low-pri (level-one) interrupt at its own subpriority
	 .set	i, i+1-(XCHAL_HAVE_NSA*2)
	.endr
# endif /*XIE_EXTEND*/

#endif /* XCHAL_HAVE_INTERRUPTS */

	.text



#if XCHAL_HAVE_INTERRUPTS

	//
	// void _xtos_unhandled_interrupt( int n );
	// 
	//  Default/empty interrupt handler.
	//  This is used for interrupts with no registered handler.
	//  Parameter n is the interrupt number (0 thru 31).
	//
	.text 
	.align 4 
	.global _xtos_unhandled_interrupt
	.type _xtos_unhandled_interrupt,@function
_xtos_unhandled_interrupt:
	abi_entry
# if XCHAL_HAVE_DEBUG
	//  Break into the debugger if one is present and active:
#  if XCHAL_NUM_INTLEVELS > XCHAL_DEBUGLEVEL
	rsil	a3, XCHAL_DEBUGLEVEL-1	// ensure break takes effect
#  endif
	break	1, 15		// unhandled (unregistered) interrupt $a2
//# elif defined(SIMULATOR)
//	addmi	a2, a2, SYS_unhandled_interrupt ...
//	simcall			// unhandled interrupt
# else
1:	j	1b		// unhandled interrupt - loop forever
# endif
	abi_return

	.size	_xtos_unhandled_interrupt, . - _xtos_unhandled_interrupt

#endif /* XCHAL_HAVE_INTERRUPTS */

