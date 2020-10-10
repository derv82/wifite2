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
#ifndef __AR6K_SOC_H__
#define __AR6K_SOC_H__

//#include "hw/apb_map.h"
//#include "hw/rtc_reg.h"
//#include "hw/mbox_reg.h"

/*
 * Basic types, appropriate for both
 *      the 32-bit MIPS core on AR6000 and
 *      the 32-bit XTensa core on AR6002
 */
typedef signed char         A_CHAR;
typedef signed char         A_INT8;
typedef unsigned char       A_UINT8;
typedef unsigned char       A_UCHAR;
typedef short               A_INT16;
typedef unsigned short      A_UINT16;
typedef int                 A_INT32;
typedef unsigned int        A_UINT32;
typedef long long           A_INT64;
typedef unsigned long long  A_UINT64;
typedef int                 A_BOOL;
typedef unsigned int        ULONG;
typedef ULONG               A_ULONG;
typedef A_ULONG             A_ADDR;

#if 0
//#include "targaddrs.h"

/*
 * Some platform-specific macros and constants that may needed
 * outside of the BSP.
 */

/*
 * AR6001/MIPS uses a cache line size of 16 Bytes.
 * AR6002/Xtensa has no caches; but existing code assumes
 * that this constant is non-zero.  To avoid code complexity
 * and possibly subtle bugs we define a bogus cache
 * line size for Xtensa that matches MIPs'.
 */
#define A_CACHE_LINE_SIZE         16

#if defined(AR6001)
#define A_MIPS_KSEG_UNCACHED      0xa0000000
#define A_MIPS_KSEG_CACHED        0x80000000
#define A_MIPS_KSEG_MASK          0xe0000000

/*
 * Convert a cached virtual address or a CPU physical address into
 * an uncached virtual address.
 */
#define A_UNCACHED_ADDR(addr)     \
    ((void *)(((A_UINT32)(addr)) | A_MIPS_KSEG_UNCACHED))

/*
 * Convert an uncached or CPU physical address into
 * a cached virtual address.
 */
#define A_CACHED_ADDR(addr)       \
    ((void *)((((A_UINT32)(addr)) & ~A_MIPS_KSEG_MASK) | A_MIPS_KSEG_CACHED))

/* Read/Write a 32-bit AR6000 SOC register, specified by its physical address */
#define A_SOC_ADDR_READ(addr) (*((volatile A_UINT32 *)A_UNCACHED_ADDR(addr))) 

#define A_SOC_ADDR_WRITE(addr, val)                                           \
    do {                                                                      \
        (*((volatile A_UINT32 *)A_UNCACHED_ADDR(addr))) = (A_UINT32)(val);    \
    } while (0)

#define A_RTC_REG_READ(addr)    A_SOC_ADDR_READ(addr)
#define A_MC_REG_READ(addr)     A_SOC_ADDR_READ(addr)
#define A_UART_REG_READ(addr)   A_SOC_ADDR_READ(addr)
#define A_SI_REG_READ(addr)     A_SOC_ADDR_READ(addr)
#define A_GPIO_REG_READ(addr)   A_SOC_ADDR_READ(addr)
#define A_MBOX_REG_READ(addr)   A_SOC_ADDR_READ(addr)
#define A_WMAC_REG_READ(addr)   A_SOC_ADDR_READ(addr)
#define A_ANALOG_REG_READ(addr) A_SOC_ADDR_READ(addr)

#define A_RTC_REG_WRITE(addr, val)     A_SOC_ADDR_WRITE((addr), (val))
#define A_MC_REG_WRITE(addr, val)      A_SOC_ADDR_WRITE((addr), (val))
#define A_UART_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE((addr), (val))
#define A_SI_REG_WRITE(addr, val)      A_SOC_ADDR_WRITE((addr), (val))
#define A_GPIO_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE((addr), (val))
#define A_MBOX_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE((addr), (val))
#define A_WMAC_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE((addr), (val))
#define A_ANALOG_REG_WRITE(addr, val)  A_SOC_ADDR_WRITE((addr), (val))
#endif

#if defined(AR6002)
#define A_UNCACHED_ADDR(addr)     (addr)
#define A_CACHED_ADDR(addr)       (addr)

#define A_SOC_ADDR_READ(addr) (*((volatile A_UINT32 *)(addr))) 

#define A_SOC_ADDR_WRITE(addr, val)                                           \
    do {                                                                      \
        (*((volatile A_UINT32 *)(addr))) = (A_UINT32)(val);                   \
    } while (0)

#define A_RTC_REG_READ(addr)    A_SOC_ADDR_READ(RTC_BASE_ADDRESS|(A_UINT32)(addr))
#define A_MC_REG_READ(addr)     A_SOC_ADDR_READ(VMC_BASE_ADDRESS|(A_UINT32)(addr))
#define A_UART_REG_READ(addr)   A_SOC_ADDR_READ(UART_BASE_ADDRESS|(A_UINT32)(addr))
#define A_SI_REG_READ(addr)     A_SOC_ADDR_READ(SI_BASE_ADDRESS|(A_UINT32)(addr))
#define A_GPIO_REG_READ(addr)   A_SOC_ADDR_READ(GPIO_BASE_ADDRESS|(A_UINT32)(addr))
#define A_MBOX_REG_READ(addr)   A_SOC_ADDR_READ(MBOX_BASE_ADDRESS|(A_UINT32)(addr))
#define A_WMAC_REG_READ(addr)   A_SOC_ADDR_READ(MAC_BASE_ADDRESS|(A_UINT32)(addr))
#define A_ANALOG_REG_READ(addr) A_SOC_ADDR_READ(ANALOG_INTF_BASE_ADDRESS|(A_UINT32)(addr))

