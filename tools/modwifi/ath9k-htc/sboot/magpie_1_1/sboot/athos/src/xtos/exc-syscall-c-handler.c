/* exc-syscall-c-handler.c - SYSCALL instruction XTOS handler in C */

/*
 * Copyright (c) 1999-2006 Tensilica Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include <xtensa/config/core.h>
#include "xtos-internal.h"


/*
 *  User vector mode exception handler for the SYSCALL cause.
 *
 *  NOTE:  This function is NOT used by default.  The assembly-level
 *  handler version of this function is normally used instead.
 *  This function is provided as an example only.
 *  To use it instead of the default assembly-level version,
 *  you can register it using _xtos_set_exception_handler().
 *  For example:
 *
 *	#include <xtensa/xtruntime.h>
 *	#include <xtensa/corebits.h>
 *	_xtos_set_exception_handler( EXCCAUSE_SYSCALL,
 *			(_xtos_handler)_xtos_p_syscall_handler );
 */
UserFrame* _xtos_p_syscall_handler( UserFrame *uf /*, int cause */ )
{
    uf->pc += 3;	/* skip SYSCALL instruction */

#if XCHAL_HAVE_LOOPS
    /*
     *  If the SYSCALL instruction was the last instruction in the body
     *  of a zero-overhead loop, then we should decrement the loop count
     *  and resume execution at the head of the loop.
     */

    if( uf->pc == uf->lend && uf->lcount != 0 )
    {
	uf->lcount--;
	uf->pc = uf->lbeg;
    }
#endif /*XCHAL_HAVE_LOOP*/

    /*
     *  Handle the system call.
     *
     *  A typical SYSCALL handler uses code such as this to handle
     *  the system call, where the operation to be done is determined
     *  by the a2 register.  Parameters to the operation are typically
     *  passed in address registers a3 and up.  Results are typically
     *  returned in a2.  (See Linux source code for example.)
     */
    switch( uf->a2 ) {
	case 0:
	    /*  Spill register windows to the stack.  */
	    /*
	     *  The Xtensa architecture reserves the a2==0 condition as a request
	     *  to flush (spill) register windows to the stack.  The current exception
	     *  handling implementation never spills windows to the stack (it used
	     *  to always spill, not true anymore), so we have to spill windows
	     *  explicitly here.  (Note that xthal_window_spill() spills windows
	     *  that are part of the interrupt handling context, that don't
	     *  really need to be spilled, but that's harmless other than being
	     *  less than optimally efficient.)
	     *
	     *  Also, be nice to programmers here.  If they're
	     *  building for Call0 ABI, silently do nothing for
	     *  syscall a2==0.
	     */
#ifdef __XTENSA_WINDOWED_ABI__
	    xthal_window_spill();
#endif
	    break;

	default:
	    uf->a2 = -1 /*ENOSYS*/;	/* system call not supported */
	    break;
    }

    return( uf );
}

