// crt1-sim.S
// For the Xtensa simulator target, this code sets up the C calling context
// and calls main()  (via __clibrary_start).
// Control arrives here at _start from the reset vector or from crt0-app.S.

// Copyright (c) 1998-2010 Tensilica Inc.
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

#include <xtensa/simboard.h>
#include <xtensa/simcall.h>
#include <xtensa/coreasm.h>
#include "xtos-internal.h"


// Exports
.global _start

// Imports
//   __clibrary_init	from C library (eg. newlib or uclibc)
//   exit		from C library
//   main		from user application
//   __stack		from linker script (see LSP Ref Manual)

.type	__clibrary_init, @function
.type	main, @function
.type	exit, @function


// Macros to abstract away ABI differences

#if __XTENSA_CALL0_ABI__
# define CALL	call0
# define ARG1	a2	/* 1st outgoing call argument */
# define ARG2	a3	/* 2nd outgoing call argument */
# define ARG3	a4	/* 3rd outgoing call argument */
# define ARG4	a5	/* 4th outgoing call argument */
# define ARG5	a6	/* 5th outgoing call argument */
#else
# define CALL	call4
# define ARG1	a6	/* 1st outgoing call argument */
# define ARG2	a7	/* 2nd outgoing call argument */
# define ARG3	a8	/* 3rd outgoing call argument */
# define ARG4	a9	/* 4th outgoing call argument */
# define ARG5	a10	/* 5th outgoing call argument */
#endif

		.data
		.weak	_start_envp	// allow overriding
		.align	4
_start_envp:	.word	0		// empty environ



	.text
	.align 4

_start:
	//  _start is typically NOT at the beginning of the text segment --
	//  it is always called from either the reset vector or other code
	//  that does equivalent initialization (such as crt0-app.S).
	//
	//  Assumptions on entry to _start:
	//	- low (level-one) and medium priority interrupts are disabled
	//	  via PS.INTLEVEL and/or INTENABLE (PS.INTLEVEL is expected to
	//	  be zeroed, to potentially enable them, before calling main)
	//	- C calling context not initialized:
	//	  - PS not initialized
	//	  - SP not initialized
	//	- the following are initialized:
	//	  - LITBASE, cache attributes, WindowBase, WindowStart,
	//	    CPENABLE, FP's FCR and FSR, EXCSAVE[n]

	// Keep a0 zero.  It is used to initialize a few things.
	// It is also the return address, where zero indicates
	// that the frame used by _start is the bottommost frame.
	//
	movi	a0, 0		// keep this register zero.

#if XTOS_RESET_UNNEEDED
#include "reset-unneeded.S"
#endif


	// Initialize the stack pointer.
	// See the "ABI and Software Conventions" chapter in the
	// Xtensa ISA Reference manual for details.

	// NOTE: Because the _start routine does not use any memory in its
	// stack frame, and because all of its CALL instructions use a
	// window size of 4, the stack frame for _start can be empty.
	movi	sp, __stack

	// reserve stack space for
	//    - argv array
	//    - argument strings
	movi	a2, SYS_iss_argv_size
	simcall		// returns size of argv[] + its strings in a2
#if XCHAL_HAVE_PIF
	// The stack only needs 16-byte alignment.
	// However, here we round up the argv size further to 128 byte multiples
	// so that in most cases, variations in argv[0]'s path do not result in
	// different stack allocation.  Otherwise, such variations can impact
	// execution timing (eg. due to cache effects etc) for the same code and data.
	// If we have a PIF, it's more likely the extra required space is okay.
	addi	a2, a2, 127
	srli	a2, a2, 7
	slli	a2, a2, 7
#else
	// Keep stack 16-byte aligned.
	addi	a2, a2, 15
	srli	a2, a2, 4
	slli	a2, a2, 4
