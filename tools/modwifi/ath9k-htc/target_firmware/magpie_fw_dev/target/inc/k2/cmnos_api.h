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
#ifndef __CMNOS_API_H__
#define __CMNOS_API_H__

/*
 * This file contains wrappers to OS operating system functions
 * that are available in all versions of the operating system.
 *
 * Target software must always use these wrappers to access OS
 * services -- it may not access any OS services directly.
 */

#include "xtensa/config/core.h"
#include "xtensa/hal.h"
#include "xtensa/xtruntime.h"
#include "sys_cfg.h"

/* cmnos interface */
#include "printf_api.h"
#include "uart_api.h"
#include "dbg_api.h"
#include "mem_api.h"
#include "misc_api.h"
#include "string_api.h"
#include "timer_api.h"
#include "romp_api.h"
#include "allocram_api.h"
#include "tasklet_api.h"
#include "clock_api.h"
#include "intr_api.h"
#include "wdt_api.h"
#include "eeprom_api.h"
#include "usb_api.h"

#if defined(PROJECT_K2)
#if SYSTEM_MODULE_SFLASH
#include "sflash_api.h"
#endif
#endif

#define AR6K_ROM_START 0x004e0000
#define AR6K_ROM_ADDR(byte_offset) (AR6K_ROM_START+(byte_offset))
#define TARG_ROM_ADDRS(byte_offset) AR6K_ROM_ADDR(byte_offset)

#define IML_SIGNAL_UNUSED0_ADDR TARG_ROM_ADDRS(0)   /* Cannot be used -- aligned */
#define IML_SIGNAL_ASSERT_ADDR  TARG_ROM_ADDRS(1)   /* Signal an assertion failure */
#define IML_SIGNAL_PRINTF_ADDR  TARG_ROM_ADDRS(2)   /* Signal a printf request */
#define IML_SIGNAL_UNUSED4_ADDR TARG_ROM_ADDRS(4)   /* Cannot be used -- aligned */
#define IML_SIGNAL_UNUSED8_ADDR TARG_ROM_ADDRS(8)   /* Cannot be used -- aligned */
#define IML_SIGNAL_UNUSEDC_ADDR TARG_ROM_ADDRS(0xc) /* Cannot be used -- aligned */
#define IML_SIGNAL_MASK         0xfffe000f
#define IML_LINENUM_SHIFT       4

#define NOW() xthal_get_ccount()

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


#define A_IML_IS_ASSERT(vaddr) \
        (((vaddr) & IML_SIGNAL_MASK) == (IML_SIGNAL_ASSERT_ADDR & IML_SIGNAL_MASK))


#define PRINT_FAILURE_STATE()                                           \
do {                                                                    \
    uint32_t  epc1, epc2, epc3, epc4;                                   \
                                                                        \
    asm volatile("rsr %0,%1" : "=r" (epc1) : "n" (EPC_1));              \
    asm volatile("rsr %0,%1" : "=r" (epc2) : "n" (EPC_2));              \
    asm volatile("rsr %0,%1" : "=r" (epc3) : "n" (EPC_3));              \
    asm volatile("rsr %0,%1" : "=r" (epc4) : "n" (EPC_4));              \
                                                                        \
    A_PRINTF("\tepc1=0x%x, epc2=0x%x, epc3=0x%x, epc4=0x%x\n",          \
                epc1, epc2, epc3, epc4);                                \
    A_PRINTF("0x%08x, 0x%08x, 0x%08x, \n\r",                            \
        DEBUG_SYSTEM_STATE, WATCH_DOG_RESET_COUNTER,                    \
        WATCH_DOG_MAGIC_PATTERN);                                       \
} while(0)
////////////////////////////////////////////////////////////////////////////////////


//#define A_CMN(sym)   _A_OS_INDIRECTION_TABLE->cmnos.sym
#define A_CMN(sym)   _A_MAGPIE_INDIRECTION_TABLE->cmnos.sym

#if SYSTEM_MODULE_MEM
/* Mem interfaces */
#define A_MEMSET(addr, value, size)     \
    A_CMN(mem._memset((char *)(addr), (int)(value), (int)(size)))

