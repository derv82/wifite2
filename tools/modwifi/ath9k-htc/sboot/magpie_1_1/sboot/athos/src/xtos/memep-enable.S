// memep-enable.S  --  Turn on local memory ECC/parity checking
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/memep-enable.S#3 $

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
	 *  void  _xtos_memep_enable(int flags);
	 *
	 *  Turn on local memory ECC/parity checking, for both
	 *  data access and instruction fetch.
	 *
	 *  For now, flags are ignored.  Caller is expected to pass zero.
	 *
	 *  _xtos_memep_initrams() must have already been called, if necessary,
	 *  to ensure all ECC/parity bits are valid in any local instruction
	 *  or data RAM.  The normal reset vector sequence already takes care
	 *  of initializing any local cache ECC/parity bits.
	 */
	.text
	.align	4
	.global	_xtos_memep_enable
_xtos_memep_enable:
	abi_entry

#if XCHAL_HAVE_MEM_ECC_PARITY

	// Local Memory ECC/Parity option initialization
	//
	//  NOTE:  We turn on exceptions on correctable errors and correct
	//	them in the memory error handler.
	movi	a2, MESR_ERRENAB | MESR_DATEXC | MESR_INSEXC
	wsr	a2, MESR
	isync

#endif /* XCHAL_HAVE_MEM_ECC_PARITY */

	movi	a2, 0		// successfully turned on what we could
	abi_return

	.size	_xtos_memep_enable, . - _xtos_memep_enable

