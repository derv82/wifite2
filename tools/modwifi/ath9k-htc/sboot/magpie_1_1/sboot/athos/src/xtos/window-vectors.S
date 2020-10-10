// window-vectors.S - Register Window Overflow/Underflow Handlers
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/window-vectors.S#3 $

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

#if XCHAL_HAVE_WINDOWED && !defined(__XTENSA_CALL0_ABI__)

# ifndef NO_SECTION_DIRECTIVES
// Exports
.global _WindowOverflow4
.global _WindowUnderflow4
.global _WindowOverflow8
.global _WindowUnderflow8
.global _WindowOverflow12
.global _WindowUnderflow12

	//  Note:  the current window exception vectors do not generate any
	//  literals.  Hence the literal_prefix directive is not necessary.
	//  Specifying it "just in case" creates an empty section (named
	//  ".WindowVectors.literal") which can in some cases cause linking
	//  problems (the linker scripts don't place it anywhere).
	//  So leave it commented out:
	//
	//.begin	literal_prefix	.WindowVectors

	.section		.WindowVectors.text, "ax"
# endif


//
// GENERAL NOTES:
//
// These window exception handlers need not be modified.
// They are specific to the windowed call ABI only.
//
// Underflow Handlers:
//
// The underflow handler for returning from call[i+1] to call[i]
// must preserve all the registers from call[i+1]'s window.
// In particular, a0 and a1 must be preserved because the RETW instruction
// will be reexecuted (and may even underflow again if an intervening
// exception has flushed call[i]'s registers).
// Registers a2 and up may contain return values.
//
// The caller could also potentially assume that the callee's a0 and a1
// (its own a4&a5 if call4, a8&a9 if call8, a12&a13 if call12)
// are correct for whatever reason (not a clean thing to do in general,
// but if it's possible, unless the ABI explicitly prohibits it,
// it will eventually be done :) -- whether the the ABI needs to
// prohibit this is a different question).
//
// Timing of Handlers:
//
// Here is an overview of the overhead of taking a window exception,
// ie. the number of additional cycles taken relative to case where
// an exception is not taken.
// NOTE:  these numbers do not take into account any cache misses,
// write buffer stalls, or other external stalls, if they occur.
// The totals consist of 5 cycles to enter the handler (or 6 or 7
// for optional longer pipelines in Xtensa LX), the number of instructions
// and interlocks (2nd and 3rd columns below), and 2 cycles jump delay
// on return (3 cycles for optional longer I-side pipeline in Xtensa LX):
//
//			Instruction+bubbles	Totals (5-stage)
//			XEA1	XEA2		XEA1	XEA2
//	Overflow-4	7	5		14	12
//	Overflow-8	14	10		21	17
//	Overflow-12	18	14		25	21
//	Underflow-4	6	5		13	12
//	Underflow-8	14	10		21	17
//	Underflow-12	18	14		25	21
//
//	Underflow-8	15	12		25	22	(7-stage; could be made 1 less)
//	Underflow-12	19	16		29	26	(7-stage; could be made 1 less)

#ifndef WINDOW_BASE_VECOFS
#define WINDOW_BASE_VECOFS	XCHAL_WINDOW_OF4_VECOFS
#endif


// 4-Register Window Overflow Vector (Handler)
//
// Invoked if a call[i] referenced a register (a4-a15)
// that contains data from ancestor call[j];
// call[j] had done a call4 to call[j+1].
// On entry here:
//	window rotated to call[j] start point;
//	a0-a3 are registers to be saved;
//	a4-a15 must be preserved;
//	a5 is call[j+1]'s stack pointer.

	.org	XCHAL_WINDOW_OF4_VECOFS - WINDOW_BASE_VECOFS
_WindowOverflow4:
#if XCHAL_HAVE_XEA1
	addi	a5, a5, -16	// to make store offsets positive
	s32i	a0, a5,   0	// save a0 to call[j+1]'s stack frame
	s32i	a1, a5,   4	// save a1 to call[j+1]'s stack frame
	s32i	a2, a5,   8	// save a2 to call[j+1]'s stack frame
	s32i	a3, a5,  12	// save a3 to call[j+1]'s stack frame
	addi	a5, a5,  16	// restore a5
#else
	s32e	a0, a5, -16	// save a0 to call[j+1]'s stack frame
	s32e	a1, a5, -12	// save a1 to call[j+1]'s stack frame
	s32e	a2, a5,  -8	// save a2 to call[j+1]'s stack frame
	s32e	a3, a5,  -4	// save a3 to call[j+1]'s stack frame
