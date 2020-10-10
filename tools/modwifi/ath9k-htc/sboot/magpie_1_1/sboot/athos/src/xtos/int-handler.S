// int-handler.S  -  Interrupt Handler Template (for levels > 1)
// $Id: //depot/main/Xtensa/OS/xtos/inth-template.S#1 $

// Copyright (c) 2003-2004, 2006 Tensilica Inc.
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


// To use this template file, define a macro called _INTERRUPT_LEVEL
// to be the interrupt priority level of the vector, then include this file.
// The default Makefile defines _INTERRUPT_LEVEL when assembling this file
// for each medium and high priority interrupt level.


#include <xtensa/coreasm.h>
#include "xtos-internal.h"


#if XCHAL_HAVE_INTERRUPTS

# if INTERRUPT_IS_HI(_INTERRUPT_LEVEL)

#  if _INTERRUPT_LEVEL > XTOS_LOCKLEVEL
   /*  Not safe to dispatch interrupts in C above XTOS_LOCKLEVEL,
    *  so default to assembly high-priority interrupt handlers template
    *  in this case (with the default XTOS_LOCKLEVEL this never happens):
    */
#   include "int-highpri-template.S"
#  else
   /*  Dispatch high-priority interrupt handlers in C:  */
#   include "int-highpri-dispatcher.S"
#  endif

# elif INTERRUPT_IS_MED(_INTERRUPT_LEVEL)

#  include "int-medpri-dispatcher.S"

# elif (_INTERRUPT_LEVEL <= XCHAL_NUM_INTLEVELS) && (_INTERRUPT_LEVEL != XCHAL_DEBUGLEVEL)
# error INTERNAL ERROR:	Interrupt priority levels > 1 must be either hi or medium priority!
# endif

#endif /* XCHAL_HAVE_INTERRUPTS */
