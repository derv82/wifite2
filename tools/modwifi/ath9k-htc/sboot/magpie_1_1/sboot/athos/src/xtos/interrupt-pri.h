/* interrupt-pri.h - Definitions and macros related to interrupt prioritization */
/*
 * Copyright (c) 2002-2004, 2006 Tensilica Inc.
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

#if !defined(_ASMLANGUAGE) && !defined(__ASSEMBLER__)
# error "The interrupt-pri.h header file is meant for inclusion by assembly source code only."
#endif

#include <xtensa/coreasm.h>
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"

/*
 *  The following macros are used by int-lowpri-dispatcher.S to
 *  implement prioritized interrupt dispatching and fairness.
 *  The prioritization scheme is set by XTOS parameters in xtos-params.h .
 */


#if XCHAL_HAVE_INTERRUPTS

	//  msindex_int
	//
	//  Return in register \aindex the index of the first (most significant) bit set
	//  in register \amask.
	//  Register \amask is clobbered (modified) by this macro.
	//
	//  Note: this code is similar to the find_ms_setbit macro in <xtensa/coreasm.h>.
	//
	.macro	msindex_int		aindex, amask
# if XCHAL_HAVE_NSA
	nsau	\aindex, \amask		// \aindex = interrupt index, from 0 to 31, from left to right
	//movi	\amask, 31
	//sub	\aindex, \amask, \aindex
# else
	movi	\aindex, 0		// start with result of 0 (point to lsbit of 32)
#  if XCHAL_NUM_INTERRUPTS > 16
	bltui	\amask, 0x10000, 2f	// is it one of the 16 lsbits? (if so, check lower 16 bits)
	addi	\aindex, \aindex, 16	// no, increment result to upper 16 bits (of 32)
	extui	\amask, \amask, 16, 16	// check upper half (shift right 16 bits)
2:
#  endif
#  if XCHAL_NUM_INTERRUPTS > 8
	bltui	\amask, 0x100, 2f	// is it one of the 8 lsbits? (if so, check lower 8 bits)
	addi	\aindex, \aindex, 8	// no, increment result to upper 8 bits (of 16)
	srli	\amask, \amask, 8	// shift right to check upper 8 bits
2:
#  endif
#  if XCHAL_NUM_INTERRUPTS > 4
	bltui	\amask, 0x10, 2f	// is it one of the 4 lsbits? (if so, check lower 4 bits)
	addi	\aindex, \aindex, 4	// no, increment result to upper 4 bits (of 8)
	srli	\amask, \amask, 4	// shift right 4 bits to check upper half
2:
#  endif
	bltui	\amask, 0x4, 2f		// is it one of the 2 lsbits? (if so, check lower 2 bits)
	addi	\aindex, \aindex, 2	// no, increment result to upper 2 bits (of 4)
	srli	\amask, \amask, 2	// shift right 2 bits to check upper half
2:
	bltui	\amask, 0x2, 2f		// is it the lsbit?
	addi	\aindex, \aindex, 1	// no, increment result to upper bit (of 2)
2:					// done! 
# endif /*!NSA*/
	//  HERE:  \aindex = index of interrupt to handle
	//	   \amask is available
	.endm


	//  msindex_int_nc
	//
	//  Same as msindex_int, but does not clobber \amask.
	//  Uses extra register \atmp (a temporary register) if needed.
	//
	.macro	msindex_int_nc	aindex, amask, atmp
# if XCHAL_HAVE_NSA
	msindex_int	\aindex, \amask		// does not clobber \amask in this case
# else
	mov		\atmp, \amask
	msindex_int	\aindex, \atmp
# endif
	.endm


	//  indexmask_int
	//
	//  Compute index of highest priority interrupt in given mask,
	//  and trim mask to single bit corresponding to that interrupt.
	//  This is used for interrupt dispatching.
	//
	//  Entry:
	//	\index  = (undefined)
	//	\mask   = non-zero mask of interrupt bits to consider handling
	//	\intptr = &_xtos_intstruct if INTENABLE virtualized, else undefined
	//	\tmp    = (undefined)
	//  Exit:
	//	\index  = index of interrupt (reversed if NSA present)
	//	\mask   = single bit corresponding to index
	//	\intptr = (preserved)
	//	\tmp    = (clobbered)
	//
	.macro	indexmask_int	index, mask, intptr, tmp
# if XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_LO

	msindex_int	\index, \mask	// \index = index of msbit set in \mask (\tmp is tmp, \mask clobbered)
	//  \index now contains the index of the highest priority pending+enabled interrupt.
#  if XCHAL_HAVE_NSA
	movi		\mask, 0x80000000
	ssr		\index
	srl		\mask, \mask	//  \mask = single bit set corresponding to interrupt to be processed...
#  else
	movi		\mask, 1
	ssl		\index
	sll		\mask, \mask	//  \mask = single bit set corresponding to interrupt to be processed...
#  endif

# elif XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_HI

	neg		\index, \mask		// find lsbit in \mask ...
	and		\mask, \index, \mask	// ...
	msindex_int_nc	\index, \mask, \tmp	// \index = index of msbit set in \mask (\tmp is tmp, \mask not clobbered)

# else
#  error Unsupported priority ordering.
# endif /*SUBPRI_ORDER*/
	.endm


	//  index_int
	//
	//  Compute index of highest priority interrupt in given mask.
	//  This is used for fairness computations.
	//
	//  Entry:
	//	\index  = (undefined)
	//	\mask   = non-zero mask of interrupt bits to consider handling
	//	\intptr = &_xtos_intptr
	//	\tmp    = (undefined)
	//  Exit:
	//	\index  = index of interrupt (reversed if NSA present)
	//	\mask   = (preserved)
	//	\intptr = (preserved)
	//	\tmp    = (clobbered)
	//
	.macro	index_int	index, mask, intptr, tmp
# if XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_LO
	msindex_int_nc	\index, \mask, \tmp	// \index = index of msbit set in \mask (\mask not clobbered)
# elif XTOS_SUBPRI_ORDER == XTOS_SPO_ZERO_HI
	neg		\tmp, \mask		// find lsbit in \mask ...
	and		\tmp, \tmp, \mask	// ...
	msindex_int	\index, \tmp		// \index = index of msbit set in \tmp (\tmp is clobbered)
# else
#  error oops
# endif
	.endm	// index_int


#endif /* XCHAL_HAVE_INTERRUPTS */


