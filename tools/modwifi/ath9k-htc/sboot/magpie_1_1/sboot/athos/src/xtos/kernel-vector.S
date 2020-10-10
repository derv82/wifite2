// kernel-vector.S  -  Kernel Vector for General Exceptions
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/kernel-vector.S#3 $

// Copyright (c) 1999-2002, 2004, 2006, 2010 Tensilica Inc.
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
 *  General exceptions in kernel vector mode (PS.UM==0) go to this kernel
 *  vector.  This kernel vector does very little.
 *  Under normal operation of the single-threaded runtime ("XTOS"), kernel
 *  vectored general exceptions do not occur, so nothing needs to be done.
 *  However when debugging, such as when writing exception and
 *  interrupt handlers, kernel vectored exceptions may occur.
 *  They are usually the sign of a bug, so here we take a breakpoint
 *  (if debug option enabled) or take drastic action (infinite loop)
 *  otherwise.
 *
 *  XTOS does not allow exceptions in interrupt or exception handlers.
 *  If it did, a more elaborate kernel vector handler would be needed.
 *  See the Xtensa Microprocessor Programmer's Guide for an
 *  example of how to implement such a kernel vector handler.
 */

#include <xtensa/coreasm.h>
#include <xtensa/config/system.h>
#ifdef SIMULATOR
#include <xtensa/simcall.h>
#endif

#if XCHAL_HAVE_EXCEPTIONS

	.begin	literal_prefix	.KernelExceptionVector
	.section		.KernelExceptionVector.text, "ax"

	.align 4
	.global _KernelExceptionVector
_KernelExceptionVector:
# if XCHAL_HAVE_DEBUG
1:	break	1,0			// unexpected kernel exception
# elif defined(SIMULATOR)
	wsr	a2, EXCSAVE1		// save a2 where simulator expects it
	movi	a2, SYS_unhandled_kernel_exc
1:	simcall				// let simulator/debugger report unhandled exception
# else
1:
# endif
	j	1b			// infinite loop - unexpected kernel exception

	.size	_KernelExceptionVector, . - _KernelExceptionVector
	.text
	.end	literal_prefix

#endif /* XCHAL_HAVE_EXCEPTIONS */

