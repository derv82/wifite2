// exc-alloca-handler.S - ALLOCA cause exception assembly-level handler
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/exc-alloca-handler.S#3 $

// Copyright (c) 2002-2010 Tensilica Inc.
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

/*
 * Code written to the windowed ABI must use the MOVSP instruction to modify
 * the stack pointer (except for startup code, which doesn't have a caller).
 * The compiler uses MOVSP to allocate very large or variable size stack frames.
 * MOVSP guarantees that the caller frame's a0-a3 registers, stored below the
 * stack pointer, are moved atomically with respect to interrupts and exceptions
 * to satisfy windowed ABI requirements.  When user code executes the MOVSP
 * instruction and the caller frame is on the stack rather than in the register
 * file, the processor takes an ALLOCA exception.  The ALLOCA exception handler
 * moves the caller frame's a0-a3 registers to follow the stack pointer.
 * This file implements this ALLOCA exception handler.
 *
 * Code written in C can generate a MOVSP in four situations:
 *
 * 1. By calling "alloca":
 *
 *   void foo(int array_size) {
 *     char * bar = alloca(array_size);
 *     ...
 *
 * 2. By using variable sized arrays (a GNU C extension):
 *
 *   void foo(int array_size) {
 *     char bar[array_size];
 *     ...
 *
 * 3. By using nested C functions (also a GNU C extension):
 *
 *   void afunction(void) {
 *     ...
 *     int anotherfunction(void) {
 *     }
 *     ...
 *
 * 4. By using very large amounts of stack space in a single function. The exact
 *    limit is 32,760 bytes (including 16-48 bytes of caller frame overhead).
 *    Typically, users don't encounter this limit unless they have functions
 *    that locally declare large arrays, for example:
 *
 *   void foo(void) {
 *     int an_array[8192];		// 32,768 bytes
 *     int another_array[100];		// 400 bytes
 *     ...
 *
 *
 * NOTE:  This handler only works when MOVSP's destination register is the stack
 * pointer "a1" (synonym with "sp"), i.e. "MOVSP a1, <as>".  This is the only
 * meaningful form of MOVSP in the windowed ABI, and the only form generated
 * by the compiler and used in assembly.  The code below does not check the
 * destination register, so other forms of MOVSP cause unexpected behaviour.
 */

#include <xtensa/coreasm.h>
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"

#define ERROR_CHECKING	1	// define as 0 to save a few bytes


#if XCHAL_HAVE_EXCEPTIONS

//Vector:
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
	.global	_xtos_alloca_handler
_xtos_alloca_handler:
#if !XCHAL_HAVE_WINDOWED || defined(__XTENSA_CALL0_ABI__)
	rfe_rfue
#else /* we have windows w/o call0 abi */
	//  HERE:  a2, a3, a4 have been saved to
	//  exception stack frame allocated with a1 (sp).
	//  a2 contains EXCCAUSE.
	//  (12 cycles from vector to here, assuming cache hits, 5-stage pipe, etc)

	/*
	 *  Skip the MOVSP instruction so we don't execute it again on return:
	 */

	rsr	a3, EPC_1		// load instruction address (PC)
	s32i	a5, a1, UEXC_a5		// save a5
	addi	a2, a3, 3		// increment PC to skip MOVSP instruction
#if XCHAL_HAVE_LOOPS
	/*
	 *  If the MOVSP instruction is the last instruction in the body of
	 *  a zero-overhead loop that must be executed again, then decrement
	 *  the loop count and resume execution at the head of the loop.
	 */
	rsr	a4, LEND
	rsr	a5, LCOUNT
	bne	a4, a2, 1f		// done unless next-PC matches LEND
	beqz	a5, 1f			// if LCOUNT zero, not in loop
	addi	a5, a5, -1		// z.o. loopback! decrement LCOUNT...
	wsr	a5, LCOUNT
	rsr	a2, LBEG		// PC back to start of loop
#endif /*XCHAL_HAVE_LOOPS*/
1:	wsr	a2, EPC_1		// update return PC past MOVSP

	/*
	 *  Figure out what register MOVSP is moving from ('s' field, 2nd byte).
	 *  If MOVSP is in an instruction RAM or ROM, we can only access it with
	 *  32-bit loads.  So use shifts to read the byte from a 32-bit load.
	 */

	addi	a3, a3, 1		// advance to byte containing 's' field
	extui	a2, a3, 0, 2		// get bits 0 and 1 of address of this byte
	sub	a3, a3, a2		// put address on 32-bit boundary
	l32i	a3, a3, 0		// get word containing byte (can't use l8ui on IRAM/IROM)
	rsr	a4, SAR			// save SAR
	//  NOTE: possible addition here: verify destination register is indeed a1.
# if XCHAL_HAVE_BE
	ssa8b	a2
	sll	a3, a3
	extui	a3, a3, 28, 4		// extract source register number
# else
	ssa8l	a2
	srl	a3, a3
	extui	a3, a3, 0, 4		// extract source register number
# endif
	wsr	a4, SAR			// restore SAR
	//  (+?? cycles max above = ?? cycles, assuming cache hits, 5-stage pipe, no zoloops, etc)

	movi	a4, .Ljmptable	        // jump table
	mov	a5, a1			// save the exception stack frame ptr in a5
	addi	a1, a1, ESF_TOTALSIZE	// restore a1 (in case of MOVSP a1,a1)

# if XCHAL_HAVE_DENSITY
	addx4	a4, a3, a4              // index by src reg number * 4
