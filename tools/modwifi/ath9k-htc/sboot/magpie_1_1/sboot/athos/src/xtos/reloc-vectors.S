// reloc-vector.S  -  Relocatable Vectors section
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/reloc-vectors.S#3 $

// Copyright (c) 2007-2010 Tensilica Inc.
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
 *  This file is only used if the relocatable vectors option is enabled.
 */

#include <xtensa/coreasm.h>
#include <xtensa/config/system.h>

#if XCHAL_HAVE_VECBASE

	.section	.RelocatableVectors.text, "ax"

	.global	_RelocVectors
_RelocVectors:

//if XCHAL_RESET_VECBASE_OVERLAP ...
# if XSHAL_VECTORS_PACKED \
  && (XCHAL_RESET_VECTOR0_VADDR == XCHAL_VECBASE_RESET_VADDR \
   || XCHAL_RESET_VECTOR1_VADDR == XCHAL_VECBASE_RESET_VADDR)
#  define JUMP_TO_RESET	1
	j	.Ljump_to_reset
# endif

# if XCHAL_HAVE_WINDOWED
#  define NO_SECTION_DIRECTIVES	1
#  define WINDOW_BASE_VECOFS	0
#  include "window-vectors.S"
# endif

#if XCHAL_HAVE_DEBUG && XCHAL_HAVE_EXCEPTIONS
# if XCHAL_DEBUGLEVEL == 2
#  define _Level2Vector	_DebugExceptionVector
# elif XCHAL_DEBUGLEVEL == 3
#  define _Level3Vector	_DebugExceptionVector
# elif XCHAL_DEBUGLEVEL == 4
#  define _Level4Vector	_DebugExceptionVector
# elif XCHAL_DEBUGLEVEL == 5
#  define _Level5Vector	_DebugExceptionVector
# elif XCHAL_DEBUGLEVEL == 6
#  define _Level6Vector	_DebugExceptionVector
# endif
#endif

# if XCHAL_HAVE_INTERRUPTS
#  if XCHAL_NUM_INTLEVELS >= 2
	.org	XCHAL_INTLEVEL2_VECOFS
	j	_Level2Vector
#  endif
#  if XCHAL_NUM_INTLEVELS >= 3
	.org	XCHAL_INTLEVEL3_VECOFS
	j	_Level3Vector
#  endif
#  if XCHAL_NUM_INTLEVELS >= 4
	.org	XCHAL_INTLEVEL4_VECOFS
	j	_Level4Vector
#  endif
#  if XCHAL_NUM_INTLEVELS >= 5
	.org	XCHAL_INTLEVEL5_VECOFS
	j	_Level5Vector
#  endif
#  if XCHAL_NUM_INTLEVELS >= 6
	.org	XCHAL_INTLEVEL6_VECOFS
	j	_Level6Vector
#  endif
#  if XCHAL_HAVE_NMI
	.org	XCHAL_NMI_VECOFS
	j	_NMIExceptionVector
#  endif
# endif
# if XCHAL_HAVE_EXCEPTIONS
	.org	XCHAL_KERNEL_VECOFS
	j	_KernelExceptionVector
	.org	XCHAL_USER_VECOFS
	j	_UserExceptionVector
	.org	XCHAL_DOUBLEEXC_VECOFS
	j	_DoubleExceptionVector
# endif

//	Put literals here.

//	Put actual handlers here.

# if JUMP_TO_RESET
	.align	4
	.literal	rvec, _ResetVector
.Ljump_to_reset:
	l32r	a2, rvec
	jx	a2
# endif

	.size	_RelocVectors, . - _RelocVectors

	.text

#endif /* XCHAL_HAVE_VECBASE */

