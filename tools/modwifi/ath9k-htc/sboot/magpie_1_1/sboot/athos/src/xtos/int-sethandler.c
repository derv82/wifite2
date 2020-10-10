/* int-sethandler.c - register an interrupt handler in XTOS */

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


#if XCHAL_HAVE_INTERRUPTS
/*
 *  Table of interrupt handlers.
 *  NOTE:  if the NSA/NSAU instructions are configured, then to save
 *  a few cycles in the interrupt dispatcher code, the
 *  _xtos_interrupt_table[] array is filled in reverse.
 *  IMPORTANT:  Use the MAPINT() macro defined in xtos-internal.h to index entries in this array.
 */
extern XtosIntHandlerEntry	_xtos_interrupt_table[XCHAL_NUM_INTERRUPTS];
extern void			_xtos_unhandled_interrupt();
#endif


_xtos_handler _xtos_set_interrupt_handler_arg( int n, _xtos_handler f, void *arg )
{
#if XCHAL_HAVE_INTERRUPTS
    XtosIntHandlerEntry *entry;
    _xtos_handler old;

    if( n < 0 || n >= XCHAL_NUM_INTERRUPTS )
	return 0;	/* invalid interrupt number */
    if( Xthal_intlevel[n] > XTOS_LOCKLEVEL )
	return 0;	/* priority level too high to safely handle in C */
    entry = _xtos_interrupt_table + MAPINT(n);
    old = entry->handler;
    if (f) {
	entry->handler = f;
	entry->arg = arg;
    } else {
	entry->handler = &_xtos_unhandled_interrupt;
	entry->arg = (void*)n;
    }
    return ((old == &_xtos_unhandled_interrupt) ? 0 : old);
#else
    return 0;
#endif
}


_xtos_handler _xtos_set_interrupt_handler( int n, _xtos_handler f )
{
    return _xtos_set_interrupt_handler_arg( n, f, (void*) n );
}


#if 0
/*
 *  User vector mode exception handler for the LEVEL1_INTERRUPT cause.
 *  NOTE:  this is now implemented in assembler for performance.
 *  This C handler is left as an example interrupt dispatcher written in C.
 *  The actual handler in int-lowpri-dispatcher.S is more fully featured.
 */
UserFrame* _xtos_p_level1int_handler( UserFrame* uf /*, int cause */ )
{
#if XCHAL_HAVE_INTERRUPTS
    unsigned int ints;
    unsigned int index;

    ints = xthal_get_interrupt();
# if XTOS_VIRTUAL_INTENABLE
    ints &= _xtos_enabled;
# else
    ints &= xthal_get_intenable();
# endif
    for( index = 0 ; ints != 0 ; ints >>= 1, index++ )
    {
	if( ints & 1 )
	{
	    void (*f)();

	    /*
	     *  Clear interrupt (in case it's edge-triggered or software or write-error).
	     *  This must be done *before* processing the interrupt.
	     */
	    xthal_set_intclear( 1 << index );

	    f = _xtos_interrupt_table[MAPINT(index)].handler;
	    if( f )
		f( _xtos_interrupt_table[MAPINT(index)].arg /*, uf, index*/ );
	}
    }
#endif /*XCHAL_HAVE_INTERRUPTS*/
    return uf;
}
#endif

