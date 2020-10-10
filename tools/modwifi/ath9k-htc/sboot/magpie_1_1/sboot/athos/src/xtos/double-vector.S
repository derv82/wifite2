// double-vector.S  --  Double Exception Vector
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/double-vector.S#3 $

// Copyright (c) 2000-2004, 2006, 2010 Tensilica Inc.
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
#include <xtensa/config/system.h>
#include <xtensa/config/specreg.h>
#ifdef SIMULATOR
#include <xtensa/simcall.h>
#endif


#if XCHAL_HAVE_EXCEPTIONS && defined(XCHAL_DOUBLEEXC_VECTOR_VADDR)

/*
 *  This is a very minimalist implementation of the double
 *  exception vector.  For XEA2 configurations without a
 *  full MMU, this vector is only expected to be executed
 *  upon fatal errors (exceptions that occur within critical
 *  sections of exception vectors and handlers).
 *
 *  For configurations with a full MMU (ie. with TLBs and
 *  auto-refill) and the windowed address registers option,
 *  a more complete version of this handler is necessary if:
 *  dynamic page mapping is implemented, and the stack
 *  can ever point to a dynamically mapped area.
 *  In this case, a double exception is a normal occurrence
 *  when a stack access within a window handler causes
 *  a TLB miss exception or other expected MMU fault.
 *  XTOS does not support this scenario, hence a minimalist
 *  double exception vector is sufficient.
 */

	.begin	literal_prefix	.DoubleExceptionVector
	.section		.DoubleExceptionVector.text, "ax"

	.align 4
	.global	_DoubleExceptionVector
_DoubleExceptionVector:
#  if XCHAL_HAVE_DEBUG
1:	break	1,4			// unhandled double exception
#  elif defined(SIMULATOR)
	wsr	a2, EXCSAVE1		// save a2 where simulator expects it
	movi	a2, SYS_unhandled_double_exc
1:	simcall				// let simulator/debugger report unhandled exception
#  else
1:
#  endif
	j	1b			// infinite loop

	// NOTE:  a non-minimalist vector may choose to
	// process the double exception in the vector itself
	// (by default, much more space is allocated to double
	// exception vectors than to most other vectors);
	// or, to jump to a double exception handler located
	// elsewhere.  If only the normal case of double
	// exceptions occurring within a window handler is
	// being handled, then it is safe to use EXCSAVE_1 to
	// do this jump (window handlers don't use EXCSAVE_1).
	// For example:
	//
	//	wsr	a0, EXCSAVE_1
	//	movi	a0, _DoubleExceptionFromVector
	//	jx	a0
	//
	//	.text
	//	.align	4
	//	.global _DoubleExceptionFromVector
	//_DoubleExceptionFromVector:
	//	...


	.size	_DoubleExceptionVector, . - _DoubleExceptionVector
	.text
	.end	literal_prefix

#endif /* have double exceptions */

