/*
 * xtos-params.h  --  user-settable parameters for XTOS single-threaded run-time
 *
 * Copyright (c) 2002, 2004, 2006-2007 Tensilica Inc.
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

#ifndef XTOS_PARAMS_H
#define XTOS_PARAMS_H

/*
 *  IMPORTANT NOTE.
 *  This file contains XTOS parameters that may be modified
 *  according to needs.  HOWEVER, any modifications are NOT
 *  supported.  Handling of parameters other than the defaults
 *  provided in the original version of this file are for
 *  illustrative and educational purposes only.  If you do
 *  change the parameters here-in (which requires rebuilding
 *  XTOS), please verify the resulting code extensively
 *  before even considering its use in production code.
 *
 *  To rebuild XTOS, see instructions in the Xtensa System Software
 *  Reference Manual.  The following sequence is no longer supported.
 *
 *	cd <config_dir>/xtensa-elf/src/handlers
 *	xt-make clean
 *	xt-make
 *	xt-make install
 *
 *  (Note: the last step installs the modified XTOS in *ALL*
 *  LSPs that normally include XTOS.  You may prefer copying
 *  the generated files to your own custom LSP instead.  Or
 *  better yet, also make a copy of all source files and maintain
 *  them somewhere completely separate -- which may require
 *  minor adjustments to the makefile.)
 *
 *  PERFORMANCE TUNING:
 *  To slightly improve performance of interrupt dispatching,
 *  you can do some combination of the following:
 *	- change XTOS_SUBPRI to zero
 *	- change XTOS_SUBPRI_GROUPS to zero
 *	- change XTOS_SUBPRI_ORDER to XTOS_SPO_ZERO_HI
 *	- change XTOS_DEBUG_PC to zero
 *	- change XTOS_INT_FAIRNESS to zero
 *	- change XTOS_CNEST to zero
 *  There are non-trivial trade-offs in making such changes however,
 *  such as loss of support (see important note above), loss of
 *  interrupt scheduling fairness, loss of ability to traceback
 *  interrupt handlers across interrupted code when debugging them,
 *  loss of supported for nested C functions, etc.
 */


/*
 *  Lower LOCKLEVEL to XCHAL_EXCM_LEVEL for improved interrupt latency
 *  if you don't register C handlers for high-priority interrupts and your
 *  high-priority handlers don't touch INTENABLE nor virtual priorities.
 *
 *  XTOS_LOCKLEVEL is less meaningful but still relevant if XEA2 and SUBPRI is zero,
 *  ie. if INTENABLE doesn't get virtualized (XTOS_VIRTUAL_INTENABLE not set);
 *  in this case, it is the interrupt level at which INTENABLE accesses are guarded,
 *  so that interrupt handlers up to this level can safely manipulate INTENABLE.
 */
#define XTOS_LOCKLEVEL		XCHAL_NUM_INTLEVELS	/* intlevel of INTENABLE register virtualization
							   (minimum is EXCM_LEVEL) */

/*
 *  NOTE:  the following four parameters (SUBPRI, SUBPRI_GROUPS, SUBPRI_ORDER, INT_FAIRNESS)
 *  are irrelevant and ignored for interrupt vectors to which only one interrupt is mapped.
 */

#define XTOS_SUBPRI		1	/* set to 0 if you don't need sub-prioritization
					   within level-one interrupts via software;
					   for XEA2 configs, this might improve performance of
					   certain sections of code, because INTENABLE register
					   virtualization becomes unnecessary in this case */

/*  Ignored unless SUBPRI set:  */
#define XTOS_SUBPRI_GROUPS	1	/* support selective grouping of interrupts at the same priority */

#define XTOS_SUBPRI_ORDER	XTOS_SPO_ZERO_LO	/* one of XTOS_SPO_ZERO_LO, XTOS_SPO_ZERO_HI */

/*  Ignored if SUBPRI set but SUBPRI_GROUPS is not (single interrupt per subpri),
 *  or if single interrupt configured at level/vector:  */
#define XTOS_INT_FAIRNESS	1	/* disable round-robin/fifo scheduling of interrupt
					   handlers of a given level or sub-priority */


#define XTOS_DEBUG_PC		1	/* enable nice stack traceback showing interrupted code
					   when debugging interrupt or exception handler;
					   not implemented for high-priority handlers, or
					   for call0 ABI */

#define XTOS_CNEST		1	/* enable support for nested C functions
					   (save/restore nested C function call-chain pointer) */

/*  Current compilers only use ACC (not MRn) when MAC16 is enabled, so you can leave this 0 for performance:  */
#define XTOS_SAVE_ALL_MAC16	0	/* set to save/restore MAC16 MRn registers */

/*  Setting this might be useful to clear X's in hardware simulation a bit earlier, but
 *  should not be needed in production code:  */
#define XTOS_RESET_UNNEEDED	0	/* set to reset more registers than are really needed */

#endif /* XTOS_PARAMS_H */

