// shared-reset-vector.S  --  Sharable Reset Vector (requires PRID option)

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

	//  Populate this processor's entry in the reset table.
	//  The core instance specific LSP should put this section
	//  in the correct location within the table.
	//
	.section .ResetTable.rodata, "a"
	.word	_ResetHandler

	//  This sharable reset code assumes RC-2009.0 or later hardware,
	//  to guarantee that no processor state initialization is required
	//  prior to doing loads etc.
	//  Total size is 28 bytes (or 27 with density option).
	//  By necessity, none of these bytes vary by core instance;
	//  the appropriate reset table entry is selected using PRID.
	//
#if XCHAL_HAVE_PRID
	.section .SharedResetVector.text, "ax"
	.begin	no-absolute-literals

	.align	4
	.global	_SharedResetVector
_SharedResetVector:
	j	.LSharedResetHandler

	.align	4
	.literal_position

	.align	4
.LSharedResetHandler:
	rsr.prid   a0		// get processor ID (16 bits)
	movi	a1, _ResetTable_base
	extui	a0, a0, 0, 4	// ID of core within the multiprocessor (FIXME: need proper constant...)
	addx4	a1, a0, a1
	l32i	a1, a1, 0
	jx	a1		// jump to core-specific initialization

	.size	_SharedResetVector, . - _SharedResetVector
	.end	no-absolute-literals
#endif

