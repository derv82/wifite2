// crt0-app.S
// Applications downloaded in RAM using a debug monitor (eg. XMON, RedBoot)
// start here at _app_reset.  Such applications don't have any vectors:
// all exceptions are handled by the debug monitor.
// Thus, this file essentially plays the role of the reset vector
// to setup a few things before jumping to _start (in crt1*.S).

// Copyright (c) 2005-2010 Tensilica Inc.
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

#include <xtensa/cacheattrasm.h>
#include <xtensa/xt2000.h>
#include <xtensa/coreasm.h>


//  Assumptions on entry to _app_reset:
//	- debug monitor handles all exceptions, has setup all vectors
//	- interrupt related state is initialized
//	  (interrupts disabled or enabled for debug monitor's purposes)
//	- debug option related state is initialized (for debug monitor)
//	- any MMU related state is initialized (all handled by debug monitor)
//	- caches are initialized (cache attributes not necessarily correct)
//	- entire application is loaded (no unpacking needed here)

//  Assumptions on exit from _app_reset, ie. when jumping to _start:
//	- low (level-one) and medium priority interrupts are disabled
//	- C calling context not initialized:
//	  - PS not fully initialized (eg. PS.WOE not set per ABI)
//	  - SP not initialized
//	- the following are initialized:
//	  - LITBASE, WindowBase, WindowStart, LCOUNT, CPENABLE, FP's FCR and FSR,
//	    cache attributes

/**************************************************************************/

	.text
	.global	_app_reset
_app_reset:
	/* _app_reset may be required to be located at the beginning of the text
	   segment.  However, the constant pool for _app_reset must be placed
	   before the code.  Jump over the constant pool to solve this. */
	j	.LpastInitialConstants

	.literal_position	// tells the assembler/linker to place literals here

.LpastInitialConstants:
	// Keep a0 zero.  It is used to initialize a few things.
	// It is also the return address, where zero indicates
	// that the frame used by _start is the bottommost frame.
	//
	movi	a0, 0		// keep this register zero.

#if XCHAL_HAVE_LOOPS
	wsr	a0, LCOUNT		// loop count = 0
#endif /* XCHAL_HAVE_LOOPS */

	// Interrupts might be enabled, make sure at least medium and low priority
	// interrupts are disabled until WindowBase, WindowStart, SP, and the stack
	// are all properly setup (which will happen outside this file, after the
	// _start label).  We leave loops enabled on new exception architecture.
#if XCHAL_HAVE_EXCEPTIONS
	movi	a2, XCHAL_EXCM_LEVEL
	wsr	a2, PS		// set PS.INTLEVEL=EXCM_LEVEL, PS.WOE=0, PS.EXCM=0
	rsync
#endif

	// DO THIS FIRST: initialize the window start and base
	// before, so that windows don't move under us.
#if XCHAL_HAVE_WINDOWED
	// We do this even if we are assembling for the
	// call0 abi, but it's not really needed.
	movi	a2, 1
	wsr	a2, WINDOWSTART		// window start = 1
	wsr	a0, WINDOWBASE		// window base = 0
	rsync

	// NOTE:  a0 may no longer be zero here, because
	// we wrote to WindowBase.  So clear it again.
	movi	a0, 0
#endif

	// Now, BEFORE we do any L32R (or MOVI with non-immediate
	// range which results in an L32R), ensure LITBASE is set
	// correctly.  This is necessary for RAM applications loaded
	// using a target-side debug monitor -- such applications
	// don't have a reset vector and start execution at _start.
	// (This part is unnecessary if running from a reset vector.)
	// The target-side debug monitor might have set LITBASE to
	// anything at all, so we cannot rely on its value here.
#if XCHAL_HAVE_ABSOLUTE_LITERALS
	wsr	a0, LITBASE		// force PC-relative L32R
	rsync
# if XSHAL_USE_ABSOLUTE_LITERALS
	.begin	no-absolute-literals		// use PC-rel L32R to load
	movi	a2, _lit4_start + 0x40001	// address of absolute literals
	.end	no-absolute-literals		// (see handlers/ResetVector.S
	wsr	a2, LITBASE			//  for explanation)
	rsync
# endif
#endif


	/*
	 *  Enable the caches correctly for this board.
	 *  We use the "safe" sequence.
	 *
	 *  NOTE:  We don't *initialize* the caches here, because the
	 *  target debugger agent (debug monitor) has initialized them for us.
	 */
	movi	a2, XTBOARD_CACHEATTR_DEFAULT
	cacheattr_set				/* set CACHEATTR from a2 (clobbers a3-a8) */



	// Coprocessor option initialization
#if XCHAL_HAVE_CP
	//movi	a2, XCHAL_CP_MASK	// enable existing CPs
	//  To allow creating new coprocessors using TC that are not known
	//  at GUI build time without having to explicitly enable them,
	//  all CPENABLE bits must be set, even though they may not always
	//  correspond to a coprocessor.
	movi	a2, 0xFF	// enable *all* bits, to allow dynamic TIE
	wsr	a2, CPENABLE
#endif

	// Floating point coprocessor option initialization
#if XCHAL_HAVE_FP
# define FCR	232	/* floating-point control register (user register number) */
# define FSR	233	/* floating-point status register (user register number) */
	rsync		/* wait for WSR to CPENABLE to complete before accessing FP coproc state */
	wur	a0, FCR	/* clear FCR (default rounding mode, round-nearest) */
	wur	a0, FSR	/* clear FSR */
#endif


	/*  NOTE:  Future releases may clear BSS here rather than in the CRT1.  */


	/*
	 *  Now jump to the application.  This is typically the
	 *  C run-time initialization ("CRT") which in turn calls main():
	 */
	movi	a4, _start
	jx	a4		// jump to _start

	.size	_app_reset, . - _app_reset

