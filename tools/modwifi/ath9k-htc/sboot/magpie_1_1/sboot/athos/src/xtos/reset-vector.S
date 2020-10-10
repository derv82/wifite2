// reset-vector.S  --  Xtensa Reset Vector
// $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/reset-vector.S#4 $

// Copyright (c) 1999-2010 Tensilica Inc.
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
#include <xtensa/cacheasm.h>
#include <xtensa/cacheattrasm.h>
#include <xtensa/xtensa-xer.h>
#include <xtensa/config/specreg.h>
#include <xtensa/config/system.h>	/* for XSHAL_USE_ABSOLUTE_LITERALS only */
#include "xtos-internal.h"

// The following reset vector avoids initializing certain registers already
// initialized by processor reset.
// Some of the registers reset by the processor include:
//   CACHEATTR or relevant TLB state
//   IBREAKENABLE		Debug
//   LCOUNT			Loops
//   PC				Core
//   PS				Core
//   ICOUNT			Debug
//   ICOUNTLEVEL		Debug
//   VECBASE			Relocatable vectors
//   (and various others, depending on hardware version)


	.begin	literal_prefix	.ResetVector
	.section		.ResetVector.text, "ax"

	.align	4
	.global	_ResetVector
_ResetVector:

# if 0	/* if XCHAL_HAVE_HALT */
	//  In theory, minimal reset vector for Xtensa TX (assuming bootloader to clear BSS).
	//  In practice we let crt*.S decide whether to do more (e.g. for sim LSP)
	//  and we might unpack below for ROMing LSPs.
	movi	sp, __stack	// setup the stack
	call0	main		// assume declared as "void main(void)" (no args)
	halt			// toodaloo
# endif

#if (!XCHAL_HAVE_HALT || defined(XTOS_UNPACK)) && XCHAL_HAVE_IMEM_LOADSTORE
	//  NOTE:
	//
	//  IMPORTANT:  If you move the _ResetHandler portion to a section
	//  other than .ResetVector.text that is outside the range of
	//  the reset vector's 'j' instruction, the _ResetHandler symbol
	//  and a more elaborate j/movi/jx sequence are needed in
	//  .ResetVector.text to dispatch to the new location.

	j	_ResetHandler

	.size	_ResetVector, . - _ResetVector

# if XCHAL_HAVE_HALT
	//  Xtensa TX: reset vector segment is only 4 bytes, so must place the
	//  unpacker code elsewhere in the memory that contains the reset vector.
#  if XCHAL_RESET_VECTOR_VADDR == XCHAL_INSTRAM0_VADDR
	.section .iram0.text, "ax"
#  elif XCHAL_RESET_VECTOR_VADDR == XCHAL_INSTROM0_VADDR
	.section .irom0.text, "ax"
#  elif XCHAL_RESET_VECTOR_VADDR == XCHAL_URAM0_VADDR
	.section .uram0.text, "ax"
#  else
#   warning "Xtensa TX reset vector not at start of iram0, irom0, or uram0 -- ROMing LSPs may not work"
	.text
#  endif
# endif

	.align	4
	.literal_position	// tells the assembler/linker to place literals here

	.align	4
	.global	_ResetHandler
_ResetHandler:
#endif

#if !XCHAL_HAVE_HALT

	/*
	 *  Even if the processor supports the non-PC-relative L32R option,
	 *  it will always start up in PC-relative mode.  We take advantage of
	 *  this, and use PC-relative mode at least until we're sure the .lit4
	 *  section is in place (which is sometimes only after unpacking).
	 */
	.begin	no-absolute-literals


	movi	a0, 0		// a0 is always 0 in this code, used to initialize lots of things

#if XCHAL_HAVE_INTERRUPTS	// technically this should be under !FULL_RESET, assuming hard reset
	wsr	a0, INTENABLE	// make sure that interrupts are shut off (*before* we lower PS.INTLEVEL and PS.EXCM!)
#endif

#if !XCHAL_HAVE_FULL_RESET

#if XCHAL_HAVE_CCOUNT && (XCHAL_HW_MIN_VERSION < XTENSA_HWVERSION_RB_2006_0)	/* pre-LX2 cores only */
	wsr	a0, CCOUNT	// not really necessary, but nice; best done very early
#endif

	// For full MMU configs, put page table at an unmapped virtual address.
	// This ensures that accesses outside the static maps result
	// in miss exceptions rather than random behaviour.
	// Assumes XCHAL_SEG_MAPPABLE_VADDR == 0 (true in released MMU).
#if XCHAL_ITLB_ARF_WAYS > 0 || XCHAL_DTLB_ARF_WAYS > 0
	wsr	a0, PTEVADDR
#endif

	// Debug initialization
	//
	// NOTE: DBREAKCn must be initialized before the combination of these two things:
	//       any load/store, and a lowering of PS.INTLEVEL below DEBUG_LEVEL.
	//       The processor already resets IBREAKENABLE appropriately.
	//
#if XCHAL_HAVE_DEBUG
# if XCHAL_NUM_DBREAK
#  if XCHAL_NUM_DBREAK >= 2
	wsr	a0, DBREAKC1
#  endif
	wsr	a0, DBREAKC0
	dsync			// wait for WSRs to DBREAKCn to complete
# endif

# if XCHAL_HW_MIN_VERSION < XTENSA_HWVERSION_RA_2004_1	/* pre-LX cores only */
	//  Starting in Xtensa LX, ICOUNTLEVEL resets to zero (not 15), so no need to initialize it.
	//  Prior to that we do, otherwise we get an ICOUNT exception, 2^32 instructions after reset.
	rsr	a2, ICOUNTLEVEL	// are we being debugged? (detected by ICOUNTLEVEL not 15, or dropped below 12)
	bltui	a2, 12, 1f	// if so, avoid initializing ICOUNTLEVEL which drops single-steps through here
	wsr	a0, ICOUNTLEVEL	// avoid ICOUNT exceptions
	isync			// wait for WSR to ICOUNTLEVEL to complete
1:
# endif
#endif

#endif /* !XCHAL_HAVE_FULL_RESET */

#if XCHAL_HAVE_ABSOLUTE_LITERALS
	//  Technically, this only needs to be done under !FULL_RESET, assuming hard reset:
	wsr	a0, LITBASE
	rsync
#endif

#if XCHAL_HAVE_PRID && XCHAL_HAVE_S32C1I
	/* Core 0 initializes the XMP synchronization variable, if present. This operation needs to
	   happen as early as possible in the startup sequence so that the other cores can be released
	   from reset.	*/
	.weak _ResetSync
	movi 	a2, _ResetSync	// address of sync variable
	rsr.prid a3		// core and multiprocessor ID
	extui 	a3, a3, 0, 8	// extract core ID (FIXME: need proper constants for PRID bits to extract)
	beqz	a2, 1f		// skip if no sync variable
	bnez	a3, 1f		// only do this on core 0
	s32i	a0, a2, 0	// clear sync variable
1:
#endif
#if XCHAL_HAVE_EXTERN_REGS && XCHAL_HAVE_MP_RUNSTALL
	/* On core 0, this releases other cores.  On other cores this has no effect, because
	   runstall control is unconnected.  */
	movi	a2, XER_MPSCORE
	wer	a0, a2
#endif

	/*
	 *  For processors with relocatable vectors, apply any alternate
	 *  vector base given to xt-genldscripts, which sets the
	 *  _memmap_vecbase_reset symbol accordingly.
	 */
#if XCHAL_HAVE_VECBASE
	movi	a2, _memmap_vecbase_reset	/* note: absolute symbol, not a ptr */
	wsr	a2, vecbase
#endif

#if XCHAL_HAVE_S32C1I && (XCHAL_HW_MIN_VERSION >= XTENSA_HWVERSION_RC_2009_0)	/* have ATOMCTL ? */
# if XCHAL_DCACHE_IS_COHERENT
	movi	a3, 0x25		/* MX -- internal for writeback, RCW otherwise */
# else
	movi	a3, 0x15		/* non-MX -- always RCW */
# endif
	wsr	a3, ATOMCTL
#endif

#if XCHAL_HAVE_INTERRUPTS && XCHAL_HAVE_DEBUG
	rsil	a2, 1		// lower PS.INTLEVEL here to make reset vector easier to debug
#endif

	/*
	 *  Initialize the caches.
	 *  We do this very early because performance can increase by
	 *  an order of magnitude when we enable the caches, which
	 *  greatly affects start up time, including the mini-loader below.
	 *  This is also required before we jump into any cacheable region.
	 *  Without caches, these macros expand to nothing (see cacheasm.h).
	 */
	icache_reset	a2, a3
	dcache_reset	a2, a3

#if XCHAL_HAVE_PREFETCH
	/* Enable cache prefetch if present.  */
	movi	a2, XCHAL_CACHE_PREFCTL_DEFAULT
	wsr	a2, PREFCTL
#endif

	/*
	 *  Now "enable" the caches, for unpacking to occur a bit more
	 *  efficiently.  Only relevant for region protection and XEA1.
	 *
	 *  The _memmap_cacheattr_reset symbol's value (address) is defined
	 *  by the LSP's linker script, as generated by xt-genldscripts.
	 *
	 *  (NOTE:  for configs that don't have CACHEATTR or region protection,
	 *   ie. for full MMUs, there is no equivalent cache attribute layout,
	 *   and the following code has no effect.  We assume for now that the
	 *   application restricts itself to the static TLB entries, i.e. to
	 *   virtual addresses 0xD0000000 thru 0xFFFFFFFF.)
	 */
#if XCHAL_HAVE_CACHEATTR || XCHAL_HAVE_MIMIC_CACHEATTR || XCHAL_HAVE_XLT_CACHEATTR \
		|| (XCHAL_HAVE_PTP_MMU && XCHAL_HAVE_SPANNING_WAY)
	movi	a2, _memmap_cacheattr_reset	/* note: absolute symbol, not a ptr */
	cacheattr_set				/* set CACHEATTR from a2 (clobbers a3-a8) */
#endif

#if XCHAL_HAVE_EXTERN_REGS && XCHAL_DCACHE_IS_COHERENT
	/* Opt into coherence if present.  */
	movi	a3, 1
	movi	a2, XER_CCON
	wer	a3, a2
#endif

#endif /* !XCHAL_HAVE_HALT */

	/*
	 *  Unpack code and data (eg. copy ROMed segments to RAM, vectors into
	 *  their proper location, etc).
	 */

#if defined(XTOS_UNPACK)
	movi	a2, _rom_store_table
	beqz	a2, unpackdone
unpack:	l32i	a3, a2, 0	// start vaddr
	l32i	a4, a2, 4	// end vaddr
	l32i	a5, a2, 8	// store vaddr
	addi	a2, a2, 12
	bgeu	a3, a4, upnext	// skip unless start < end
uploop:	l32i 	a6, a5, 0
	addi	a5, a5, 4
	s32i	a6, a3, 0
	addi	a3, a3, 4
	bltu	a3, a4, uploop
	j	unpack
upnext:	bnez	a3, unpack
	bnez	a5, unpack
#endif /* XTOS_UNPACK */

unpackdone:

#if defined(XTOS_UNPACK) || defined(XTOS_MP)
	/*
	 *  If writeback caches are configured and enabled, unpacked data must be
	 *  written out to memory before trying to execute it:
	 */
	dcache_writeback_all	a2, a3, 0
	icache_sync		a2	// ensure data written back is visible to i-fetch
	/*
	 *  Note:  no need to invalidate the i-cache after the above, because we
	 *  already invalidated it further above and did not execute anything within
	 *  unpacked regions afterwards.  [Strictly speaking, if an unpacked region
	 *  follows this code very closely, it's possible for cache-ahead to have
	 *  cached a bit of that unpacked region, so in the future we may need to
	 *  invalidate the entire i-cache here again anyway.]
	 */
#endif


#if !XCHAL_HAVE_HALT	/* skip for TX */

	/*
	 *  Now that we know the .lit4 section is present (if got unpacked)
	 *  (and if absolute literals are used), initialize LITBASE to use it.
	 */
#if XCHAL_HAVE_ABSOLUTE_LITERALS && XSHAL_USE_ABSOLUTE_LITERALS
	/*
	 *  Switch from PC-relative to absolute (litbase-relative) L32R mode.
	 *  Set LITBASE to 256 kB beyond the start of the literals in .lit4
	 *  (aligns to the nearest 4 kB boundary, LITBASE does not have bits 1..11)
	 *  and set the enable bit (_lit4_start is assumed 4-byte aligned).
	 */
	movi	a2, _lit4_start + 0x40001
	wsr	a2, LITBASE
	rsync
#endif /* have and use absolute literals */
	.end	no-absolute-literals		// we can now start using absolute literals


//  Technically, this only needs to be done pre-LX2, assuming hard reset:
# if XCHAL_HAVE_WINDOWED && defined(__XTENSA_WINDOWED_ABI__)
	//  Windowed register init, so we can call windowed code (eg. C code).
	movi	a1, 1
	wsr	a1, WINDOWSTART
	//  The processor always clears WINDOWBASE at reset, so no need to clear it here.
	//  It resets WINDOWSTART to 1 starting with LX2.0/X7.0 (RB-2006.0).
	//  However, assuming hard reset is not yet always practical, so do this anyway:
	wsr	a0, WINDOWBASE
	rsync
	movi	a0, 0			// possibly a different a0, clear it
# endif

#if XCHAL_HW_MIN_VERSION < XTENSA_HWVERSION_RB_2006_0	/* only pre-LX2 needs this */
	// Coprocessor option initialization
# if XCHAL_HAVE_CP
	//movi	a2, XCHAL_CP_MASK	// enable existing CPs
	//  To allow creating new coprocessors using TC that are not known
	//  at GUI build time without having to explicitly enable them,
	//  all CPENABLE bits must be set, even though they may not always
	//  correspond to a coprocessor.
	movi	a2, 0xFF	// enable *all* bits, to allow dynamic TIE
	wsr	a2, CPENABLE
# endif

	// Floating point coprocessor option initialization (at least
	// rounding mode, so that floating point ops give predictable results)
# if XCHAL_HAVE_FP && !XCHAL_HAVE_VECTORFPU2005
#  define FCR	232	/* floating-point control register (user register number) */
#  define FSR	233	/* floating-point status register (user register number) */
	rsync		/* wait for WSR to CPENABLE to complete before accessing FP coproc state */
	wur	a0, FCR	/* clear FCR (default rounding mode, round-nearest) */
	wur	a0, FSR	/* clear FSR */
# endif
#endif /* pre-LX2 */


	/*
	 *  Initialize medium and high priority interrupt dispatchers:
	 */
#if HAVE_XSR

/*  For asm macros; works for positive a,b smaller than 1000:  */
# define GREATERTHAN(a,b)	(((b)-(a)) & ~0xFFF)

# ifndef XCHAL_DEBUGLEVEL		/* debug option not selected? */
#  define XCHAL_DEBUGLEVEL	99	/* bogus value outside 2..6 */
# endif

	.macro	init_vector	level
	  .if GREATERTHAN(XCHAL_NUM_INTLEVELS+1,\level)
	    .if XCHAL_DEBUGLEVEL-\level
	      .weak   _Level&level&FromVector
	      movi    a4, _Level&level&FromVector
	      wsr     a4, EXCSAVE+\level
	      .if GREATERTHAN(\level,XCHAL_EXCM_LEVEL)
		movi    a5, _Pri_&level&_HandlerAddress
		s32i    a4, a5, 0
		/*  If user provides their own handler, that handler might
		 *  not provide its own _Pri_<n>_HandlerAddress variable for
		 *  linking handlers.  In that case, the reference below
		 *  would pull in the XTOS handler anyway, causing a conflict.
		 *  To avoid that, provide a weak version of it here:
		 */
		.pushsection .data, "aw"
		.global  _Pri_&level&_HandlerAddress
		.weak   _Pri_&level&_HandlerAddress
		.align	4
		_Pri_&level&_HandlerAddress: .space 4
		.popsection
	      .endif
	    .endif
	  .endif
	.endm

	init_vector	2
	init_vector	3
	init_vector	4
	init_vector	5
	init_vector	6

#endif /*HAVE_XSR*/


	/*
	 *  Complete reset initialization outside the vector,
	 *  to avoid requiring a vector that is larger than necessary.
	 *  This 2nd-stage startup code sets up the C Run-Time (CRT) and calls main().
	 *  
	 *  Here we use call0 not because we expect any return, but
	 *  because the assembler/linker dynamically sizes call0 as
	 *  needed (with -mlongcalls) which it doesn't with j or jx.
	 *  Note:  This needs to be call0 regardless of the selected ABI.
	 */
	call0	_start		// jump to _start (in crt1-*.S)
	/* does not return */

#else /* XCHAL_HAVE_HALT */

	j	_start		// jump to _start (in crt1-*.S)
				// (TX has max 64kB IRAM, so J always in range)

	//  Paranoia -- double-check requirements / assumptions of this Xtensa TX code:
# if !defined(__XTENSA_CALL0_ABI__) || !XCHAL_HAVE_FULL_RESET || XCHAL_HAVE_INTERRUPTS || XCHAL_HAVE_CCOUNT || XCHAL_DTLB_ARF_WAYS || XCHAL_HAVE_DEBUG || XCHAL_HAVE_S32C1I || XCHAL_HAVE_ABSOLUTE_LITERALS || XCHAL_DCACHE_SIZE || XCHAL_ICACHE_SIZE || XCHAL_HAVE_PIF || XCHAL_HAVE_WINDOWED
#  error "Halt architecture (Xtensa TX) requires: call0 ABI, all flops reset, no exceptions or interrupts, no TLBs, no debug, no S32C1I, no LITBASE, no cache, no PIF, no windowed regs"
# endif

#endif /* XCHAL_HAVE_HALT */


#if (!XCHAL_HAVE_HALT || defined(XTOS_UNPACK)) && XCHAL_HAVE_IMEM_LOADSTORE
	.size	_ResetHandler, . - _ResetHandler
#else
	.size	_ResetVector, . - _ResetVector
#endif

	.text
	.global xthals_hw_configid0, xthals_hw_configid1
	.global xthals_release_major, xthals_release_minor
	.end	literal_prefix
