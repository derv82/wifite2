// int-initlevel.S  -  Routines used to pull-in interrupt dispatch code
//	in the tiny-rt LSP.
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/int-initlevel.S#3 $

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


// To assemble this template file, define a macro called _INTERRUPT_LEVEL
// to be the interrupt level of the vector.  We use the same template for both
// high-level and medium-level interrupts, but not debug level.


#include <xtensa/coreasm.h>
#include "xtos-internal.h"


#if XCHAL_HAVE_INTERRUPTS && (_INTERRUPT_LEVEL <= XCHAL_NUM_INTLEVELS) && (_INTERRUPT_LEVEL != XCHAL_DEBUGLEVEL)

	//  Nothing to do at runtime.  This function only has effect
	//  at link-time.
	//
	.text
	.global	LABEL(_xtos_dispatch_level,_interrupts)
	.align 4
LABEL(_xtos_dispatch_level,_interrupts):
	abi_entry
	abi_return
	.size	LABEL(_xtos_dispatch_level,_interrupts), . - LABEL(_xtos_dispatch_level,_interrupts)

	//  This reference is what does the work of pulling-in the
	//  relevant interrupt vector at the specified level.
	//  This is only needed in the tiny-rt LSP.
	//
# if _INTERRUPT_LEVEL == 1
	.global	_need_level1int_
# else
	.global	LABEL(_Level,Vector)
# endif

#endif /* XCHAL_HAVE_INTERRUPTS */
