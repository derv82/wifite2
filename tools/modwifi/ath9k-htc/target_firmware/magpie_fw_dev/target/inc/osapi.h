/*
 * Copyright (c) 2013 Qualcomm Atheros, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the
 * disclaimer below) provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *  * Neither the name of Qualcomm Atheros nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
 * GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
 * HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
 * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
 * IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#ifndef __OSAPI_H__
#define __OSAPI_H__

#define A_COMPILE_TIME_ASSERT(assertion_name, predicate) \
    typedef char assertion_name[(predicate) ? 1 : -1];

#if !defined(LOCAL)
#if 0 /* At least for now, simplify debugging. */
#define LOCAL      static
#else
#define LOCAL
#endif
#endif

#if !defined(NULL)
#define NULL       (void *)0
#endif

#if !defined(FALSE)
#define FALSE 0
#endif

#if !defined(TRUE)
#define TRUE 1
#endif

#ifdef __GNUC__
#define __ATTRIB_PACK           __attribute__ ((packed))
#define __ATTRIB_PRINTF         __attribute__ ((format (printf, 1, 2)))
#define __ATTRIB_NORETURN       __attribute__ ((noreturn))
#define __ATTRIB_ALIGN(x)       __attribute__ ((aligned((x))))
#define INLINE                  __inline__
#else /* Not GCC */
#define __ATTRIB_PACK
#define __ATTRIB_PRINTF
#define __ATTRIB_NORETURN
#define __ATTRIB_ALIGN(x)
#define INLINE                  __inline
#endif /* End __GNUC__ */

#define PREPACK
#define POSTPACK                __ATTRIB_PACK

/* Utility macros */
#define A_SWAB32(_x) ( \
	((A_UINT32)( \
		(((A_UINT32)(_x) & (A_UINT32)0x000000ffUL) << 24) | \
		(((A_UINT32)(_x) & (A_UINT32)0x0000ff00UL) <<  8) | \
		(((A_UINT32)(_x) & (A_UINT32)0x00ff0000UL) >>  8) | \
		(((A_UINT32)(_x) & (A_UINT32)0xff000000UL) >> 24) )) \
)

#define A_SWAB16(_x) \
	((A_UINT16)( \
		(((A_UINT16)(_x) & (A_UINT16)0x00ffU) << 8) | \
		(((A_UINT16)(_x) & (A_UINT16)0xff00U) >> 8) ))

/* unaligned little endian access */
#define A_LE_READ_2(p)                                              \
        ((A_UINT16)(                                                \
        (((A_UINT8 *)(p))[0]) | (((A_UINT8 *)(p))[1] <<  8)))

#define A_LE_READ_4(p)                                              \
        ((A_UINT32)(                                                \
        (((A_UINT8 *)(p))[0]      ) | (((A_UINT8 *)(p))[1] <<  8) | \
        (((A_UINT8 *)(p))[2] << 16) | (((A_UINT8 *)(p))[3] << 24)))

#define A_LE64_TO_CPU(_x)     ((A_UINT64)(_x))
#define A_LE32_TO_CPU(_x)     ((A_UINT32)(_x))
#define A_CPU_TO_LE32(_x)     ((A_UINT32)(_x))
#define A_BE32_TO_CPU(_x)     A_SWAB32(_x)
#define A_CPU_TO_BE32(_x)     A_SWAB32(_x)
#define A_LE16_TO_CPU(_x)     ((A_UINT16)(_x))
#define A_CPU_TO_LE16(_x)     ((A_UINT16)(_x))
#define A_BE16_TO_CPU(_x)     A_SWAB16(_x)
#define A_CPU_TO_BE16(_x)     A_SWAB16(_x)


#define	A_LE32TOH(_x)	A_LE32_TO_CPU(_x)
#define	A_HTOLE32(_x)	A_CPU_TO_LE32(_x)
#define	A_BE32TOH(_x)	A_BE32_TO_CPU(_x)
#define	A_HTOBE32(_x)	A_CPU_TO_BE32(_x)
#define	A_LE16TOH(_x)	A_LE16_TO_CPU(_x)
#define	A_HTOLE16(_x)	A_CPU_TO_LE16(_x)
#define	A_BE16TOH(_x)	A_BE16_TO_CPU(_x)
#define	A_HTOBE16(_x)	A_CPU_TO_BE16(_x)

#define A_MAX(x, y)                  (((x) > (y)) ? (x) : (y))
#define A_MIN(x, y)                  (((x) < (y)) ? (x) : (y))
#define A_ABS(x)                     (((x) >= 0) ? (x) : (-(x)))
#define A_ROUND_UP(x, y)             ((((x) + ((y) - 1)) / (y)) * (y))
#define A_ROUND_UP_PAD(x, y)         (A_ROUND_UP(x, y) - (x))
#define A_ROUND_UP_PWR2(x, align)    (((int) (x) + ((align)-1)) & ~((align)-1))
#define A_ROUND_DOWN_PWR2(x, align)  ((int)(x) & ~((align)-1))

