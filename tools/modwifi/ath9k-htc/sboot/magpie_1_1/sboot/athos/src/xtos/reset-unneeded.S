// reset-unneeded.S  --  Optional Extraneous Reset Code
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/reset-unneeded.S#2 $

// Copyright (c) 2002-2006 Tensilica Inc.
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

//  This file is meant to be included by another, e.g. crt1-***.S .
//  The code it contains is generally not needed, so is kept in a
//  separate file for clarity of other code.

#if XTOS_RESET_UNNEEDED
	/*
	 *  Reset registers that don't really need to be reset,
	 *  but may provide more predictability when buggy code
	 *  relies on uninitialized state.  It might also clear
	 *  "X"s a bit earlier in hardware simulations.
	 *
	 *  NOTE:  This code is by no means exhaustive.
	 *  More processor registers/states could be reset if desired.
	 *  This is just an example.
	 *
	 *  ASSUMPTION:  a0 is still zero at this point.
	 */

	// Interrupt initialization.
	// Because INTENABLE is cleared by the reset vector, clearing the
	// interrupt-pending register should not be needed.  This assumes
	// that any application setting up an interrupt will register and
	// clear it before enabling it, which is the recommended sequence.
	// 
#if XCHAL_HAVE_INTERRUPTS && (XCHAL_INTCLEARABLE_MASK != 0) && !XCHAL_HAVE_FULL_RESET
	movi	a2, XCHAL_INTCLEARABLE_MASK
	wsr	a2, INTCLEAR		// clear software and edge-trig ints
#endif

	// Timer initialization (not strictly required, but sometimes helpful)
	.macro	reset_timer	num
	 wsr	a0, CCOMPARE_0 + \num
	.endm
	iterate	0, XCHAL_NUM_TIMERS-1, reset_timer

# if XCHAL_HAVE_WINDOWED
	// Windowed address register init -- initialize entire physical AR file
	movi	a0, XCHAL_NUM_AREGS/8	// number of 8-register chunks
arloop:
	addi	a8, a0, -1		// countdown into next chunk's a0
	movi	a0, 0
	movi	a1, 0
	movi	a2, 0
	movi	a3, 0
	movi	a4, 0
	movi	a5, 0
	movi	a6, 0
	movi	a7, 0
	rotw	2			// rotate to next chunk
	bnez	a0, arloop
	//  NOTE:  WINDOWBASE is back to zero at this point.
# else /* XCHAL_HAVE_WINDOWED */
	// Non-windowed address register init
	movi	a1, 0
	movi	a2, 0
	movi	a3, 0
	movi	a4, 0
	movi	a5, 0
	movi	a6, 0
	movi	a7, 0
	movi	a8, 0
	movi	a9, 0
	movi	a10, 0
	movi	a11, 0
	movi	a12, 0
	movi	a13, 0
	movi	a14, 0
	movi	a15, 0
# endif /* XCHAL_HAVE_WINDOWED */
	//  Now all address registers are zero.

	// Initialize LBEG, LEND, and LCOUNT.
# if XCHAL_HAVE_LOOPS
	wsr	a0, LCOUNT		// note: LCOUNT gets cleared by processor reset
	wsr	a0, LBEG
	wsr	a0, LEND
# endif

# if XCHAL_HAVE_DEBUG
	.macro	reset_dbreaka	num
	 wsr	a0, DBREAKA + \num
	.endm
	.macro	reset_ibreaka	num
	 wsr	a0, IBREAKA + \num
	.endm
	iterate	0, XCHAL_NUM_DBREAK-1, reset_dbreaka
	iterate	0, XCHAL_NUM_IBREAK-1, reset_ibreaka
# endif

	// SAR initialization
	ssai	0

	// Exception initialization
# if XCHAL_HAVE_EXCEPTIONS
	wsr	a0, EPC+1
	wsr	a0, EXCSAVE+1
	wsr	a0, EXCCAUSE
# endif

# if XCHAL_HAVE_HIGHLEVEL_INTERRUPTS
	.macro	reset_int	num
	 wsr	a0, EPC + \num
	 wsr	a0, EPS + \num
	 wsr	a0, EXCSAVE + \num
	.endm
	iterate	2, XCHAL_NUM_INTLEVELS, reset_int
# endif

	// Booleans initialization
# if XCHAL_HAVE_BOOLEANS
	wsr	a0, BR
# endif

	// MAC16 initialization
# if XCHAL_HAVE_MAC16
	wsr	a0, ACCLO
	wsr	a0, ACCHI
	wsr	a0, M0
	wsr	a0, M1
	wsr	a0, M2
	wsr	a0, M3
# endif

	// OCD initialization
# if XCHAL_HAVE_OCD
	wsr	a0, DDR
# endif

	isync			// wait for all the above to take effect

#endif /* XTOS_RESET_UNNEEDED */

