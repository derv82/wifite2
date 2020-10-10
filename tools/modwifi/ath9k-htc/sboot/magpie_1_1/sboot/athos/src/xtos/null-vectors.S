// null-vectors.S  -  Stubs for Unused Vectors and Handlers
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/null-vectors.S#3 $

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


// NOTE:  The simulator version of this file is currently not used,
// i.e. the SIMULATOR macro is never defined when assembling this file.
// The relevant simulator code is left here for illustrative purposes only.


#include <xtensa/coreasm.h>
#include "xtos-internal.h"
#ifdef SIMULATOR
#include <xtensa/simcall.h>
#endif

	//  These are just tiny non-functional vectors and handlers for when
	//  their functionality is not being used.  They just try to signal
	//  the debugger that an unhandled exception or interrupt occurred,
	//  and otherwise just spin in a loop.
	//
	//  For interrupts levels above DEBUGLEVEL, lowering PS.INTLEVEL
	//  for break to work is tricky, and not always possible in a
	//  generic fashion without interfering with normal program execution.
	//  So for now we don't do it.


#if defined(__SPLIT__user)

# if XCHAL_HAVE_EXCEPTIONS
	.begin	literal_prefix	.UserExceptionVector
	.section		.UserExceptionVector.text, "ax"
	.align 4
	.global _UserExceptionVector
_UserExceptionVector:
#  if XCHAL_HAVE_DEBUG
	break	1, 1	// unexpected user-vectored general exception
#  endif
1:	j	1b	// infinite loop - unexpected user-vectored exception
	.size	_UserExceptionVector, . - _UserExceptionVector
	.end	literal_prefix
# endif

#elif defined(__SPLIT__level1int)

	.text
	.global	_xtos_l1int_handler
_xtos_l1int_handler:
	movi	a3, _xtos_unhandled_exception
	jx	a3
	.size	_xtos_l1int_handler, . - _xtos_l1int_handler

#elif defined(__SPLIT__level2)

# if (XCHAL_NUM_INTLEVELS >= 2) && (XCHAL_DEBUGLEVEL != 2)
	.begin	literal_prefix	.Level2InterruptVector
	.section		.Level2InterruptVector.text, "ax"
	.align 4
	.global	_Level2Vector
_Level2Vector:
#  if XCHAL_HAVE_DEBUG && (XCHAL_DEBUGLEVEL > 2)
	break	1, 2	// unexpected high-priority interrupt
#  elif defined(SIMULATOR)
	wsr	a2, EXCSAVE_2
	movi	a2, SYS_unhandled_highpri_interrupt
	simcall		// let simulator/debugger report unhandled level-2 interrupt
#  endif
1:	j	1b	// infinite loop - unexpected level-2 interrupt
	.size	_Level2Vector, . - _Level2Vector
	.text
	.end	literal_prefix
# endif /* level 2 */


#elif defined(__SPLIT__level3)

# if (XCHAL_NUM_INTLEVELS >= 3) && (XCHAL_DEBUGLEVEL != 3)
	.begin	literal_prefix	.Level3InterruptVector
	.section		.Level3InterruptVector.text, "ax"
	.align 4
	.global	_Level3Vector
_Level3Vector:
#  if XCHAL_HAVE_DEBUG && (XCHAL_DEBUGLEVEL > 3)
	break	1, 2	// unexpected high-priority interrupt
#  elif defined(SIMULATOR)
	wsr	a2, EXCSAVE_3
	movi	a2, SYS_unhandled_highpri_interrupt
	simcall		// let simulator/debugger report unhandled level-3 interrupt
#  endif
1:	j	1b	// infinite loop - unexpected level-3 interrupt
	.size	_Level3Vector, . - _Level3Vector
	.text
	.end	literal_prefix
# endif /* level 3 */


#elif defined(__SPLIT__level4)

# if (XCHAL_NUM_INTLEVELS >= 4) && (XCHAL_DEBUGLEVEL != 4)
	.begin	literal_prefix	.Level4InterruptVector
	.section		.Level4InterruptVector.text, "ax"
	.align 4
	.global	_Level4Vector
_Level4Vector:
#  if XCHAL_HAVE_DEBUG && (XCHAL_DEBUGLEVEL > 4)
	break	1, 2	// unexpected high-priority interrupt
#  elif defined(SIMULATOR)
	wsr	a2, EXCSAVE_4
	movi	a2, SYS_unhandled_highpri_interrupt
	simcall		// let simulator/debugger report unhandled level-4 interrupt
#  endif
1:	j	1b	// infinite loop - unexpected level-4 interrupt
	.size	_Level4Vector, . - _Level4Vector
	.text
	.end	literal_prefix
# endif /* level 4 */


#elif defined(__SPLIT__level5)

# if (XCHAL_NUM_INTLEVELS >= 5) && (XCHAL_DEBUGLEVEL != 5)
	.begin	literal_prefix	.Level5InterruptVector
	.section		.Level5InterruptVector.text, "ax"
	.align 4
	.global	_Level5Vector
_Level5Vector:
#  if XCHAL_HAVE_DEBUG && (XCHAL_DEBUGLEVEL > 5)
	break	1, 2	// unexpected high-priority interrupt
#  elif defined(SIMULATOR)
	wsr	a2, EXCSAVE_5
	movi	a2, SYS_unhandled_highpri_interrupt
	simcall		// let simulator/debugger report unhandled level-5 interrupt
#  endif
1:	j	1b	// infinite loop - unexpected level-5 interrupt
	.size	_Level5Vector, . - _Level5Vector
	.text
	.end	literal_prefix
# endif /* level 5 */


#elif defined(__SPLIT__level6)

# if (XCHAL_NUM_INTLEVELS >= 6) && (XCHAL_DEBUGLEVEL != 6)
	.begin	literal_prefix	.Level6InterruptVector
	.section		.Level6InterruptVector.text, "ax"
	.align 4
	.global	_Level6Vector
_Level6Vector:
#  if XCHAL_HAVE_DEBUG && (XCHAL_DEBUGLEVEL > 6)
	break	1, 2	// unexpected high-priority interrupt
#  elif defined(SIMULATOR)
	wsr	a2, EXCSAVE_6
	movi	a2, SYS_unhandled_highpri_interrupt
	simcall		// let simulator/debugger report unhandled level-6 interrupt
#  endif
1:	j	1b	// infinite loop - unexpected level-6 interrupt
	.size	_Level6Vector, . - _Level6Vector
	.text
	.end	literal_prefix
# endif /* level 6 */


#endif /* split */