#define A_MEMZERO(addr, size)           \
    A_CMN(mem._memset((char *)(addr), (int)0, (int)(size)))

#define A_MEMCPY(dst, src, size)        \
    A_CMN(mem._memcpy((char *)(dst), (char *)(src), (int)(size)))

#define A_MEMMOVE(dst, src, size)       \
    A_CMN(mem._memmove((char *)(dst), (char *)(src), (int)(size)))

#define A_MEMCMP(p1, p2, nbytes)        \
    A_CMN(mem._memcmp)((void *)(p1), (void *)(p2), (int)(nbytes))
#else
/* Mem interfaces */
#define A_MEMSET(addr, value, size)

#define A_MEMZERO(addr, size)

#define A_MEMCPY(dst, src, size)

#define A_MEMMOVE(dst, src, size)

#define A_MEMCMP(p1, p2, nbytes)
#endif


#if 1
    /* String interfaces */
    #define A_STRCPY(dst, src)          A_CMN(string._strcpy((dst), (src)))
    #define A_STRNCPY(dst, src, n)      A_CMN(string._strncpy((dst), (src), (n)))
    #define A_STRLEN(str)               A_CMN(string._strlen(str))
    #define A_STRCMP(str1, str2)        A_CMN(string._strcmp((str1), (str2)))
    #define A_STRNCMP(str1, str2, n)    A_CMN(string._strncmp((str1), (str2), (n)))
#endif

#if SYSTEM_MODULE_PRINT
/* Printf support */
#define A_PRINTF_INIT()                 A_CMN(printf._printf_init())
#define A_PRINTF                        A_CMN(printf._printf)
#else
#define A_PRINTF_INIT()
#define A_PRINTF
#endif /* SYSTEM_MODULE_PRINT */

#if SYSTEM_MODULE_UART
/* Serial port support */
#define A_UART_INIT()               A_CMN(uart._uart_init())

#define A_UART_HWINIT(freq, baud)     \
        A_CMN(uart._uart_hwinit((freq), (baud)))

#define A_UART_ENABLED()            (HOST_INTEREST->hi_uart_enable)

#define A_PUTS(str)                 A_CMN(uart._uart_str_out(str))

#define A_PUTC(ch)                  A_CMN(uart._uart_char_put(ch))
#define A_GETC(pCh)                 A_CMN(uart._uart_char_get(pCh))

#define A_UART_TASK()               A_CMN(uart._uart_task())
#define A_UART_CONFIG(x)            A_CMN(uart._uart_config(x))

#else

#define A_UART_INIT()

#define A_UART_HWINIT(freq, baud)

#define A_UART_ENABLED()

#define A_PUTS(str)

#define A_PUTC(ch)
#define A_GETC(pCh)

#define A_UART_TASK()
#define A_UART_CONFIG(x)

#endif

#if SYSTEM_MODULE_MISC
/* Reset Support */
#define A_RESET()                        A_CMN(misc._system_reset())
#define A_RESET_MAC()                    A_CMN(misc._mac_reset())

/* Assertion failure */
#define A_ASSFAIL(regdump)               A_CMN(misc._assfail((regdump)))

/* Report a failure to the Host */
#define A_REPORT_FAILURE(data, len)      \
        A_CMN(misc._report_failure_to_host((data), (len)))

/* UNALIGNED references are used for ASSERTs */
#define A_MISALIGNED_LOAD_HANDLER(dump)  A_CMN(misc._misaligned_load_handler(dump))

/* reture the host interface type */
#define A_IS_HOST_PRESENT()             A_CMN(misc._is_host_present())
#define A_KBHIT(delay)                  A_CMN(misc._kbhit(delay))
#define A_GET_ROM_VER()                 A_CMN(misc._rom_version_get())
#else
/* Reset Support */
#define A_RESET()
#define A_RESET_MAC()

/* Assertion failure */
#define A_ASSFAIL(regdump)

#define A_MISALIGNED_LOAD_HANDLER(dump)