#endif
	rfwo			// rotates back to call[i] position

	.size	_WindowOverflow4, . - _WindowOverflow4


// 4-Register Window Underflow Vector (Handler)
//
// Invoked by RETW returning from call[i+1] to call[i]
// where call[i]'s registers must be reloaded (not live in ARs);
// call[i] had done a call4 to call[i+1].
// On entry here:
//	window rotated to call[i] start point;
//	a0-a3 are undefined, must be reloaded with call[i].reg[0..3];
//	a4-a15 must be preserved (they are call[i+1].reg[0..11]);
//	a5 is call[i+1]'s stack pointer.

	.org	XCHAL_WINDOW_UF4_VECOFS - WINDOW_BASE_VECOFS
_WindowUnderflow4:
#if XCHAL_HAVE_XEA1
	addi	a3, a5, -16	// to make load offsets positive
	l32i	a0, a3,   0	// restore a0 from call[i+1]'s stack frame
	l32i	a1, a3,   4	// restore a1 from call[i+1]'s stack frame
	l32i	a2, a3,   8	// restore a2 from call[i+1]'s stack frame
	l32i	a3, a3,  12	// restore a3 from call[i+1]'s stack frame
#else
	l32e	a0, a5, -16	// restore a0 from call[i+1]'s stack frame
	l32e	a1, a5, -12	// restore a1 from call[i+1]'s stack frame
	l32e	a2, a5,  -8	// restore a2 from call[i+1]'s stack frame
	l32e	a3, a5,  -4	// restore a3 from call[i+1]'s stack frame
#endif
	rfwu

	.size	_WindowUnderflow4, . - _WindowUnderflow4


// 8-Register Window Overflow Vector (Handler)
//
// Invoked if a call[i] referenced a register (a4-a15)
// that contains data from ancestor call[j];
// call[j] had done a call8 to call[j+1].
// On entry here:
//	window rotated to call[j] start point;
//	a0-a7 are registers to be saved;
//	a8-a15 must be preserved;
//	a9 is call[j+1]'s stack pointer.

	.org	XCHAL_WINDOW_OF8_VECOFS - WINDOW_BASE_VECOFS
_WindowOverflow8:
#if XCHAL_HAVE_XEA1
	addi	a9, a9, -16	// to make store offsets positive
	s32i	a0, a9,   0	// save a0 to call[j+1]'s stack frame
	addi	a0, a1, -16	// a0 <- call[j-1]'s sp
	s32i	a1, a9,   4	// save a1 to call[j+1]'s stack frame
	l32i	a0, a0,   4	// (used to find end of call[j]'s frame)
	s32i	a2, a9,   8	// save a2 to call[j+1]'s stack frame
	s32i	a3, a9,  12	// save a3 to call[j+1]'s stack frame
	addi	a9, a9,  16	// restore a9
	addi	a0, a0, -32	// to make load offsets positive
	s32i	a4, a0,   0	// save a4 to call[j]'s stack frame
	s32i	a5, a0,   4	// save a5 to call[j]'s stack frame
	s32i	a6, a0,   8	// save a6 to call[j]'s stack frame
	s32i	a7, a0,  12	// save a7 to call[j]'s stack frame
#else
	s32e	a0, a9, -16	// save a0 to call[j+1]'s stack frame
	l32e	a0, a1, -12	// a0 <- call[j-1]'s sp (used to find end of call[j]'s frame)
	s32e	a1, a9, -12	// save a1 to call[j+1]'s stack frame
	s32e	a2, a9,  -8	// save a2 to call[j+1]'s stack frame
	s32e	a3, a9,  -4	// save a3 to call[j+1]'s stack frame
	s32e	a4, a0, -32	// save a4 to call[j]'s stack frame
	s32e	a5, a0, -28	// save a5 to call[j]'s stack frame
	s32e	a6, a0, -24	// save a6 to call[j]'s stack frame
	s32e	a7, a0, -20	// save a7 to call[j]'s stack frame
#endif
	rfwo			// rotates back to call[i] position

	.size	_WindowOverflow8, . - _WindowOverflow8


// 8-Register Window Underflow Vector (Handler)
//
// Invoked by RETW returning from call[i+1] to call[i]
// where call[i]'s registers must be reloaded (not live in ARs);
// call[i] had done a call8 to call[i+1].
// On entry here:
//	window rotated to call[i] start point;
//	a0-a7 are undefined, must be reloaded with call[i].reg[0..7];
//	a8-a15 must be preserved (they are call[i+1].reg[0..7]);
//	a9 is call[i+1]'s stack pointer.

	.org	XCHAL_WINDOW_UF8_VECOFS - WINDOW_BASE_VECOFS