#define A_RTC_REG_WRITE(addr, val)     A_SOC_ADDR_WRITE(RTC_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_MC_REG_WRITE(addr, val)      A_SOC_ADDR_WRITE(VMC_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_UART_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE(UART_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_SI_REG_WRITE(addr, val)      A_SOC_ADDR_WRITE(SI_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_GPIO_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE(GPIO_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_MBOX_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE(MBOX_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_WMAC_REG_WRITE(addr, val)    A_SOC_ADDR_WRITE(MAC_BASE_ADDRESS|(A_UINT32)(addr), (val))
#define A_ANALOG_REG_WRITE(addr, val)  A_SOC_ADDR_WRITE(ANALOG_INTF_BASE_ADDRESS|(A_UINT32)(addr), (val))

#endif /* AR6002 */

/*
 * Sleep/stay awake control.
 * It is the caller's responsibility to guarantee atomicity.
 */

typedef A_UINT32 A_old_sleep_t;

#define A_SYSTEM_SLEEP_DISABLE(pOldSystemSleep)                        \
do {                                                                   \
    *(pOldSystemSleep) = A_RTC_REG_READ(SYSTEM_SLEEP_ADDRESS);         \
    A_RTC_REG_WRITE(SYSTEM_SLEEP_ADDRESS,                              \
                    *(pOldSystemSleep) | SYSTEM_SLEEP_DISABLE_MASK);   \
    (void)A_RTC_REG_READ(SYSTEM_SLEEP_ADDRESS); /* flush */            \
} while (0)

#define A_SYSTEM_SLEEP_RESTORE(OldSystemSleep)                         \
do {                                                                   \
    A_RTC_REG_WRITE(SYSTEM_SLEEP_ADDRESS, (OldSystemSleep));           \
    (void)A_RTC_REG_READ(SYSTEM_SLEEP_ADDRESS); /* flush */            \
} while (0)


/*
 * AR6K-specific High Frequency Timestamp support.
 * This is intended for use as a performance tool, and
 * is not to be used in normal operation.
 */
typedef struct {
    A_UINT32 highfreq; /* ~40MHz resolution */
    A_UINT32 lowfreq;  /* ~32KHz resolution */
} A_timestamp_t;

/*
 * Enable HighFrequency timer.
 * Normally, we keep this OFF in order to save power.
 */
#define HF_TIMER_CONTROL_START_MASK HF_TIMER_CONTROL_ON_MASK
#define A_TIMESTAMP_ENABLE()                                             \
do {                                                                     \
    A_RTC_REG_WRITE(HF_TIMER_ADDRESS, (40000000/32768)<<12);             \
    A_RTC_REG_WRITE(HF_TIMER_CONTROL_ADDRESS,                            \
                  HF_TIMER_CONTROL_START_MASK |                          \
                  HF_TIMER_CONTROL_AUTO_RESTART_MASK |                   \
                  HF_TIMER_CONTROL_RESET_MASK);                          \
} while (0)

/* 
 * Turn it OFF when you're done:
 */
#define A_TIMESTAMP_DISABLE() A_RTC_REG_WRITE(HF_TIMER_CONTROL_ADDRESS, 0)

/*
 * Get a timestamp.  It's the caller's responsibility to
 * guarantee atomicity of the two reads, if needed.
 */
#define A_TIMESTAMP(pTimestamp)                                          \
    do {                                                                 \
        (pTimestamp)->highfreq = A_RTC_REG_READ(HF_TIMER_COUNT_ADDRESS); \
        (pTimestamp)->lowfreq = A_RTC_REG_READ(HF_LF_COUNT_ADDRESS);     \
    } while (0)

/*
 * Supported reference clock speeds.
 *
 * Note: MAC HAL code has multiple tables indexed by these values,
 * so do not rearrange them.  Add any new refclk values at the end.
 */
typedef enum {
    AR6K_REFCLK_UNKNOWN   = -1, /* Unsupported ref clock -- use PLL Bypass */
    AR6K_REFCLK_19_2_MHZ  = 0,
    AR6K_REFCLK_26_MHZ    = 1,
    AR6K_REFCLK_40_MHZ    = 2,
    AR6K_REFCLK_52_MHZ    = 3,
    AR6K_REFCLK_38_4_MHZ  = 4,
    AR6K_REFCLK_24_MHZ    = 5,
} A_refclk_speed_t;

#define A_REFCLK_UNKNOWN    AR6K_REFCLK_UNKNOWN
#define A_REFCLK_19_2_MHZ   AR6K_REFCLK_19_2_MHZ
#define A_REFCLK_26_MHZ     AR6K_REFCLK_26_MHZ
#define A_REFCLK_40_MHZ     AR6K_REFCLK_40_MHZ
#define A_REFCLK_52_MHZ     AR6K_REFCLK_52_MHZ
#define A_REFCLK_38_4_MHZ   AR6K_REFCLK_38_4_MHZ
#define A_REFCLK_24_MHZ     AR6K_REFCLK_24_MHZ

/* System defaults to 2.4GHz settings */
#define A_BAND_DEFAULT        A_BAND_24GHZ

#if defined(AR6001)
#define FLASH_ADDR(n) AR6000_FLASH_ADDR(n)
#endif

#if defined(AR6002)
#define HOST_INTEREST ((struct host_interest_s *)AR6002_HOST_INTEREST_ADDRESS)
#else
#define HOST_INTEREST ((struct host_interest_s *)AR6001_HOST_INTEREST_ADDRESS)
#endif

#define AR6K_OPTION_TEST(option) \
            (A_MBOX_REG_READ(LOCAL_SCRATCH_ADDRESS) & (option))

#endif

#endif /* __AR6K_SOC_H__ */
