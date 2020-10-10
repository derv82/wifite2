// null-alloca.S  -  Stub for Unused Alloca (MOVSP) Handler
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/null-alloca.S#3 $

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


	//  Redirect alloca (MOVSP) exceptions as not handled, when
	//  that functionality is not needed.  Done this way, a user can
	//  just specify this small handler to override the default one.

	.text
	.weak	_xtos_unhandled_exception
	.global	_xtos_alloca_handler
_xtos_alloca_handler:
	movi	a3, _xtos_unhandled_exception
1:	beqz	a3, 1b
	jx	a3
	.size	_xtos_alloca_handler, . - _xtos_alloca_handler