/* Report a failure to the Host */
#define A_REPORT_FAILURE(data, len)

#define A_IS_HOST_PRESENT()
#define A_KBHIT(delay)
#define A_GET_ROM_VER()
#endif

#if SYSTEM_MODULE_USB
/* debug Support */
#define A_USB_INIT()                    A_CMN(usb._usb_init())
#define A_USB_ROM_TASK()                A_CMN(usb._usb_rom_task())
#define A_USB_FW_TASK()                 A_CMN(usb._usb_fw_task())
#define A_USB_INIT_PHY()                A_CMN(usb._usb_init_phy())

#define A_USB_EP0_SETUP()               A_CMN(usb._usb_ep0_setup())
#define A_USB_EP0_TX_DATA()             A_CMN(usb._usb_ep0_tx_data())
#define A_USB_EP0_RX_DATA()             A_CMN(usb._usb_ep0_rx_data())

#define A_USB_GET_CONFIG()              A_CMN(usb._usb_get_configuration())
#define A_USB_SET_CONFIG()              A_CMN(usb._usb_set_configuration())

#define A_USB_GET_INTERFACE()           A_CMN(usb._usb_get_interface())
#define A_USB_SET_INTERFACE()           A_CMN(usb._usb_set_interface())

#define A_USB_STANDARD_CMD()            A_CMN(usb._usb_standard_cmd())
#define A_USB_VENDOR_CMD()              A_CMN(usb._usb_vendor_cmd())

#define A_USB_POWER_OFF()               A_CMN(usb._usb_power_off())
#define A_USB_RESET_FIFO()              A_CMN(usb._usb_reset_fifo())
#define A_USB_GEN_WDT()                 A_CMN(usb._usb_gen_wdt())
#define A_USB_JUMP_BOOT()               A_CMN(usb._usb_jump_boot())

#define A_USB_GET_DESCRIPTOR()          A_CMN(usb._usb_get_descriptor())
#define A_USB_SET_ADDRESS()             A_CMN(usb._usb_set_address())
#define A_USB_SET_FEATURE()             A_CMN(usb._usb_set_feature())
#define A_USB_CLEAR_FEATURE()           A_CMN(usb._usb_clr_feature())

#define A_USB_GET_STATUS()              A_CMN(usb._usb_get_status())
#define A_USB_SETUP_DESC()              A_CMN(usb._usb_setup_desc())
#define A_USB_STATUS_IN()               A_CMN(usb._usb_status_in())
#define A_USB_REG_OUT()                 A_CMN(usb._usb_reg_out())

#define A_USB_EP0_TX()                  A_CMN(usb._usb_ep0_tx())
#define A_USB_EP0_RX()                  A_CMN(usb._usb_ep0_rx())
#define A_USB_CLK_INIT()                A_CMN(usb._usb_clk_init())

#else
#define A_USB_INIT()
#define A_USB_TASK()
#define A_USB_INIT_PHY()

#define A_USB_EP0_SETUP()
#define A_USB_EP0_TX()
#define A_USB_EP0_RX()

#define A_USB_GET_CONFIG()
#define A_USB_SET_CONFIG()

#define A_USB_GET_INTERFACE()
#define A_USB_SET_INTERFACE()

#define A_USB_STANDARD_CMD()
#define A_USB_VENDOR_CMD()

#define A_USB_POWER_OFF()
#define A_USB_RESET_FIFO()
#define A_USB_GEN_WDT()
#define A_USB_JUMP_BOOT()

#define A_USB_GET_DESCRIPTOR()
#define A_USB_SET_ADDRESS()
#define A_USB_SET_FEATURE()
#define A_USB_CLEAR_FEATURE()

#define A_USB_GET_STATUS()
#define A_USB_SETUP_DESC()


#define A_USB_STATUS_IN()
#define A_USB_REG_OUT()

#define A_USB_EP0_TX()
#define A_USB_EP0_RX()

#define A_USB_CLK_INIT()
#endif

