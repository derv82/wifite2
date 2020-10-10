/* exc-sethandler.c - register an exception handler in XTOS */

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
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"


#if XCHAL_HAVE_EXCEPTIONS

extern void	_xtos_c_wrapper_handler(void);	/* assembly-level handler for C handlers */
extern void	_xtos_unhandled_exception(void); /* assembly-level handler for exceptions
						   with no registered handler */
extern void	_xtos_p_none(void);		/* default/empty C handler */


extern _xtos_handler _xtos_c_handler_table[];
extern _xtos_handler _xtos_exc_handler_table[];

/*
 *  Register a C handler for the specified general exception
 *  (specified EXCCAUSE value).
 */
_xtos_handler _xtos_set_exception_handler( int n, _xtos_handler f )
{
    _xtos_handler ret;

    if( (unsigned) n >= XCHAL_EXCCAUSE_NUM )
	return 0;
    if( f == 0 )
	f = &_xtos_p_none;
    ret = _xtos_c_handler_table[n];
    _xtos_exc_handler_table[n] = ( (f == &_xtos_p_none)
				 ? &_xtos_unhandled_exception
				 : &_xtos_c_wrapper_handler );
    _xtos_c_handler_table[n] = f;
    if( ret == &_xtos_p_none )
	ret = 0;

    return ret;
}

#endif /* XCHAL_HAVE_EXCEPTIONS */