_WindowUnderflow8:
#if XCHAL_HAVE_XEA1
	addi	a9, a9, -16	// to make load offsets positive
	l32i	a0, a9,   0	// restore a0 from call[i+1]'s stack frame
	l32i	a1, a9,   4	// restore a1 from call[i+1]'s stack frame
	l32i	a2, a9,   8	// restore a2 from call[i+1]'s stack frame
	addi	a7, a1, -16	// a7 <- call[i-1]'s sp
	l32i	a7, a7,   4	// (used to find end of call[i]'s frame)
	l32i	a3, a9,  12	// restore a3 from call[i+1]'s stack frame
	addi	a9, a9,  16	// restore a9
	addi	a7, a7, -32	// to make load offsets positive
	l32i	a4, a7,   0	// restore a4 from call[i]'s stack frame
	l32i	a5, a7,   4	// restore a5 from call[i]'s stack frame
	l32i	a6, a7,   8	// restore a6 from call[i]'s stack frame
	l32i	a7, a7,  12	// restore a7 from call[i]'s stack frame
#else
	l32e	a0, a9, -16	// restore a0 from call[i+1]'s stack frame
	l32e	a1, a9, -12	// restore a1 from call[i+1]'s stack frame
	l32e	a2, a9,  -8	// restore a2 from call[i+1]'s stack frame
	l32e	a7, a1, -12	// a7 <- call[i-1]'s sp (used to find end of call[i]'s frame)
	l32e	a3, a9,  -4	// restore a3 from call[i+1]'s stack frame
	l32e	a4, a7, -32	// restore a4 from call[i]'s stack frame
	l32e	a5, a7, -28	// restore a5 from call[i]'s stack frame
	l32e	a6, a7, -24	// restore a6 from call[i]'s stack frame
	l32e	a7, a7, -20	// restore a7 from call[i]'s stack frame
#endif
	rfwu

	.size	_WindowUnderflow8, . - _WindowUnderflow8


// 12-Register Window Overflow Vector (Handler)
//
// Invoked if a call[i] referenced a register (a4-a15)
// that contains data from ancestor call[j];
// call[j] had done a call12 to call[j+1].
// On entry here:
//	window rotated to call[j] start point;
//	a0-a11 are registers to be saved;
//	a12-a15 must be preserved;
//	a13 is call[j+1]'s stack pointer.

	.org	XCHAL_WINDOW_OF12_VECOFS - WINDOW_BASE_VECOFS
_WindowOverflow12:
#if XCHAL_HAVE_XEA1
	addi	a13, a13, -16	// to make store offsets positive
	s32i	a0,  a13,   0	// save a0 to call[j+1]'s stack frame
	addi	a0,  a1,  -16	// a0 <- call[j-1]'s sp
	s32i	a1,  a13,   4	// save a1 to call[j+1]'s stack frame
	l32i	a0,  a0,    4	// (used to find end of call[j]'s frame)
	s32i	a2,  a13,   8	// save a2 to call[j+1]'s stack frame
	s32i	a3,  a13,  12	// save a3 to call[j+1]'s stack frame
	addi	a13, a13,  16	// restore a13
	addi	a0,  a0,  -48	// to make load offsets positive
	s32i	a4,  a0,    0	// save a4 to end of call[j]'s stack frame
	s32i	a5,  a0,    4	// save a5 to end of call[j]'s stack frame
	s32i	a6,  a0,    8	// save a6 to end of call[j]'s stack frame
	s32i	a7,  a0,   12	// save a7 to end of call[j]'s stack frame
	s32i	a8,  a0,   16	// save a8 to end of call[j]'s stack frame
	s32i	a9,  a0,   20	// save a9 to end of call[j]'s stack frame
	s32i	a10, a0,   24	// save a10 to end of call[j]'s stack frame
	s32i	a11, a0,   28	// save a11 to end of call[j]'s stack frame
