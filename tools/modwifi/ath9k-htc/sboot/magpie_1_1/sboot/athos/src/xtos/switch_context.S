/* switch_contexts.S - setup for multiple contexts */

/*
 * Copyright (c) 2003-2010 Tensilica Inc.
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

#include <xtensa/coreasm.h>
#include <xtensa/xtruntime-frames.h>

#if XCHAL_NUM_CONTEXTS > 1


/*
 *  void	_xtos_setup_context(int context_num, StartInfo *info);
 */
	.align 4 
	.global _xtos_setup_context
	.type _xtos_setup_context,@function
_xtos_setup_context:
	abi_entry
#if XCHAL_HAVE_INTERRUPTS
	rsil	a5, 15			/* disable interrupts so we can use EXCSAVE_1 */
#else
	rsr	a5, PS			/* just read PS */
#endif
	wsr	a3, EXCSAVE_1		/* save pointer to new context info */
	s32i	a5, a3, INFO_prevps	/* save previous PS */
	movi	a4, ~0x01F00000		/* mask out PS.CTXT */
	slli	a2, a2, 20		/* shift up new PS.CTXT value */
	and	a4, a5, a4
	or	a4, a4, a2		/* new PS value */
	wsr	a4, PS
	rsync
	/*  We're now in the new context!  */
	movi	a0, 0
	movi	a1, 1
	wsr	a1, WINDOWSTART
	wsr	a0, WINDOWBASE
	rsync
	rsr	a9, EXCSAVE_1		/* get pointer to context info */
	movi	a0, 0			/* terminate call frames */
	l32i	a1, a9, INFO_sp		/* get stack pointer */
	l32i	a10, a9, INFO_arg1	/* get start function's arguments... */
	l32i	a8, a9, INFO_funcpc	/* get start function's address */
	/*  Okay, now switch back to context zero:  */
	l32i	a9, a9, INFO_prevps	/* retrieve previous PS */
	wsr	a9, PS
	rsync
	/*  Back to original context!  */
	abi_return

	.size	_xtos_setup_context, . - _xtos_setup_context



	/*
	 *  This is the first thing to be executed in the new context
	 *  by explicit setting of PC:
	 */
	.align 4 
	.global _xtos_start_context
_xtos_start_context:
#ifdef __XTENSA_CALL0_ABI__
	Crash the assembler here:  I think this is wrong.
	callx0	a8
#else
	callx8	a8
#endif
1:	nop
	j	1b	/* do nothing until context 0 exits */
	.size	_xtos_start_context, . - _xtos_start_context


#endif /* XCHAL_NUM_CONTEXTS > 1 */

