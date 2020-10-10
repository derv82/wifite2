// intlevel-restore.S - Interrupt related assembler code - _xtos_restore_intlevel

// Copyright (c) 2004-2010 Tensilica Inc.
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
#include <xtensa/config/specreg.h>
#include "xtos-internal.h"


/***************************************************************************
 *  void  _xtos_restore_intlevel(unsigned restoreval);
 *
 *  _xtos_restore_intlevel() restores the current interrupt level
 *  according to a value returned by _xtos_set_intlevel() or
 *  _xtos_set_min_intlevel() (or one of the corresponding macros).
 *
 *  NOTE:  In XEA2, this function may restore the entire PS register, not
 *  just the PS.INTLEVEL field.  If some other PS field(s) must be changed
 *  and kept intact across restoring PS.INTLEVEL (this is generally unlikely),
 *  use the XTOS_RESTORE_JUST_INTLEVEL() macro instead (which is slower).
 *
 *  NOTE:  In XEA1, this function is implemented further below, identically
 *  to _xtos_set_vpri().
 *
 *  NOTE:  The macro form of this function (XTOS_RESTORE_INTLEVEL())
 *  is recommended (for XEA2 configs or where the config is unknown)
 *  because it may be more efficient.
 */

	.text
	.global	_xtos_restore_intlevel
	.type	_xtos_restore_intlevel,@function
#if XCHAL_HAVE_XEA2
	.align 4
_xtos_restore_intlevel:
	abi_entry
# if XCHAL_HAVE_INTERRUPTS
	wsr	a2, PS		// restore PS
	rsync			// wait for WSR to PS to complete
# endif
	abi_return
	.size	_xtos_restore_intlevel, . - _xtos_restore_intlevel
#endif



/***************************************************************************
 *  _xtos_set_vpri() is used to set the current virtual priority from C code;
 *  it can be called from the application or from a C interrupt handler.
 */

	.global	_xtos_set_vpri
	.type	_xtos_set_vpri,@function
	.align 4
_xtos_set_vpri:
#if XCHAL_HAVE_XEA1
_xtos_restore_intlevel:
#endif
	abi_entry
#if XCHAL_HAVE_INTERRUPTS && XTOS_VIRTUAL_INTENABLE
	mov	a3, a2
	movi	a4, _xtos_intstruct
	xtos_lock	a7	// MUST USE highest address register of function to avoid window overflows in critical section
	l32i	a2, a4, XTOS_VPRI_ENABLED_OFS	// return old xtos_vpri_enabled (current vpri)
	l32i	a5, a4, XTOS_ENABLED_OFS	// a3 = xtos_enabled
	s32i	a3, a4, XTOS_VPRI_ENABLED_OFS	// set new xtos_vpri_enabled (current vpri)
	and	a5, a5, a3			// a5 = xtos_enabled & xtos_vpri_enabled
	wsr	a5, INTENABLE
	xtos_unlock	a7
#endif /*XCHAL_HAVE_INTERRUPTS*/
	abi_return
	.size	_xtos_set_vpri, . - _xtos_set_vpri