#else
	s32e	a0,  a13, -16	// save a0 to call[j+1]'s stack frame
	l32e	a0,  a1,  -12	// a0 <- call[j-1]'s sp (used to find end of call[j]'s frame)
	s32e	a1,  a13, -12	// save a1 to call[j+1]'s stack frame
	s32e	a2,  a13,  -8	// save a2 to call[j+1]'s stack frame
	s32e	a3,  a13,  -4	// save a3 to call[j+1]'s stack frame
	s32e	a4,  a0,  -48	// save a4 to end of call[j]'s stack frame
	s32e	a5,  a0,  -44	// save a5 to end of call[j]'s stack frame
	s32e	a6,  a0,  -40	// save a6 to end of call[j]'s stack frame
	s32e	a7,  a0,  -36	// save a7 to end of call[j]'s stack frame
	s32e	a8,  a0,  -32	// save a8 to end of call[j]'s stack frame
	s32e	a9,  a0,  -28	// save a9 to end of call[j]'s stack frame
	s32e	a10, a0,  -24	// save a10 to end of call[j]'s stack frame
	s32e	a11, a0,  -20	// save a11 to end of call[j]'s stack frame
#endif
	rfwo			// rotates back to call[i] position

	.size	_WindowOverflow12, . - _WindowOverflow12


// 12-Register Window Underflow Vector (Handler)
//
// Invoked by RETW returning from call[i+1] to call[i]
// where call[i]'s registers must be reloaded (not live in ARs);
// call[i] had done a call12 to call[i+1].
// On entry here:
//	window rotated to call[i] start point;
//	a0-a11 are undefined, must be reloaded with call[i].reg[0..11];
//	a12-a15 must be preserved (they are call[i+1].reg[0..3]);
//	a13 is call[i+1]'s stack pointer.

	.org	XCHAL_WINDOW_UF12_VECOFS - WINDOW_BASE_VECOFS
_WindowUnderflow12:
#if XCHAL_HAVE_XEA1
	addi	a13, a13, -16	// to make load offsets positive
	l32i	a0,  a13,   0	// restore a0 from call[i+1]'s stack frame
	l32i	a1,  a13,   4	// restore a1 from call[i+1]'s stack frame
	l32i	a2,  a13,   8	// restore a2 from call[i+1]'s stack frame
	addi	a11, a1,  -16	// a11 <- call[i-1]'s sp
	l32i	a11, a11,   4	// (used to find end of call[i]'s frame)
	l32i	a3,  a13,  12	// restore a3 from call[i+1]'s stack frame
	addi	a13, a13,  16	// restore a13
	addi	a11, a11, -48	// to make load offsets positive
	l32i	a4,  a11,   0	// restore a4 from end of call[i]'s stack frame
	l32i	a5,  a11,   4	// restore a5 from end of call[i]'s stack frame
	l32i	a6,  a11,   8	// restore a6 from end of call[i]'s stack frame
	l32i	a7,  a11,  12	// restore a7 from end of call[i]'s stack frame
	l32i	a8,  a11,  16	// restore a8 from end of call[i]'s stack frame
	l32i	a9,  a11,  20	// restore a9 from end of call[i]'s stack frame
	l32i	a10, a11,  24	// restore a10 from end of call[i]'s stack frame
	l32i	a11, a11,  28	// restore a11 from end of call[i]'s stack frame
#else
	l32e	a0,  a13, -16	// restore a0 from call[i+1]'s stack frame
	l32e	a1,  a13, -12	// restore a1 from call[i+1]'s stack frame
	l32e	a2,  a13,  -8	// restore a2 from call[i+1]'s stack frame
	l32e	a11, a1,  -12	// a11 <- call[i-1]'s sp (used to find end of call[i]'s frame)
	l32e	a3,  a13,  -4	// restore a3 from call[i+1]'s stack frame
	l32e	a4,  a11, -48	// restore a4 from end of call[i]'s stack frame
	l32e	a5,  a11, -44	// restore a5 from end of call[i]'s stack frame
	l32e	a6,  a11, -40	// restore a6 from end of call[i]'s stack frame
	l32e	a7,  a11, -36	// restore a7 from end of call[i]'s stack frame
	l32e	a8,  a11, -32	// restore a8 from end of call[i]'s stack frame
	l32e	a9,  a11, -28	// restore a9 from end of call[i]'s stack frame
	l32e	a10, a11, -24	// restore a10 from end of call[i]'s stack frame
	l32e	a11, a11, -20	// restore a11 from end of call[i]'s stack frame
#endif
	rfwu

	.size	_WindowUnderflow12, . - _WindowUnderflow12


# ifndef NO_SECTION_DIRECTIVES
	//.end	literal_prefix
	.text
# endif


#endif /* XCHAL_HAVE_WINDOWED && !defined(__XTENSA_CALL0_ABI__) */