#define A_TOLOWER(c)        (((c) >= 'A' && (c) <= 'Z') ? ((c)-'A'+'a') : (c))
#define A_TOUPPER(c)        (((c) >= 'a' && (c) <= 'z') ? ((c)-'a'+'A') : (c))

#define A_ARRAY_NUM_ENTRIES(a)        (sizeof(a)/sizeof(*(a)))
#define A_FIELD_OFFSET(type, field)   ((int)(&((type *)0)->field))

#define A_MSECS_PER_SECOND      1000         /* Milliseconds */
#define A_USECS_PER_SECOND      1000000      /* Microseconds */
#define A_NSECS_PER_SECOND      1000000000   /* Nanoseconds  */

/*
 * Intentional Misaligned Load special "addresses".
 * Loads from misaligned addresses have special semantics, 
 * handled by the OS, depending on the lower nibble.
 *
 * NOTE1: word-aligned nibbles will not cause any exception,
 * so they must not be used.
 *
 * NOTE2: On AR6002, the Xtensa CPU may issue a load speculatively.
 * If this load accesses an unmapped region of SOC (such as the
 * lower 4KB), AR6002 hardware generates an Address Error interrupt
 * even before the instruction has actually executed and therefore
 * before it has a chance to generate the expected Misaligned Load
 * error.  To avoid this, we make these IML accesses be to an address
 * range that is valid....ROM.
 */
#if 0
#define IML_SIGNAL_UNUSED0_ADDR TARG_ROM_ADDRS(0)   /* Cannot be used -- aligned */
#define IML_SIGNAL_ASSERT_ADDR  TARG_ROM_ADDRS(1)   /* Signal an assertion failure */
#define IML_SIGNAL_PRINTF_ADDR  TARG_ROM_ADDRS(2)   /* Signal a printf request */
#define IML_SIGNAL_UNUSED4_ADDR TARG_ROM_ADDRS(4)   /* Cannot be used -- aligned */
#define IML_SIGNAL_UNUSED8_ADDR TARG_ROM_ADDRS(8)   /* Cannot be used -- aligned */
#define IML_SIGNAL_UNUSEDC_ADDR TARG_ROM_ADDRS(0xc) /* Cannot be used -- aligned */
#define IML_SIGNAL_MASK         0xfffe000f
#define IML_LINENUM_SHIFT       4
#endif

#ifdef HTC_TRACE_MBOX_PAUSE
#define A_ASSERT( __bool ) 
#else
/*
 * Code space dedicated to asserts is minimal.  We use an Intentional
 * Misaligned Load to signal an assert failure.  We embed the line
 * number in the misaligned address as a debugging aid.  This may
 * make it a bit more difficult to recognize a bona fide misaligned
 * load, but that's an acceptable tradeoff.
 *
 * Bits 3..0 encodes the IML_SIGNAL_* number.
 * Bits 16..4 encode the LINE number of the ASSERTion.
 * Upper nibbles are the start of ROM.
 */
#if defined(__XTENSA__)
#define _A_BARRIER asm volatile("memw")
#else
#define _A_BARRIER
#endif
#define A_ASSERT( __bool )                                                  \
    do {                                                                    \
        if (0 == (__bool)) {                                                \
            (void)*((volatile int *)(IML_SIGNAL_ASSERT_ADDR+(__LINE__<<4)));\
            _A_BARRIER;                                                     \
        }                                                                   \
    } while (0)
#endif

#define A_IML_IS_ASSERT(vaddr) \
        (((vaddr) & IML_SIGNAL_MASK) == (IML_SIGNAL_ASSERT_ADDR & IML_SIGNAL_MASK))

/*
 * The A_ASSERT macro encodes line number in the Intentionally Misaligned
 * Address that it uses to signal a failure.  This macro extracts that
 * line number information.
 *
 * Note: ASSERTs up to line 8191 (13 bits) of a file are supported.
 * Beyond that an assertion failure appears as a misaligned load.
 */
#define A_IML_ASSLINE(vaddr) (((vaddr) & ~IML_SIGNAL_MASK) >> IML_LINENUM_SHIFT)

/* Prevent compiler code movement */
#define A_REORDER_BARRIER() asm volatile ( "" : : : "memory" )

/*
 * Some general system settings may depend on which wireless band is
 * to be used.   For example, on AR6K the system PLL setting is
 * band-dependent.
 *
 * These constants are used with A_WLAN_BAND_SET.
 */
#define A_BAND_24GHZ           0
#define A_BAND_5GHZ            1
#define A_NUM_BANDS            2

#define OTUS

#if defined(AR6K)
//#include <AR6K/AR6K_soc.h>
#elif defined(OTUS)
#include <OTUS/OTUS_soc.h>
#else
#error "Unsupported platform"
#endif


//#include "os/athos_api.h"

#endif /* __OSAPI_H__ */
