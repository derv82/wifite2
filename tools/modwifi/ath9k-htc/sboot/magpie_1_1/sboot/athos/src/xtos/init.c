/* init.c - context initialization */

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
#if XCHAL_NUM_CONTEXTS > 1
#include <stdlib.h>
#endif



#if 0 /* XCHAL_NUM_CONTEXTS > 1 */
extern	void	_xtos_setup_context(int context_num, SetupInfo *info);
extern	void	_xtos_start_context(void);

/*
 *  Sets up a context for running code.
 *
 *  Returns PC at which to set the new context, or 0 on error.
 */
unsigned	_xtos_init_context(int context_num, int stack_size,
				   _xtos_handler_func *start_func, int arg1)
{
    SetupInfo info;

    /*  Allocate stack:  */
    char *sp;
    char *stack = malloc(stack_size);
    if (stack == NULL)
	return 0;

    /*  Setup stack for call8:  */
    sp = stack + stack_size - 16;
    *(unsigned*)(sp - 12) = (unsigned)(sp + 32);

    info.sp = (unsigned)sp;
    info.funcpc = (unsigned)start_func;
    info.arg1 = arg1;
    _xtos_setup_context(context_num, &info);
    return (unsigned) &_xtos_start_context;
}
#endif /* multiple contexts */

