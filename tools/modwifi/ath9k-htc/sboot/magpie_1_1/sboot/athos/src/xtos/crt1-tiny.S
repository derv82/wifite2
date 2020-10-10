// crt1-tiny.S
//
// This is a reduced version of the code in crt1-boards.S .
// For most hardware / boards, this code sets up the C calling context
// (setting up stack, PS, and clearing BSS) and calls main().
// It has some limitations (see LSP Ref Manual for details) such as:
//	- does not setup the C library (...)
//	- does not call C++ static constructors and destructors
//	- only clears .bss , not other *.bss sections
//
// Control arrives here at _start from the reset vector or from crt0-app.S.

// Copyright (c) 1998-2010 Tensilica Inc.
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


// Imports
//	__stack			from linker script (see LSP Ref Manual)
//	_bss_start		from linker script (see LSP Ref Manual)
//	_bss_end		from linker script (see LSP Ref Manual)
//	main			from user application



#ifdef __XTENSA_CALL0_ABI__
# define CALL		call0
#else
# define CALL		call4
#endif


/**************************************************************************/

	.text
	.global	_start
_start:
	//  _start is typically NOT at the beginning of the text segment --
	//  it is always called from either the reset vector or other code
	//  that does equivalent initialization (such as crt0-app.S).
	//  See crt1-boards.S for assumptions on entry to _start ,
	//  and for comments on what is being done in this file.

#if !XCHAL_HAVE_HALT || !XCHAL_HAVE_BOOTLOADER		// not needed for Xtensa TX
	movi	a0, 0		// mark base of call stack
#endif

	movi	sp, __stack	// setup the stack

#if XCHAL_HAVE_EXCEPTIONS
# ifdef __XTENSA_CALL0_ABI__
	movi	a3, PS_UM		// PS:  WOE=0, UM=1, EXCM=0, INTLEVEL=0
# else  
	movi	a3, PS_UM|PS_WOE	// PS:  WOE=1, UM=1, EXCM=0, INTLEVEL=0
# endif
	wsr	a3, PS			// setup PS for the application
	rsync
#endif


	// Clear the BSS (uninitialized data) segment.
	//
	// This code only supports .bss, not multiple *.bss sections.
	// Corresponding code in crt1-boards.S does, and is faster but bigger.

#if !XCHAL_HAVE_BOOTLOADER
	movi	a6, _bss_start
	movi	a7, _bss_end
	bgeu	a6, a7, 2f
1:	s32i	a0, a6, 0
	addi	a6, a6, 4
	bltu	a6, a7, 1b
2:
#endif

	//  We can now call C code, the C calling environment is initialized.
	//  This tiny C runtime assumes main is declared as "void main(void)"
	//  rather than with the usual argc,argv.  So there are no arguments.

	CALL	main

	//  In this tiny C runtime, main() is not expected to return.
	//  If it does, just loop forever.

	//CALL	xthal_dcache_all_writeback	// sync dirty dcaches to memory
	//extw			// sync TIE queues/ports/etc (LX or later only)

.L0:
#if XCHAL_HAVE_DEBUG
	break	1, 15		// give control to debugger
#elif XCHAL_HAVE_HALT
	halt
#endif
	j	.L0

	.size	_start, . - _start


// Local Variables:
// mode:fundamental
// comment-start: "// "
// comment-start-skip: "// *"
// End:
