/* memerror-vector.S  --  Memory Error Exception Vector and Handler */

/* $Id: //depot/rel/Cottonwood/Xtensa/OS/xtos/memerror-vector.S#3 $ */

/*
 * Copyright (c) 2006-2010 Tensilica Inc.
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

//#include <xtensa/config/specreg.h>
#include <xtensa/coreasm.h>
#include <xtensa/corebits.h>

#if XCHAL_HAVE_MEM_ECC_PARITY
# if defined(__SPLIT__vector)

	//  Place this code in the memory error exception vector:
	.begin	literal_prefix	.MemoryExceptionVector
	.section		.MemoryExceptionVector.text, "ax"

	.global _MemErrorVector
	.align 4
_MemErrorVector:
# if 0 /* XCHAL_HAVE_DEBUG */
	//  Memory errors raise PS.INTLEVEL above DEBUGLEVEL, so
	//  break instructions have no effect within them (debug
	//  exceptions are masked).  So leave commented out for now.
	break	1, 5		// unhandled memory error exception
# endif
	wsr	a0, MESAVE
	movi	a0, _MemErrorHandler
	jx	a0

	.size	_MemErrorVector, . - _MemErrorVector
	.text
	.end	literal_prefix


# elif defined(__SPLIT__handler)

/*
 *  Some rules and assumptions:
 *
 *	Anything that can interrupt this handler (e.g. NMI):
 *		- must not lock or unlock cache lines
 */


#define ICACHE_WAYWIDTH	(XCHAL_ICACHE_SETWIDTH + XCHAL_ICACHE_LINEWIDTH)	/* LICT's "iis" */
#define DCACHE_WAYWIDTH	(XCHAL_DCACHE_SETWIDTH + XCHAL_DCACHE_LINEWIDTH)	/* LDCT's "dis" */
/*  NOTE:  Memory ECC/parity is not supported on XLMI or on local ROMs:  */
#define HAVE_LOCAL_RAM	(XCHAL_NUM_DATARAM || XCHAL_NUM_INSTRAM /*|| XCHAL_NUM_URAM || XCHAL_NUM_XLMI*/)


	//.lcomm	_MemErrorSave, 8
	.comm	_MemErrorSave, 8, 4

	.text
	.align 4
	.global	_MemErrorHandler
_MemErrorHandler:
	rsr	a0, MESR
	bbsi.l	a0, MESR_DME_SHIFT, .L_fatal_dme
# if XCHAL_ICACHE_SIZE > 0 || XCHAL_DCACHE_SIZE > 0
	bbsi.l	a0, MESR_MEMTYPE_SHIFT+1, .L_cache	// branch if error on a cache
# endif
	//  Error in a local memory.
# if HAVE_LOCAL_RAM
	bbsi.l	a0, MESR_ERRTYPE_SHIFT, .L_uncorrectable_local
	//  Correctable error in a local memory (IRAM or DRAM).
	//  (MEVADDR has all 32 bits, so XSR preserves a register:)
	xsr	a2, MEVADDR
	//  Note:  MEVADDR is always 4-byte aligned,
	//  so we can just do L32I/S32I to correct the error.
	//  However, that's not atomic, and NMI can store in between;
	//  that's usually a problem for D rather than I, avoid the
	//  issue using S32C1I if configured (else NMI must not write DataRAM!?!):
#  if (XCHAL_HAVE_S32C1I && (XCHAL_NUM_DATARAM /*|| XCHAL_NUM_URAM || XCHAL_NUM_XLMI*/))
	bbci.l	a0, MESR_MEMTYPE_SHIFT, .L_instram	// branch if error on InstRAM
	//  Unfortunately we need 3 registers to do S32C1I (data,addr,SCOMPARE1) so
	//  we need to save to _MemErrorSave:
	movi	a0, _MemErrorSave
	s32i	a4, a0, 0	// save a4
	l32i	a4, a2, 0	// load data (re-correct)
	rsr	a0, SCOMPARE1	// save SCOMPARE1
	wsr	a4, SCOMPARE1
	s32c1i	a4, a2, 0	// store if still contains same value (else other store corrected error)
	movi	a4, _MemErrorSave
	wsr	a0, SCOMPARE1	// restore SCOMPARE1
	l32i	a4, a4, 0	// restore a4
	j	2f
.L_instram:
#  endif
	l32i	a0, a2, 0	// load data (re-correct)
	s32i	a0, a2, 0	// store data to correct ECC bits
2:	xsr	a2, MEVADDR
# endif /* HAVE_LOCAL_RAM */
.L_done:
	rsr	a0, MESAVE
	rfme


	//  Weak reference:  if unresolved, links okay but with zero value:
	.weak	_xtos_merr_hook_fatal_dme
.L_fatal_dme:
	//  Fatal (unrecoverable) error, double memory exception
	movi	a0, _xtos_merr_hook_fatal_dme
1:	beqz	a0, 1b		// fatal double memory error, no hook, so infinite loop
	jx	a0		// jump to user hook, if present


# if HAVE_LOCAL_RAM
	//  Weak reference:  if unresolved, links okay but with zero value:
	.weak	_xtos_merr_hook_uncorrectable_local
.L_uncorrectable_local:
	//  Fatal (unrecoverable) error in IRAM or DRAM:  parity or uncorrectable ECC error
	movi	a0, _xtos_merr_hook_uncorrectable_local
1:	beqz	a0, 1b		// fatal memory error, no hook provided, so infinite loop
	jx	a0		// jump to user hook, if present
# endif


# if XCHAL_ICACHE_SIZE > 0 || XCHAL_DCACHE_SIZE > 0
.L_cache:
	//  Error in one of the caches.
# endif

# if XCHAL_ICACHE_SIZE > 0
#  if XCHAL_DCACHE_SIZE > 0
	bbsi.l	a0, MESR_MEMTYPE_SHIFT, .L_dcache	// branch if data cache error
#  endif
	//  Error in the instruction cache.
	bbsi.l	a0, MESR_ERRTYPE_SHIFT, .L_icache_noncorr	// branch if uncorrectable
	//  Correctable error in the instruction cache.
	xsr	a2, MEVADDR
	//  TODO FIXME: remove these 5 lines if waynum is in MEVADDR!? by using III if tag and IHI otherwise!?!?!?:
#  if XCHAL_ICACHE_WAYS > 1
	extui	a0, a0, MESR_WAYNUM_SHIFT, 2
	slli	a0, a0, ICACHE_WAYWIDTH
	slli	a2, a2, 32 - ICACHE_WAYWIDTH
	srli	a2, a2, 32 - ICACHE_WAYWIDTH
	or	a2, a2, a0
#  endif
	iii	a2, 0			// invalidate line (whole set!) if not locked
#  if XCHAL_ICACHE_LINE_LOCKABLE
	//  III has no effect if the line is locked; for that case, need to do more:
	lict	a0, a2
	bbci.l	a0, XCHAL_ICACHE_TAG_L_SHIFT, .L_icache_done	// branch if unlocked
	//  Correctable error in a locked instruction cache line.
	//  Fix both tag and one word, quicker than figuring out whether error is in tag or data:
	sict	a0, a2			// fix tag
	licw	a0, a2
	sicw	a0, a2			// fix data word
#  endif
.L_icache_done:
	xsr	a2, MEVADDR
	j	.L_done

.L_icache_noncorr:
	//  Non-correctable error in the instruction cache.
	bbsi.l	a0, MESR_MEMTYPE_SHIFT+2, .L_icache_tag_noncorr	// branch if tag error
	//  Non-correctable error in the instruction cache data.
	//  Just invalidate the line if we can.
#  if XCHAL_ICACHE_LINE_LOCKABLE
	//  If locked, need a different fix sequence.
	xsr	a2, MEVADDR

#   if XCHAL_ICACHE_WAYS > 1
	//  This sequence is shorter, but does not retain original MEVADDR so
	//  prevents subsequent use of instructions requiring a virtual address
	//  (such as LICW, IPFL, etc):
//	extui	a0, a0, MESR_WAYNUM_SHIFT, 2
//	slli	a0, a0, ICACHE_WAYWIDTH
//	slli	a2, a2, 32 - ICACHE_WAYWIDTH
//	srli	a2, a2, 32 - ICACHE_WAYWIDTH
//	or	a2, a2, a0

	extui	a0, a0, MESR_WAYNUM_SHIFT, 2	// id of way with mem error
	slli	a0, a0, ICACHE_WAYWIDTH
	xor	a0, a2, a0			// xor corresponding bits of addr
	extui	a0, a0, ICACHE_WAYWIDTH, 2	// take 2 xor'ed way bits
	or	a2, a2, a0			// save them at bottom of addr
	slli	a0, a0, ICACHE_WAYWIDTH
	xor	a2, a2, a0			// and change 2 way bits of addr
#   endif
	lict	a0, a2
	bbsi.l	a0, XCHAL_ICACHE_TAG_L_SHIFT, .L_icache_locked_uncor	// branch if locked
	//  Cache line is not locked, just invalidate:
#   if XCHAL_ICACHE_WAYS > 1
	iii	a2, 0
#   else
	ihi	a2, 0
#   endif
	j	.L_icache_done

	//  NOTE:  we don't use the LICW/SICW sequence below unless the line is locked,
	//	otherwise the i-cache line might get replaced between LICW and SICW
	//	(if we're not extremely careful), which would be disastrous.
	//	Also, for locked lines, LICW/SICW is much safer than IHU/IHI/IPFL
	//	because it doesn't leave a window where the line is unlocked;
	//	however, if the error is non-correctable, we have no choice.

.L_icache_locked_uncor:
	//  If locked and uncorrectable however, the only recourse is relocking.
	//  So we need to recover the virtual address so we can do IPFL.
	//  Note:  can't use MEPC instead of MEVADDR, because (a) it might not
	//  point to the correct cache line, and (b) it might be completely wrong
	//  in the case where the mem error happened e.g. during an LICW or IPFL.
#   if XCHAL_ICACHE_WAYS > 1
	//  Recover virtual address in a2:
	extui	a0, a2, 0, 2			// get saved xor'ed bits at bottom
	slli	a0, a0, ICACHE_WAYWIDTH		// line them up
	xor	a2, a2, a0			// restore original MEVADDR
#   endif
	ihu	a2, 0		// unlock line
	ihi	a2, 0		// invalidate line
	ipfl	a2, 0		// refetch-and-lock the line
	j	.L_icache_done
#  else /* LOCKABLE */
	rsr	a0, MEVADDR
	ihi	a0, 0		// invalidate that cache line
	j	.L_done
#  endif /* LOCKABLE */

.L_icache_tag_noncorr:
	//  Non-correctable error in the instruction cache tag.
	//  Just invalidate the tag or the entire set.
#  if XCHAL_ICACHE_LINE_LOCKABLE
	//  Note:  can't use either IIU or III, as these don't write the entire tag,
	//  so they'll get the exception again.  So, have to use SICT.
#   if XCHAL_ICACHE_WAYS > 1
	//  TODO FIXME: avoid this 8-line alternative if waynum is in MEVADDR!?:
	xsr	a2, MEVADDR
	extui	a0, a0, MESR_WAYNUM_SHIFT, 2
	slli	a0, a0, ICACHE_WAYWIDTH
	slli	a2, a2, 32 - ICACHE_WAYWIDTH
	srli	a2, a2, 32 - ICACHE_WAYWIDTH
	or	a2, a2, a0
	iiu	a2, 0		// unlock line ==> also invalidates! (I-side only)
	xsr	a2, MEVADDR
#   else
	rsr	a0, MEVADDR
	iiu	a0, 0		// unlock line ==> also invalidates! (I-side only)
#   endif
	// If line was locked, can't recover lock state, need external info to recover.
	// User can provide an assembler hook routine _xtos_merr_hook_icache_relock
	// to relock the icache at the index in a2:
	//	- any number of lines might still be locked at that index,
	//	  including all of them
	//	- no stack is provided, a0 must be used as starting point to
	//	  load a save area and saved registers as necessary
	//	- unless routine just does ret (i.e. does not modify any
	//	  register, only possible if it does nothing), it needs to
	//	  return by restoring all registers it modified, ending with:
	//		rsr	a0, MESAVE
	//		rfme
	//  CAVEAT EMPTOR:  this hook mechanism is subject to change.
	.weak	_xtos_merr_hook_icache_relock	// if unresolved, links with zero value
	movi	a0, _xtos_merr_hook_icache_relock
1:	beqz	a0, 1b		// if no hook to recover lock state on icache tag mem error, loop forever
	callx0	a0		// invoke user hook to relock i-cache (index in MEVADDR)
#  else
	rsr	a0, MEVADDR
	iii	a0, 0		// invalidate entire set
#  endif
	j	.L_done
# endif /* have ICACHE */


# if XCHAL_DCACHE_SIZE > 0
#  if XCHAL_ICACHE_SIZE > 0
.L_dcache:
#  endif
	//  Error in the data cache.
#  if XCHAL_DCACHE_IS_WRITEBACK || XCHAL_DCACHE_LINE_LOCKABLE
	bbsi.l	a0, MESR_ERRTYPE_SHIFT, .L_dcache_noncorr	// branch if uncorrectable
	//  Uncorrectable error on a writeback dcache might be unrecoverable:
#  endif
	bbsi.l	a0, MESR_MEMTYPE_SHIFT+2, .L_dcache_tag		// branch if tag error
	//  Error in the data cache data (correctable, or non-correctable in writethru+unlockable cache).
	//  MEVADDR always a real vaddr here; might point to cache-isolate mode area though.
#  if XCHAL_DCACHE_LINE_LOCKABLE
	//  Correctable error on lockable dcache data.
	//  If locked, need to refetch the line (or load/store its contents, which is less safe):
	xsr	a2, MEVADDR
#   if XCHAL_DCACHE_WAYS > 1
	//  Need some extra computation to get the correct dcache way's tag:
	movi	a0, _MemErrorSave
	s32i	a4, a0, 0	// save a4
	s32i	a5, a0, 4	// save a5
	rsr	a4, MESR
	extui	a4, a4, MESR_WAYNUM_SHIFT, 2
	slli	a4, a4, DCACHE_WAYWIDTH
	slli	a5, a2, 32 - DCACHE_WAYWIDTH
	srli	a5, a5, 32 - DCACHE_WAYWIDTH
	add	a4, a4, a5
	mov	a5, a0
	ldct	a0, a4
	l32i	a4, a5, 0	// restore a4
	l32i	a5, a5, 4	// restore a5
#   else
	ldct	a0, a2
#   endif
	//  FIXME:  if castout, a2 is a physical address! doesn't work with any address translation.
#   if 0 /* translation */
	movi	a4, _xtos_vmap_vaddr	// FIXME: do we need two variables for full MMU?
1:	beqz	a4, 1b		// if no vaddr to use, loop forever (FIXME: caxlt: could assume V==P)
	rdtlb1	a5, a4		// save current contents
	... clear lower bits of a4 ...
	xx = some function of a2
	wdtlb	xx, a4
	a2 = virtual address, i.e. some function of a2 and a4 ...
	... do the sequence below ...
	...
	wdtlb	a5, a4		// restore TLB entry
#   endif
	//  NOTE:  the following sequence leaves the line temporarily unlocked, if locked.
	//  We assume NMI handlers don't lock lines or rely on their being locked.
	//  We could have used "l32i a0,a2,0; s32i a0,a2,0" but that's not atomic on the data.
	dhu	a2, 0		// unlock the cache line, if locked
	dhwbi	a2, 0		// writeback and invalidate cache line
	bbci.l	a0, XCHAL_DCACHE_TAG_L_SHIFT, 1f
	dpfl	a2, 0		// re-prefetch-and-lock the cache line
1:	xsr	a2, MEVADDR
#  else /* LOCKABLE */
	//  Error in unlockable data cache data (correctable, or non-correctable in writethru cache).
	rsr	a0, MEVADDR
	//  USELESS NOTE:  if writethru dcache and NMI handlers don't store to this, we could use DHI instead:
	//  FIXME:  if castout, a0 is a physical address! doesn't work with any address translation.
	dhwbi	a0, 0		// writeback (if correctable) and invalidate that cache line
#  endif /* LOCKABLE */
	j	.L_done

.L_dcache_tag:
	//  Error in data cache tag (correctable, or non-correctable in writethru+unlockable cache).
	//  MEVADDR only contains cache index here (not waynum), don't expect a vaddr (the ISA
	//  says upper bits are undefined; actual hw does put a vaddr, but in future might not).
	//  Whether or not correctable, just invalidate the particular way's line:
	xsr	a2, MEVADDR
	//  NOTE: could remove these 5 lines if hw were designed with waynum in MEVADDR (but is not):
#  if XCHAL_DCACHE_WAYS > 1
	extui	a0, a0, MESR_WAYNUM_SHIFT, 2
	slli	a0, a0, DCACHE_WAYWIDTH
	slli	a2, a2, 32 - DCACHE_WAYWIDTH
	srli	a2, a2, 32 - DCACHE_WAYWIDTH
	or	a2, a2, a0
#  endif
#  if XCHAL_DCACHE_LINE_LOCKABLE
	ldct	a0, a2		// invalidate and unlock that cache tag
	bbci.l	a0, XCHAL_DCACHE_TAG_L_SHIFT, 1f	// branch if not locked
	sdct	a0, a2		// if locked, this safely writes whole tag
#  endif
1:	diwbi	a2, 0		// writeback (if correctable) and invalidate the line
	xsr	a2, MEVADDR
	j	.L_done



#  if XCHAL_DCACHE_IS_WRITEBACK || XCHAL_DCACHE_LINE_LOCKABLE
.L_dcache_noncorr:
	//  Uncorrectable error on a (writeback and/or lockable) data cache.
#   if XCHAL_DCACHE_IS_WRITEBACK
	//  On tag errors we don't know whether the line is dirty, so this is unrecoverable:
	bbsi.l	a0, MESR_MEMTYPE_SHIFT+2, .L_uncorrectable_dtag	// branch if tag error
	//  Castouts are by definition dirty, uncorrectable errors on these are unrecoverable:
	bbsi.l	a0, MESR_ACCTYPE_SHIFT, .L_uncorrectable_dirty	// branch if castout
	//  Note: could still be an error on dirty dcache data, also unrecoverable.
#   else
	bbsi.l	a0, MESR_MEMTYPE_SHIFT+2, .L_dcache_tag_noncorr	// branch if tag error
#   endif
	//  Uncorrectable error in dcache data.
	//  May be dirty or locked, so get tag to find out.
	xsr	a2, MEVADDR
#   if XCHAL_DCACHE_WAYS > 1
	extui	a0, a0, MESR_WAYNUM_SHIFT, 2	// id of way with mem error
	slli	a0, a0, DCACHE_WAYWIDTH
	xor	a0, a2, a0			// xor corresponding bits of addr
	extui	a0, a0, DCACHE_WAYWIDTH, 2	// take 2 xor'ed way bits
	or	a2, a2, a0			// save them at bottom of addr
	slli	a0, a0, DCACHE_WAYWIDTH
	xor	a2, a2, a0			// and change 2 way bits of addr
#   endif
	ldct	a0, a2			// get dcache tag
#   if XCHAL_DCACHE_IS_WRITEBACK
	bbsi.l	a0, XCHAL_DCACHE_TAG_D_SHIFT, .L_uncorrectable_dirty_2	// branch if dirty
#   endif
	//  Data cache line is clean.
#   if XCHAL_DCACHE_LINE_LOCKABLE
	bbsi.l	a0, XCHAL_DCACHE_TAG_L_SHIFT, .L_dcache_nc_locked
#   endif
	//  Data cache line is clean and unlocked.  Just invalidate it.
	//  FIXME:  any stores to this line by an NMI handler will be lost.
	//	On the other hand, if we use DHWBI, any stores by an NMI handler
	//	that don't happen to fix the error result in an unrecoverable castout.
	//	
#   if XCHAL_ICACHE_WAYS > 1
	//  Recover virtual address in a2:
	extui	a0, a2, 0, 2			// get saved xor'ed bits at bottom
	slli	a0, a0, ICACHE_WAYWIDTH		// line them up
	xor	a2, a2, a0			// restore original MEVADDR
#   endif
	dhi	a2, 0		// invalidate that data cache line
	xsr	a2, MEVADDR
	j	.L_done

#   if XCHAL_DCACHE_LINE_LOCKABLE
.L_dcache_nc_locked:
#    if XCHAL_ICACHE_WAYS > 1
	//  Recover virtual address in a2:
	extui	a0, a2, 0, 2			// get saved xor'ed bits at bottom
	slli	a0, a0, ICACHE_WAYWIDTH		// line them up
	xor	a2, a2, a0			// restore original MEVADDR
#    endif
	//  Unlock, invalidate, and relock it:
	dhu	a2, 0		// unlock that data cache line
	dhi	a2, 0		// invalidate that data cache line
	dpfl	a2, 0		// prefetch-and-lock the line again
	xsr	a2, MEVADDR
	j	.L_done
#   endif

#   if XCHAL_DCACHE_IS_WRITEBACK
	//  Weak reference:  if unresolved, links okay but with zero value:
	.weak	_xtos_merr_hook_uncor_dtag
.L_uncorrectable_dtag:
	//  Fatal (unrecoverable) error in dcache tag (maybe dirty):  parity or uncorrectable ECC error
	movi	a0, _xtos_merr_hook_uncor_dtag
1:	beqz	a0, 1b		// fatal non-corr dcache tag, no hook, so infinite loop
	jx	a0		// jump to user hook, if present

	//  Weak reference:  if unresolved, links okay but with zero value:
	.weak	_xtos_merr_hook_uncor_dirty
.L_uncorrectable_dirty_2:
	xsr	a2, MEVADDR
.L_uncorrectable_dirty:
	//  Fatal (unrecoverable) error, parity or non-correctable ECC error on dirty cache data
	movi	a0, _xtos_merr_hook_uncor_dirty
1:	beqz	a0, 1b		// fatal non-corr dirty cache line, no hook, so infinite loop
	jx	a0		// jump to user hook, if present
#   else
.L_dcache_tag_noncorr:
	//  Uncorrectable error on a lockable writethru data cache tag.
	//  We have to invalidate the line, but that way we lose the lock bit.
	//  Provide a hook to relock if necessary (using knowledge outside this module
	//  about what needs to be locked).  See _xtos_merr_hook_icache_relock for details.
	//  CAVEAT EMPTOR:  this hook mechanism is subject to change.
	.weak	_xtos_merr_hook_dcache_relock	// if unresolved, links with zero value
	movi	a0, _xtos_merr_hook_dcache_relock
1:	beqz	a0, 1b		// if no hook to recover lock state on dcache tag mem error, loop forever
	callx0	a0		// invoke user hook to relock d-cache (index in MEVADDR)
	j	.L_done
#   endif

#  endif /* DCACHE IS WRITEBACK || LINE_LOCKABLE */

# endif /* have DCACHE */

	.size	_MemErrorHandler, . - _MemErrorHandler



# endif /* splitting */
#endif /* XCHAL_HAVE_MEM_ECC_PARITY */

