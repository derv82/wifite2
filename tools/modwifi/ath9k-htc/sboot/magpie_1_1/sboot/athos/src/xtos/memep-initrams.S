// memep-initrams.S  --  Initialize local memory ECC/parity
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/memep-initrams.S#3 $

// Copyright (c) 2006-2010 Tensilica Inc.
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


	/*
	 *  void  _xtos_memep_initrams(void);
	 *
	 *  Most reset vectors initialize caches, leaving only the local memories
	 *  (instruction and data RAMs) with potentially some words that have
	 *  not been written to and thus have uninitialized ECC/parity bits.
	 *  Loading such a word after enabling ECC/parity checking would result
	 *  in an exception (or memory error reported in MESR).  To avoid this,
	 *  an application must either carefully avoid loading from uninitialized
	 *  words, or ensure it writes to every instruction and data RAM word.
	 *  The latter is what this function does.  It reads and writes every
	 *  word of every local instruction and data RAM.  It should normally
	 *  be called with interrupts disabled.  An interrupt might come in
	 *  between a load and store, in which case any modification made by the
	 *  interrupt handler to that local memory location is lost when this
	 *  function resumes and does the store.  If no interrupt handler makes
	 *  any persistent modification to local memories, disabling them around
	 *  a call to this function may be unnecessary.
	 *
	 * On the simulator (ISS), everything comes up zeroed, so no there is
	 * no need for this initialization.
	 */
	.text
	.align	4
	.global	_xtos_memep_initrams
_xtos_memep_initrams:
	abi_entry

	// Local Memory ECC/Parity option initialization
#if XCHAL_HAVE_MEM_ECC_PARITY && (XCHAL_NUM_DATARAM || XCHAL_NUM_INSTRAM /*|| XCHAL_NUM_URAM || XCHAL_NUM_XLMI*/) && !defined(SIMULATOR)
	.section .rodata, "a"
	.align	4
.L_locmemep_start:
#  if XCHAL_NUM_DATARAM >= 1 && XCHAL_DATARAM0_ECC_PARITY
	.long	XCHAL_DATARAM0_VADDR, XCHAL_DATARAM0_VADDR+XCHAL_DATARAM0_SIZE
#  endif
#  if XCHAL_NUM_DATARAM >= 2 && XCHAL_DATARAM1_ECC_PARITY
	.long	XCHAL_DATARAM1_VADDR, XCHAL_DATARAM1_VADDR+XCHAL_DATARAM1_SIZE
#  endif
#  if XCHAL_NUM_INSTRAM >= 1 && XCHAL_INSTRAM0_ECC_PARITY
	.long	XCHAL_INSTRAM0_VADDR, XCHAL_INSTRAM0_VADDR+XCHAL_INSTRAM0_SIZE
#  endif
#  if XCHAL_NUM_INSTRAM >= 2 && XCHAL_INSTRAM1_ECC_PARITY
	.long	XCHAL_INSTRAM1_VADDR, XCHAL_INSTRAM1_VADDR+XCHAL_INSTRAM1_SIZE
#  endif
.L_locmemep_end:
	.text
	movi	a5, .L_locmemep_start	// start of table of local memory ranges
	movi	a6, .L_locmemep_end	// end of table ...
2:	l32i	a3, a5, 0		// start of local memory
	l32i	a4, a5, 4		// end of local memory
	addi	a5, a5, 8		// (next entry in table)
1:	l32i	a2, a3, 0		// load and store every word of local memory...
	s32i	a2, a3, 0		//  ... to initialize all parity and/or ECC bits
	addi	a3, a3, 4
	bltu	a3, a4, 1b		// loop until whole memory initialized
	bltu	a5, a6, 2b		// loop until all memories initialized
	//  ECC/parity bits are now initialized, checking can be turned on.
#endif /* ECC/parity on instruction or data RAM(s) */

	abi_return

	.size	_xtos_memep_initrams, . - _xtos_memep_initrams

