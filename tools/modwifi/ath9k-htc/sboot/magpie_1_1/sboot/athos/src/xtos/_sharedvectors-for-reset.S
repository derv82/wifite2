// _sharedvectors-for-reset.S  --  Reference to pull in a shared reset vector
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/_sharedvectors-for-reset.S#2 $

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

/*  Multicore build flows can use this file (_sharedvectors-for-reset.o)
    by copying it to _sharedvectors.o early in the linker search path
    (to override the default one), and updating the memory map or linker
    scripts accordingly.
    This file pulls in a sharable reset vector (typically
    shared-reset-vector.S, which requires the PRID option).  */

.global	_SharedResetVector

/*  The following allows this object file to be pulled in by reference:  */
.text
.global	_xtos_sharedvectors_ref_
.set	_xtos_sharedvectors_ref_, 0