#if SYSTEM_MODULE_INTR
/* Low-level interrupt support intended for use by OS modules */
#define A_INTR_GET_INTRENABLE()         A_CMN(intr._get_intrenable())
#define A_INTR_SET_INTRENABLE(val)      A_CMN(intr._set_intrenable(val))
#define A_INTR_GET_INTRPENDING()        A_CMN(intr._get_intrpending())
#define A_INTR_UNBLOCK_ALL_INTRLVL()    A_CMN(intr._unblock_all_intrlvl())

/* Interrupt support */
#define A_INTR_INIT()                   A_CMN(intr._intr_init())

#define  A_INTR_DISABLE(pOld)                           \
    do {                                                \
        *(pOld) = A_CMN(intr._intr_disable());        \
    } while (0)

#define  A_INTR_RESTORE(old)            A_CMN(intr._intr_restore((old)))

#define A_INVOKE_ISR(inum)              A_CMN(intr._intr_invoke_isr(inum))

#define A_INTR_MASK(inum)               A_CMN(intr._intr_mask_inum(inum))
#define A_INTR_UNMASK(inum)             A_CMN(intr._intr_unmask_inum(inum))

#define A_ATTACH_ISR(inum, isr, arg)    A_CMN(intr._intr_attach_isr(inum, isr, arg))
#else
#define A_INTR_INIT()
#define  A_INTR_DISABLE(pOld)
#define  A_INTR_RESTORE(old)

#define A_INTR_GET_INTRENABLE()
#define A_INTR_SET_INTRENABLE(val)
#define A_INTR_GET_INTRPENDING()
#define A_INTR_UNBLOCK_ALL_INTRLVL()
#define A_INVOKE_ISR(inum)
#define A_INTR_MASK(inum)
#define A_INTR_UNMASK(inum)
#define A_ATTACH_ISR(inum, isr, arg)

#endif

/* Tasklet Support */
#define A_TASKLET_INIT()                    A_CMN(tasklet._tasklet_init())
#define A_TASKLET_INIT_TASK(f, arg, t)      A_CMN(tasklet._tasklet_init_task(f, arg, t))
#define A_TASKLET_DISABLE(t)                A_CMN(tasklet._tasklet_disable(t))
#define A_TASKLET_SCHEDULE(t)               A_CMN(tasklet._tasklet_schedule(t))
#define A_TASKLET_RUN()                     A_CMN(tasklet._tasklet_run())


/* RAM Allocation Support */
#if defined(__mips__)
#define alloc_arena_start _end
#endif
#if defined(__XTENSA__)
#define alloc_arena_start _end
#endif

#if SYSTEM_MODULE_CLOCK

#define A_CLOCK_INIT(refclk_guess)      A_CMN(clock._clock_init(refclk_guess))
#define A_CLOCK_TICK()                  A_CMN(clock._clock_tick())
#define A_CLOCK_GET_TICK()              A_CMN(clock._clock_get_tick())

/*
 * Get the number of millisecond ticks since the system was started.
 * Note that this only approximates 1Ms.  It's actually 32 ticks of
 * a 32KHz clock.
 *
 * Returns a A_UINT32 value.
 */
#define A_MILLISECONDS()                A_CMN(clock._milliseconds())

/*
 * Get the frequency of the reference clock, expressed as
 * an A_refclk_speed_t.
 */
#define A_REFCLK_SPEED_GET()            A_CMN(clock._refclk_speed_get())

/* Spin delay */
#define A_DELAY_USECS(us)               A_CMN(clock._delay_us(us))

#define A_UART_FREQUENCY()              A_CMN(clock._uart_frequency())

#define A_CLOCKREGS_INIT()              A_CMN(clock._clockregs_init())

/* which_band is either A_BAND_24GHZ or A_BAND_5GHZ */
#define A_WLAN_BAND_SET(which_band)      \
        A_CMN(clock._wlan_band_set(which_band))

/* Called whenever the system clock changes speed */
#define A_SYSCLK_CHANGE(mhz)               A_CMN(clock._sysclk_change(mhz))

#define A_SYSCLK_GET()               A_CMN(clock._sysclk_get())

#else

#define A_CLOCK_INIT(refclk_guess)
#define A_CLOCK_TICK()
#define A_CLOCK_GET_TICK()
#define A_MILLISECONDS()
#define A_REFCLK_SPEED_GET()
#define A_DELAY_USECS(us)
#define A_UART_FREQUENCY()
#define A_CLOCKREGS_INIT()
#define A_WLAN_BAND_SET(which_band)
#define A_SYSCLK_CHANGE(mhz)
#define A_SYSCLK_GET()

#endif

// Timer
#define A_INIT_TIMER(pTimer, pFunction, pArg) \
    A_CMN(timer._timer_setfn((pTimer), (pFunction), (pArg)))

/* Set a (possibly periodic) timer for "period" Milliseconds. */
#define A_TIMEOUT_MS(pTimer, period) \
    A_CMN(timer._timer_arm((pTimer), (period)))

#define A_UNTIMEOUT(pTimer) \
    A_CMN(timer._timer_disarm(pTimer))

#define A_TIMER_RUN() \
    A_CMN(timer._timer_run())

#define A_PCI_BOOT_INIT() \
    A_CMN(pci.pci_boot_init()) 

#define A_GMAC_BOOT_INIT() \
    A_CMN(gmac.gmac_boot_init()) 

#if SYSTEM_MODULE_ALLOCRAM
/* Default size of ALLOCRAM area */
#define ARENA_SZ_DEFAULT 12000

#define A_ALLOCRAM_INIT(arena_start, arena_size)			\
	do {								\
		extern unsigned int alloc_arena_start;			\
		void *astart;						\
		int asize;						\
		astart = (arena_start) ? (void *)(arena_start) : &alloc_arena_start; \
		asize = (arena_size) ? (arena_size) : (ARENA_SZ_DEFAULT); \
		A_CMN(allocram.cmnos_allocram_init((astart), (asize)));	\
	} while (0)

#define A_ALLOCRAM(nbytes)      A_CMN(allocram.cmnos_allocram(0, (nbytes)))

#define A_ALLOCRAM_DEBUG()    A_CMN(allocram.cmnos_allocram_debug())

#else
#define A_ALLOCRAM_INIT(arena_start, arena_size)
#define A_ALLOCRAM(nbytes)
#define A_ALLOCRAM_DEBUG()
#endif

#if SYSTEM_MODULE_ROM_PATCH

#define A_ROMP_INIT()           A_CMN(romp._romp_init())
#define A_ROMP_DOWNLOAD(x)      A_CMN(romp._romp_download(x))
#define A_ROMP_DECODE(addr)     A_CMN(romp._romp_decode(addr))
#define A_ROMP_INSTALL()        A_CMN(romp._romp_install())
#else
#define A_ROMP_INIT()
#define A_ROMP_DOWNLOAD(x)
#define A_ROMP_DECODE(addr)
#define A_ROMP_INSTALL()
#endif

#if SYSTEM_MODULE_WDT

#define A_WDT_INIT()            A_CMN(wdt_timer._wdt_init())
#define A_WDT_ENABLE()          A_CMN(wdt_timer._wdt_enable())
#define A_WDT_DISABLE()         A_CMN(wdt_timer._wdt_disable())
#define A_WDT_SET(t)            A_CMN(wdt_timer._wdt_set(t))
#define A_WDT_TASK()            A_CMN(wdt_timer._wdt_task())
#define A_WDT_LASTBOOT()        A_CMN(wdt_timer._wdt_last_boot())
#define A_WDT_RESET()           A_CMN(wdt_timer._wdt_reset())

#else
#define A_WDT_INIT()
#define A_WDT_ENABLE()
#define A_WDT_DISABLE()
#define A_WDT_SET(t)
#define A_WDT_TASK()
#define A_WDT_LASTBOOT()
#define A_WDT_RESET()
#endif