#  define ALIGN	.align 4		// 4-byte jmptable entries
#  define MOV	_mov.n
#  define L32I	_l32i.n
#  define DONE	_bnez.n a4, .Lmove_save_area	// a4 known non-zero
# else
	addx8	a4, a3, a4              // index by src reg number * 8
#  define ALIGN	.align 8		// 8-byte jmptable entries
#  define MOV	mov
#  define L32I	l32i
#  define DONE	j .Lmove_save_area
# endif

	jx	a4			// jump into the following table

	ALIGN
.Ljmptable:	MOV	a1, a0		; DONE	// MOVSP a1, a0
	ALIGN				; DONE	// MOVSP a1, a1
	ALIGN ; L32I	a1, a5, UEXC_a2	; DONE	// MOVSP a1, a2
	ALIGN ; L32I	a1, a5, UEXC_a3	; DONE	// MOVSP a1, a3
	ALIGN ; L32I	a1, a5, UEXC_a4	; DONE	// MOVSP a1, a4
	ALIGN ; L32I	a1, a5, UEXC_a5	; DONE	// MOVSP a1, a5
	ALIGN ; MOV	a1, a6		; DONE	// MOVSP a1, a6
	ALIGN ; MOV	a1, a7		; DONE	// MOVSP a1, a7
	ALIGN ; MOV	a1, a8		; DONE	// MOVSP a1, a8
	ALIGN ; MOV	a1, a9		; DONE	// MOVSP a1, a9
	ALIGN ; MOV	a1, a10		; DONE	// MOVSP a1, a10
	ALIGN ; MOV	a1, a11		; DONE	// MOVSP a1, a11
	ALIGN ; MOV	a1, a12		; DONE	// MOVSP a1, a12
	ALIGN ; MOV	a1, a13		; DONE	// MOVSP a1, a13
	ALIGN ; MOV	a1, a14		; DONE	// MOVSP a1, a14
	ALIGN ; MOV	a1, a15			// MOVSP a1, a15

.Lmove_save_area:
	//  Okay.  a1 now contains the new SP value.

# if ERROR_CHECKING
	//  Verify it is sensible:
	extui	a3, a1, 0, 2		// verify that new SP is 4-byte aligned
	beqz	a3, 1f			// if so, skip fixup

//	.global	_xtos_misaligned_movsp	// make label visible for debugging
//_xtos_misaligned_movsp:
#  if XCHAL_HAVE_DEBUG
	break	1, 15			// break into debugger (if any)
#  endif
	sub	a1, a1, a3		// FORCE alignment of the new pointer (!)
1:
# endif

# if XCHAL_HAVE_XEA2
	addi	a2, a5, ESF_TOTALSIZE		// compute a2 = old SP
# else /*XEA1:*/
	addi	a2, a5, ESF_TOTALSIZE-16	// compute a2 = old SP's save area
# endif
	//  Does new SP (in a1) overlap with exception stack frame (in a5)?:
	movi	a4, ESF_TOTALSIZE	// size of exception stack frame
	sub	a3, a1, a5		// distance from ESF ptr to new SP
	bgeu	a3, a4, 1f		// does new SP overlap ESF? branch if not
	//  Move ESF down so it doesn't overlap with the new register save area:
	//  (a1 = current ESF, a2 = new SP, a4 = ESF_TOTALSIZE)
	sub	a5, a5, a4		// shift down ESF (by ESF size)
	l32i	a3, a5, UEXC_a2+ESF_TOTALSIZE
	l32i	a4, a5, UEXC_a3+ESF_TOTALSIZE
	s32i	a3, a5, UEXC_a2
	s32i	a4, a5, UEXC_a3
	l32i	a3, a5, UEXC_a4+ESF_TOTALSIZE
	l32i	a4, a5, UEXC_a5+ESF_TOTALSIZE
	s32i	a3, a5, UEXC_a4
	s32i	a4, a5, UEXC_a5
1:

	//  Move the register save area (from old SP to new SP):
# if XCHAL_HAVE_XEA2
	l32e	a3, a2, -16
	l32e	a4, a2, -12
	s32e	a3, a1, -16
	s32e	a4, a1, -12
	l32e	a3, a2, -8
	l32e	a4, a2, -4
	s32e	a3, a1, -8
	s32e	a4, a1, -4
# else /*XEA1:*/
	addi	a1, a1, -16		// point to new save area
	l32i	a3, a2, 0
	l32i	a4, a2, 4
	s32i	a3, a1, 0
	s32i	a4, a1, 4
	l32i	a3, a2, 8
	l32i	a4, a2, 12
	s32i	a3, a1, 8
	s32i	a4, a1, 12
	addi	a1, a1, 16		// back to correct new SP
# endif /*XEA1*/
	//  (+?? cycles max above = ?? cycles, assuming cache hits, 5-stage pipe, etc)

	//  Restore a2, a3, a4, a5, and return:
	l32i	a2, a5, UEXC_a2
	l32i	a3, a5, UEXC_a3
	l32i	a4, a5, UEXC_a4
	l32i	a5, a5, UEXC_a5
	rfe_rfue
	//  (+?? cycles max above = ?? cycles, assuming cache hits, 5-stage pipe, etc)


#endif /* !XCHAL_HAVE_WINDOWED || __XTENSA_CALL0_ABI */

	.size	_xtos_alloca_handler, . - _xtos_alloca_handler

#endif /* XCHAL_HAVE_EXCEPTIONS */