#endif
	// No need to use MOVSP because we have no caller (we're the
	// base caller); in fact it's better not to use MOVSP in this
	// context, to avoid unnecessary ALLOCA exceptions and copying
	// from undefined memory:
	//   sub     a3, sp, a2
	//   movsp   sp, a3
	sub	sp, sp, a2


	/*
	 *  Now that sp (a1) is set, we can set PS as per the application
	 *  (user vector mode, enable interrupts, enable window exceptions if applicable).
	 */
#if XCHAL_HAVE_EXCEPTIONS
# ifdef __XTENSA_CALL0_ABI__
	movi	a3, PS_UM		// PS.WOE = 0, PS.UM = 1, PS.EXCM = 0, PS.INTLEVEL = 0
# else  
	movi	a3, PS_UM|PS_WOE	// PS.WOE = 1, PS.UM = 1, PS.EXCM = 0, PS.INTLEVEL = 0
# endif
	wsr	a3, PS
	rsync
#endif


	/*  The new ISS simcall only appeared after RB-2007.2:  */
#if !XCHAL_HAVE_BOOTLOADER && (XCHAL_HW_MAX_VERSION > XTENSA_HWVERSION_RB_2007_2)	/* pre-LX2 cores only */
	/*
	 *  Clear the BSS (uninitialized data) segments.
	 *  This code supports multiple zeroed sections (*.bss).
	 *  For speed, we clear memory using an ISS simcall
	 *  (see crt1-boards.S for more generic BSS clearing code).
	 */
	movi 	a6, _bss_table_start
	movi 	a7, _bss_table_end
	bgeu  	a6, a7, .Lnobss
.Lbssloop:
	movi	a2, SYS_memset
	l32i 	a3, a6, 0	// arg1 = fill start address
	movi	a4, 0		// arg2 = fill pattern
	l32i 	a5, a6, 4	// get end address
	addi   	a6, a6, 8	// next bss table entry
	sub	a5, a5, a3	// arg3 = fill size in bytes
	simcall			// memset(a3,a4,a5)
	bltu  	a6, a7, .Lbssloop	// loop until end of bss table
.Lnobss:
#endif


	/* 
	 *  Call __clibrary_init to initialize the C library:
	 *
	 *  void __clibrary_init(int argc, char ** argv, char ** environ, 
	 *		void(*init_func)(void), void(*fini_func)(void));
	 */	

	// Get argv with the arguments from the ISS
	mov	a3, sp		// tell simcall where to write argv[]
	movi	a2, SYS_iss_set_argv
	simcall			// write argv[] array at a3

	movi	a2, SYS_iss_argc
	simcall			// put argc in a2	


//	Alternative smaller code for Xtensa TX.
//	Many starting with simulation assume a full C env, so NOT DONE FOR NOW.
//
//#if XCHAL_HAVE_HALT
//
//	//  Assume minimalist environment for memory-constrained TX cores.
//	//  No C library or board initialization, and no call to exit().
//	//  However, in the interest of software regressions, for now we
//	//  still pass parameters to main (but not the rarely used envp).
//
//	//mov	ARG1, a2		// argc already in a2.
//	mov	ARG2, sp		// argv
//	CALL	main
//	halt
//
//#else /* !HALT */
//	...


#if __XTENSA_CALL0_ABI__
	mov 	a12, a2			// save argc (a2 is ARG1)
#else
	mov 	ARG1, a2		// argc
#endif
	mov	ARG2, sp		// argv
	movi 	ARG3, _start_envp	// envp
	movi 	ARG4, _init		// _init
	movi	ARG5, _fini		// _fini
	CALL	__clibrary_init

	//  Call:   int main(int argc, char ** argv, char ** environ);
#if __XTENSA_CALL0_ABI__
	mov 	ARG1, a12		// argc
#else
	mov	ARG1, a2		// argc
#endif
	mov	ARG2, sp		// argv
	movi	ARG3, _start_envp	// envp = [0]
	CALL	main
	//  The return value is the same register as the first outgoing argument.
	CALL	exit			// exit with main's return value
	// Does not return here.

	.size	_start, . - _start


// Local Variables:
// mode:fundamental
// comment-start: "// "
// comment-start-skip: "// *"
// End:
