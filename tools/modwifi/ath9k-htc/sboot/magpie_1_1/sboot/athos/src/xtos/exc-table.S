// exc-table.S - general exception C handler table

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
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"


#if XCHAL_HAVE_EXCEPTIONS

	/*
	 *  Table of exception handlers (in C) for user vectored exceptions.
	 *  Provides entries for all possible 64 exception causes
	 *  currently allowed for in the EXCCAUSE register.
	 */
	.data
	.global	_xtos_c_handler_table
	.align 4
_xtos_c_handler_table:
	.rept	XCHAL_EXCCAUSE_NUM
	.word	_xtos_p_none
	.endr

	/*
	 *  Default/empty exception C handler.
	 *  This is just a placeholder for exception causes with no registered
	 *  handler; it normally never gets executed.
	 *  NOTE:  control goes first to the debugger if one is present;
	 *	   see _xtos_unhandled_exception in exc-unhandled.S .
	 */
	.text
	.align	4
	.global	_xtos_p_none
	.type	_xtos_p_none,@function
_xtos_p_none:
	abi_entry
	//  Do nothing.
	abi_return
	.size	_xtos_p_none, . - _xtos_p_none

#endif /* XCHAL_HAVE_EXCEPTIONS */

