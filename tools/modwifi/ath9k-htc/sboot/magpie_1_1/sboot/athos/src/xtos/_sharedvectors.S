// _sharedvectors.S  --  Reference symbols to pull in any shared vectors
//			 (default version, used when not sharing any vector)
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/_sharedvectors.S#2 $

// Copyright (c) 2008 Tensilica Inc.
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

/*  Not present by default.  Multicore build flows build/use a custom
    version of _sharedvectors.o that may pull in shared vectors.  */

/* .global	_SharedResetVector */

/*  The following allows this object file to be pulled in by reference:  */
.text
.global	_xtos_sharedvectors_ref_
.set	_xtos_sharedvectors_ref_, 0