#if SYSTEM_MODULE_EEPROM
#define A_EEP_INIT()                    A_CMN(eep._eep_init())
#define A_EEP_READ(off, len, buf)       A_CMN(eep._eep_read(off, len, buf))
#define A_EEP_WRITE(off, len, buf)      A_CMN(eep._eep_write(off, len, buf))
#define A_EEP_IS_EXIST()                A_CMN(eep._eep_is_exist())
#else
#define A_EEP_INIT()
#define A_EEP_READ(off, len, buf)
#define A_EEP_WRITE(off, len, buf)
#define A_EEP_IS_EXIST()
#endif



struct _A_os_linkage_check; /* OS-dependent */

typedef struct _A_cmnos_indirection_table {
    int (* hal_linkage_check)(int sz, struct _A_os_linkage_check *);
    unsigned int *start_bss;
    void (* app_start)(void);

#if SYSTEM_MODULE_MEM
    struct mem_api    mem;
#endif

#if SYSTEM_MODULE_MISC
    struct misc_api     misc;
#endif

#if SYSTEM_MODULE_PRINT
    struct printf_api    printf;
#endif

#if SYSTEM_MODULE_UART
    struct uart_api      uart;
#endif

#if SYSTEM_MODULE_DBG
#if !MOVE_DBG_TO_RAM // move to firmware not in cmnos
    struct dbg_api      dbg;
#endif
#endif
#if SYSTEM_MODULE_PCI
   struct pci_api pci;
#endif

#if SYSTEM_MODULE_GMAC
   struct gmac_api gmac;
#endif

#if SYSTEM_MODULE_USB
    struct usb_api      usb;
#endif

#if SYSTEM_MODULE_CLOCK
    struct clock_api     clock;
#endif

#if SYSTEM_MODULE_TIMER
    struct timer_api     timer;
#endif

#if SYSTEM_MODULE_INTR
    struct intr_api     intr;
#endif

#if SYSTEM_MODULE_ALLOCRAM
    struct allocram_api     allocram;
#endif

#if SYSTEM_MODULE_ROM_PATCH
    struct romp_api     romp;
#endif

#if SYSTEM_MODULE_WDT
    struct wdt_api     wdt_timer;
#endif

#if SYSTEM_MODULE_EEPROM
    struct eep_api     eep;
#endif

    struct string_api   string;
    struct tasklet_api  tasklet;

} _A_cmnos_indirection_table_t;

/* Module installation  for cmnos modules */

#if SYSTEM_MODULE_MEM
extern void cmnos_mem_module_install(struct mem_api *);
#endif

#if SYSTEM_MODULE_MISC
extern void cmnos_misc_module_install(struct misc_api *);
#endif

#if SYSTEM_MODULE_PRINT
extern void cmnos_printf_module_install(struct printf_api *);
#endif

#if SYSTEM_MODULE_UART
extern void cmnos_uart_module_install(struct uart_api *);
#endif

#if SYSTEM_MODULE_DBG
extern void cmnos_dbg_module_install(struct dbg_api *);
#endif

#if SYSTEM_MODULE_USB
extern void cmnos_usb_module_install(struct usb_api *);
#endif

#if SYSTEM_MODULE_INTR
extern void cmnos_intr_module_install(struct intr_api *);
#endif

#if SYSTEM_MODULE_CLOCK
extern void cmnos_clock_module_install(struct clock_api *);
#endif

#if SYSTEM_MODULE_TIMER
extern void cmnos_timer_module_install(struct timer_api *);
#endif

#if SYSTEM_MODULE_ALLOCRAM
extern void cmnos_allocram_module_install(struct allocram_api *);
#endif

#if SYSTEM_MODULE_ROM_PATCH
extern void cmnos_romp_module_install(struct romp_api *);
#endif

#if SYSTEM_MODULE_WDT
extern void cmnos_wdt_module_install(struct wdt_api *);
#endif

#if SYSTEM_MODULE_EEPROM
extern void cmnos_eep_module_install(struct eep_api *);
#endif

#if SYSTEM_MODULE_PCI
extern void cmnos_pci_module_install(struct pci_api *);
#endif

extern void cmnos_tasklet_module_install(struct tasklet_api *);

extern void cmnos_string_module_install(struct string_api *tbl);

#endif /* __CMNOS_API_H__ */
