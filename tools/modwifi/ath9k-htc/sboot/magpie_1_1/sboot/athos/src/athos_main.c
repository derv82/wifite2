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
/*
 * Copyright (c) 2000-2008 Atheros Communications, Inc., All Rights Reserved
 *
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/magpie_fw_dev/build/magpie_1_1/sboot/athos/src/athos_main.c#1 $
 *
 * This file contains type definitions
 */

/* osapi support */
#include "sys_cfg.h"
#include "athos_api.h"
//#include <fwd.h>

#include "regdump.h"

/* dhry mips stone test */
//#include "dhry.h"

/* usb support */
//#include "usb_defs.h"
//#include "usb_type.h"

/* xtensa related */
#include "xtensa/corebits.h"
#include "xtensa/tie/xt_core.h"

#include <dma_lib.h>
#include <hif_pci.h>
#include <hif_gmac.h>
#include <fwd.h>


BOOLEAN download_enable = FALSE;

/* #define ALLOCRAM_START       0x512800 */
/* #define ALLOCRAM_SIZE        ( SYS_RAM_SZIE - ( ALLOCRAM_START - SYS_D_RAM_REGION_0_BASE) - SYS_D_RAM_STACK_SIZE) */

#define ALLOCRAM_START       SYS_D_RAM_REGION_3_BASE
#define ALLOCRAM_SIZE        SYS_RAM_BLOCK_SIZE

extern unsigned int _text_start_in_rom;
extern unsigned int _text_start;
extern unsigned int _text_end;

extern unsigned int _rodata_start_in_rom;
extern unsigned int _lit4_start;
extern unsigned int _lit4_end;

/*
 * This special table is used by Xtensa startup code to copy
 * ROM-based data into RAM.  See Xtensa documentation or
 * "unpack" code in ResetVector.S for details.
 */
const uint32_t _rom_store_table[] = {
    (uint32_t)&_data_start,   (uint32_t)&_data_end, (uint32_t)&_data_start_in_rom,
    (uint32_t)&_text_start,   (uint32_t)&_text_end, (uint32_t)0xf002000,
    (uint32_t)&_lit4_start,   (uint32_t)&_lit4_end, (uint32_t)0xf008000,
    (uint32_t)0x00500400,   (uint32_t)0x00500940,  (uint32_t)0x004e0260,
    0,   0,             0
};


#define ATH_DATE_STRING     __DATE__" "__TIME__


/*
 * 03/09: it'll always fall into this exception if we enable this exception handler, need to do more testing, Ryan
 */
void
Magpie_fatal_exception_handler(CPU_exception_frame_t *exc_frame)
{
    struct register_dump_s dump;

    dump.exc_frame              = *exc_frame; /* structure copy */
    dump.badvaddr               = XT_RSR_EXCVADDR();
    dump.exc_frame.xt_exccause  = XT_RSR_EXCCAUSE();
    dump.pc                     = exc_frame->xt_pc;
    dump.assline                = 0;

    A_PRINTF("Fatal exception (%d): pc=0x%x badvaddr=0x%x dump area=0x%x\n",
                dump.exc_frame.xt_exccause, dump.pc, dump.badvaddr, &dump);
    // PRINT_FAILURE_STATE();

    // A_ASSFAIL(&dump); // misc module
}

//dummy now
//void app_start(void);

static int
athos_linkage_check(int sz, struct _A_os_linkage_check *link_check)
{
    if (sz != sizeof(struct _A_os_linkage_check)) {
        goto app_link_error;
    }

    if (link_check->version != OS_LINKAGE_VERSION) {
        goto app_link_error;
    }

    if (link_check->table != sizeof(struct _A_magpie_indirection_table) &&
        (link_check->table != 0)) {
        goto app_link_error;
    }

    return 1; /* successful linkage check */

app_link_error:
//    A_PRINTF("athos_linkage_check failure!\n");
    A_PUTS("-A1-\n\r");
    return 0;
}


#ifdef SYSTEM_MODULE_INTR

/* Mask of Interrupt Level bits in Xtensa's Processor Status register */
#define XTENSA_PS_INTLEVEL_MASK 0xf

LOCAL uint32_t
athos_block_all_intrlvl(void)
{
    uint32_t tmp;

    /*
     * This function doesn't actually block ALL interrupts;
     * it leaves ERROR & WDT interrupts -- which are fatal
     * and are at level 3 -- active.
     */
    asm volatile("rsil %0,2" : "=r" (tmp));

    return (uint32_t)((A_UINT32)tmp & XTENSA_PS_INTLEVEL_MASK);
}

LOCAL void
athos_unblock_all_intrlvl(void)
{
    unsigned int tmp;

    asm volatile("rsil %0, 0" : "=r" (tmp));
}

LOCAL void
athos_restore_intrlvl(uint32_t old_intr)
{
    if (old_intr == 0) {
        athos_unblock_all_intrlvl();
    }
}
#endif


static void
AR6002_misaligned_load_handler(CPU_exception_frame_t *exc_frame)
{
    struct register_dump_s dump;
    uint32_t *stkptr;

#if SYSTEM_MODULE_PRINT
    A_PRINTF("misaligned_load\n\r");
#else
    A_PUTS("misaligned_load\n\r");
#endif

    dump.exc_frame = *exc_frame; /* structure copy */
    dump.badvaddr  = XT_RSR_EXCVADDR();
    dump.pc        = exc_frame->xt_pc;

    asm volatile("mov %0,a1" : "=r" (stkptr));

    /* Stores a0,a1,a2,a3 on stack; but leaves sp unchanged */
    xthal_window_spill();

	{
        int i;

#define MAGPIE_REGDUMP_FRAMES 5

        /* Walk back the stack */
        for (i=0; i<MAGPIE_REGDUMP_FRAMES; i++) {
            dump.exc_frame.wb[i].a0 = stkptr[-4];
            dump.exc_frame.wb[i].a1 = stkptr[-3];
            dump.exc_frame.wb[i].a2 = stkptr[-2];
            dump.exc_frame.wb[i].a3 = stkptr[-1];
            if (dump.exc_frame.wb[i].a0 == 0) {
                break;
            }
            stkptr = (uint32_t *)dump.exc_frame.wb[i].a1;
        }
    }

    A_MISALIGNED_LOAD_HANDLER(&dump);

}

static void
AR6002_fatal_exception_handler(CPU_exception_frame_t *exc_frame)
{
    struct register_dump_s dump;

    dump.exc_frame              = *exc_frame; /* structure copy */
    dump.badvaddr               = XT_RSR_EXCVADDR();
    dump.exc_frame.xt_exccause  = XT_RSR_EXCCAUSE();
    dump.pc                     = exc_frame->xt_pc;
    dump.assline                = 0;

#if SYSTEM_MODULE_PRINT
    A_PRINTF("Fatal exception (%d): \tpc=0x%x \n\r\tbadvaddr=0x%x \n\r\tdump area=0x%x\n",
                dump.exc_frame.xt_exccause, dump.pc, dump.badvaddr, &dump);
    PRINT_FAILURE_STATE();
 #else
    A_PUTS("Fatal exception\n\r");
#endif

    A_ASSFAIL(&dump);

     // trigger wdt, in case hang
#if defined(_ROM_)     
    //HAL_WORD_REG_WRITE(MAGPIE_REG_RST_WDT_TIMER_CTRL_ADDR, 0x03);
    //HAL_WORD_REG_WRITE(MAGPIE_REG_RST_WDT_TIMER_ADDR, 0x10);
	A_WDT_ENABLE();
#endif

    while(1)
        ;
}


typedef void (*INSTFN)(void *);

/*
 * These are all modules that reside in ROM which are installed
 * by default by the operating system.  Other ROM modules may
 * be installed by the application if they are needed.
 */
struct {
    void (* install_fn)(void *);
    void *api_tbl;
} basic_ROM_module_table[] =
{

#if SYSTEM_MODULE_MEM
    {(INSTFN)cmnos_mem_module_install,          (void *)&A_CMN(mem)},
#endif

#if SYSTEM_MODULE_MISC
    {(INSTFN)cmnos_misc_module_install,         (void *)&A_CMN(misc)},
#endif

#if SYSTEM_MODULE_PRINT
    {(INSTFN)cmnos_printf_module_install,       (void *)&A_CMN(printf)},
#endif

#if SYSTEM_MODULE_UART
    {(INSTFN)cmnos_uart_module_install,       (void *)&A_CMN(uart)},
#endif

#if SYSTEM_MODULE_USB
    {(INSTFN)cmnos_usb_module_install,       (void *)&A_CMN(usb)},
#endif

#if SYSTEM_MODULE_INTR
    {(INSTFN)cmnos_intr_module_install,       (void *)&A_CMN(intr)},
#endif

#if SYSTEM_MODULE_TIMER
    {(INSTFN)cmnos_timer_module_install,       (void *)&A_CMN(timer)},
#endif

#if SYSTEM_MODULE_CLOCK
    {(INSTFN)cmnos_clock_module_install,       (void *)&A_CMN(clock)},
#endif

#if SYSTEM_MODULE_ALLOCRAM
    {(INSTFN)cmnos_allocram_module_install,       (void *)&A_CMN(allocram)},
#endif

#if SYSTEM_MODULE_ROM_PATCH
    {(INSTFN)cmnos_romp_module_install,       (void *)&A_CMN(romp)},
#endif

#if SYSTEM_MODULE_WDT
    {(INSTFN)cmnos_wdt_module_install,       (void *)&A_CMN(wdt_timer)},
#endif

#if SYSTEM_MODULE_EEPROM
    {(INSTFN)cmnos_eep_module_install,       (void *)&A_CMN(eep)},
#endif
    {(INSTFN)cmnos_string_module_install,        (void *)&A_CMN(string)},
    {(INSTFN)cmnos_tasklet_module_install,        (void *)&A_CMN(tasklet)},
    {(INSTFN)vdesc_module_install,                  (void *)&A_INDIR(vdesc)},
    {(INSTFN)vbuf_module_install,                   (void *)&A_INDIR(vbuf)},
    {(INSTFN)generic_hif_module_install,                   (void *)&A_INDIR(hif)},
    {(INSTFN)buf_pool_module_install,                  (void *)&A_INDIR(buf_pool)},
    {(INSTFN)usbfifo_module_install,                  (void *)&A_INDIR(usbfifo_api)},
    {(INSTFN)dma_engine_module_install,             (void *)&A_INDIR(dma_engine)}, 
    {(INSTFN)dma_lib_module_install,                (void *)&A_INDIR(dma_lib)}, 
};

#define BASIC_ROM_MODULE_TABLE_SZ (sizeof(basic_ROM_module_table)/sizeof(basic_ROM_module_table[0]))

void
generic_hif_module_install(struct hif_api *apis)
{
  A_HOSTIF hostif;

  hostif = A_IS_HOST_PRESENT();

  switch(hostif){
	case HIF_USB:
	  hif_usb_module_install(apis);
      break;
	}
}

void
athos_indirection_table_install(void)
{
    unsigned int i;

    /* Sanity: start with a clear table */
    {
        //char *tbl = (char *)_A_OS_INDIRECTION_TABLE;
        char *tbl = (char *)_A_MAGPIE_INDIRECTION_TABLE;

        //for (i=0; i<_A_OS_INDIRECTION_TABLE_SIZE; i++) {
        for (i=0; i<_A_MAGPIE_INDIRECTION_TABLE_SIZE; i++) {
            tbl[i] = 0;
        }
    }

    /* Install basic ROM modules */
    for (i=0; i<BASIC_ROM_MODULE_TABLE_SZ; i++) {
        basic_ROM_module_table[i].install_fn(basic_ROM_module_table[i].api_tbl);
    }

	#if !defined(_ROM_)
	DBG_MODULE_INSTALL(); // move DBG to indirection table
	#endif

    //_A_OS_INDIRECTION_TABLE->cmnos.app_start = app_start;
    //_A_OS_INDIRECTION_TABLE->cmnos.hal_linkage_check     = athos_linkage_check;
    //_A_MAGPIE_INDIRECTION_TABLE->cmnos.app_start = app_start;
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.hal_linkage_check     = athos_linkage_check;

//    _A_OS_INDIRECTION_TABLE->cmnos.start_bss             = &START_BSS;

#if SYSTEM_MODULE_INTR
    /* Install a few CPU-specific functions */
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.intr._get_intrenable = xthal_get_intenable;
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.intr._set_intrenable = xthal_set_intenable;
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.intr._get_intrpending = xthal_get_interrupt;
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.intr._unblock_all_intrlvl = athos_unblock_all_intrlvl;
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.intr._intr_disable = athos_block_all_intrlvl;
    _A_MAGPIE_INDIRECTION_TABLE->cmnos.intr._intr_restore = athos_restore_intrlvl;
#endif

    /* UNALIGNED references are used for ASSERTs */
    (void)_xtos_set_exception_handler(EXCCAUSE_UNALIGNED, AR6002_misaligned_load_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_LOAD_STORE_ERROR, AR6002_fatal_exception_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_ILLEGAL, AR6002_fatal_exception_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_INSTR_ERROR, AR6002_fatal_exception_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_PRIVILEGED, AR6002_fatal_exception_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_INSTR_DATA_ERROR, AR6002_fatal_exception_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_LOAD_STORE_DATA_ERROR, AR6002_fatal_exception_handler);
    (void)_xtos_set_exception_handler(EXCCAUSE_DIVIDE_BY_ZERO, AR6002_fatal_exception_handler);
}


#ifdef SYSTEM_MODULE_INTR
/*
 * All interrupts pass through here.  Yes, it adds a
 * bit of overhead; but it may be very helpful with
 * debugging, ROM patching, and workarounds.
 *
 * NB: Assembler code that calls this loops through all
 * pending & enabled interrupts.
 */
void
athos_interrupt_handler(unsigned int inum, unsigned int *interrupt_frame)
{
    A_INVOKE_ISR(inum);
}
#endif

void
athos_interrupt_init(void)
{
#ifdef SYSTEM_MODULE_INTR
    int i;
    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x20;

    for (i=0; i<NUM_DIRECT_INTR; i++) {
        (void)_xtos_set_interrupt_handler(i, athos_interrupt_handler);
    }
    
    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x21;
    A_INTR_INIT();
//    A_MC_REG_WRITE(ADDR_ERROR_CONTROL_ADDRESS, ADDR_ERROR_CONTROL_ENABLE_MASK);

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x22;
    athos_unblock_all_intrlvl();
#endif
}



void athos_init(A_HOSTIF hif)
{

    ///////////////////////////////////////////////////////
    //init each module, should be put together..
    A_CLOCK_INIT(SYSTEM_CLK);

    A_UART_INIT();
    A_PRINTF_INIT();

    A_EEP_INIT();
}

void led_on(unsigned int bit)
{
    *(unsigned long *)0x5200c = 1<<bit;
}

void led_off(unsigned int bit)
{
    *(unsigned long *)0x52010 = 1<<bit;
}


void led_all_on() 
{
    led_on(10);
    led_on(12);
}

void led_all_off()
{
    led_off(10);
    led_off(12);
}


unsigned long i=0;
#define LED_ON_OFF_FREQ 500

void led_task()
{
    i++;
   
    if(i==LED_ON_OFF_FREQ*1)
        led_on(10);
    else if (i==LED_ON_OFF_FREQ*2)
        led_on(12);
    else if (i==LED_ON_OFF_FREQ*3)
        led_off(12);
    else if (i==LED_ON_OFF_FREQ*4)
        led_off(10);
    else if (i==LED_ON_OFF_FREQ*5)
        led_all_on();
    else if (i==LED_ON_OFF_FREQ*6)
    {
        i=0;
        led_all_off();
    }
}


void bootload()
{
    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0xe;
    CURRENT_PROGRAM = (uint32_t)bootload;
    A_PUTS("8. wait for read/read_comp.... \n\r");
    while(1) {

        /* update wdt timer */
        //A_WDT_TASK();

        /* high priority tasks */
        A_USB_ROM_TASK();
        
//        A_DBG_TASK();
        led_task();

        if( download_enable )
            break;
    }

}

void
change_magpie_clk(uint32_t  cpu_freq, uint32_t ahb_div)
{
    volatile uint32_t i = 0;
    volatile uint32_t rd_data = 0, wd_data = 0;

    /* Put the PLL into reset */
    rd_data = HAL_WORD_REG_READ(0x00050010) | (1<<1);
    HAL_WORD_REG_WRITE(0x00050010,rd_data);

    HAL_WORD_REG_WRITE(0x00056004, 0x11);
    rd_data = HAL_WORD_REG_READ(0x00056004) & 0x1;

    /* Wait for the update bit to get cleared */
    while (rd_data)
        rd_data = HAL_WORD_REG_READ(0x00056004) & 0x1;

    /* Setting of the PLL */
    if (cpu_freq== 100) wd_data = 0x142;      /* PLL 400 MHz*/
    else if (cpu_freq== 105) wd_data = 0x152; /* PLL 420 MHz */
    else if (cpu_freq== 110) wd_data = 0x162; /* PLL 440 MHz*/
    else if (cpu_freq== 115) wd_data = 0x172; /* PLL 460 MHz */
    else if (cpu_freq== 120) wd_data = 0x182; /* PLL 480 MHz */
    else if (cpu_freq== 125) wd_data = 0x192; /* PLL 500 MHz */
    else if (cpu_freq== 130) wd_data = 0x1a2; /* PLL 520 MHz */
    else if (cpu_freq== 135) wd_data = 0x1b2; /* PLL 540 MHz */
    else if (cpu_freq== 140) wd_data = 0x1c2; /* PLL 560 MHz */
    else if (cpu_freq== 145) wd_data = 0x1d2; /* PLL 580 MHz */
    else if (cpu_freq== 150) wd_data = 0x1e2; /* PLL 600 MHz */
    else if (cpu_freq== 155) wd_data = 0x1f2; /* PLL 620 MHz */
    else if (cpu_freq== 160) wd_data = 0x202; /* PLL 640 MHz */
    else if (cpu_freq== 165) wd_data = 0x212; /* PLL 660 MHz */
    else if (cpu_freq== 170) wd_data = 0x222; /* PLL 680 MHz */
    else if (cpu_freq== 175) wd_data = 0x232; /* PLL 700 MHz */
    else if (cpu_freq== 180) wd_data = 0x242; /* PLL 720 MHz */
    else if (cpu_freq== 185) wd_data = 0x252; /* PLL 740 MHz */
    else if (cpu_freq== 190) wd_data = 0x262; /* PLL 760 MHz */
    else if (cpu_freq== 195) wd_data = 0x272; /* PLL 780 MHz */
    else if (cpu_freq== 200) wd_data = 0x142; /* PLL 400 MHz */
    else if (cpu_freq== 210) wd_data = 0x152; /* PLL 420 MHz */
    else if (cpu_freq== 220) wd_data = 0x162; /* PLL 440 MHz */
    else if (cpu_freq== 230) wd_data = 0x172; /* PLL 460 MHz */
    else if (cpu_freq== 240) wd_data = 0x182; /* PLL 480 MHz */
    else if (cpu_freq== 250) wd_data = 0x192; /* PLL 500 MHz */
    else if (cpu_freq== 260) wd_data = 0x1a2; /* PLL 520 MHz */
    else if (cpu_freq== 270) wd_data = 0x1b2; /* PLL 540 MHz */
    else if (cpu_freq== 280) wd_data = 0x1c2; /* PLL 560 MHz */
    else if (cpu_freq== 290) wd_data = 0x1d2; /* PLL 580 MHz */
    else if (cpu_freq== 300) wd_data = 0x1e2; /* PLL 600 MHz */
    else if (cpu_freq== 310) wd_data = 0x1f2; /* PLL 620 MHz */
    else if (cpu_freq== 320) wd_data = 0x202; /* PLL 640 MHz */
    else if (cpu_freq== 330) wd_data = 0x212; /* PLL 660 MHz */
    else if (cpu_freq== 340) wd_data = 0x222; /* PLL 680 MHz */
    else if (cpu_freq== 350) wd_data = 0x232; /* PLL 700 MHz */
    else if (cpu_freq== 360) wd_data = 0x242; /* PLL 720 MHz */
    else if (cpu_freq== 370) wd_data = 0x252; /* PLL 740 MHz */
    else if (cpu_freq== 380) wd_data = 0x262; /* PLL 760 MHz */
    else if (cpu_freq== 390) wd_data = 0x272; /* PLL 780 MHz */
    else if (cpu_freq== 400) wd_data = 0x282; /* PLL 800 MHz */
    else wd_data = 0x142;                     /* PLL 400 MHz*/

    HAL_WORD_REG_WRITE(0x00056000, wd_data);

    /* Pull CPU PLL out of Reset */
    rd_data = HAL_WORD_REG_READ(0x00050010) & ~(1<<1);
    HAL_WORD_REG_WRITE(0x00050010,rd_data);

    /* CPU & AHB settings */
    rd_data = HAL_WORD_REG_READ(0x00056004);

    /*  > 200 Mhz CPU clock (PLL / 2) or  < 200 Mhz (PLL / 4) */
    if (cpu_freq > 195)
        rd_data = (rd_data & ~(0xff<<16)) | (1<<16);
    else
        rd_data = (rd_data & ~(0xff<<16)) | (2<<16);

    /* AHB Clock, AHB_FREQ = CPU_FREQ / ahb_div */
    switch (ahb_div) {
    case 1:
        rd_data = (rd_data & ~(0x3<<8) & ~(1<<4)) | 0x1;
        break;
    case 2:
        rd_data = (rd_data & ~(0x3<<8) & ~(1<<4)) | (1<<8) | 0x1;
        break;
    case 4:
        rd_data = (rd_data & ~(0x3<<8) & ~(1<<4)) | (2<<8) | 0x1;
        break;
    default:
        rd_data = (rd_data & ~(0x3<<8) & ~(1<<4)) | (1<<8) | 0x1;
        break;
    }
    
    HAL_WORD_REG_WRITE(0x00056004, rd_data);
    rd_data = HAL_WORD_REG_READ(0x00056004) & 0x1;

    while(rd_data)
        rd_data = HAL_WORD_REG_READ(0x00056004) & 0x1;

    while(i++ < 1000)
        ;
    
    /* UART Setting */
    A_UART_HWINIT((cpu_freq / ahb_div) * (1000*1000), 115200);

//    A_PRINTF("reg_read(0x56000): %p \n", HAL_WORD_REG_READ(0x00056000));
//    A_PRINTF("reg_read(0x56004): %p \n", HAL_WORD_REG_READ(0x00056004));

    /* set the current reference clock */
//    A_CLOCK_INIT(cpu_freq);

}

/* 
 * rom1.0 fix: turn off rc if no patch/eeprom exist
*/
void turn_off_rc()
{
    extern BOOLEAN eep_state;

	// clear the cmnos_eeprom init state
	eep_state = FALSE;

    // reset the pcie_rc shift, pll and phy
    HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)|(BIT10|BIT9|BIT8|BIT7)));
        
    // reset ahb_arb of pcie_rc
    HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_AHB_ARB_ADDR)|BIT1));
}

void bootentry(void)
{
    /* uint32_t reset_temp; */
    A_HOSTIF hostif=0x0;
    T_BOOT_TYPE rst_status;
    T_EEP_RET retEEP;

    ///////////////////////////////////
    athos_indirection_table_install();

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x1;
    CURRENT_PROGRAM = (uint32_t)bootentry;
    // athos module install
    athos_init(hostif);     // move all the athos indirection table init function to here

    athos_interrupt_init(); // install all interrupt function to known state

    A_WDT_DISABLE();        // make srue wdt is diable

    rst_status = A_WDT_LASTBOOT(); 

    // pump up flash clock to 12.5Mhz
    HAL_WORD_REG_WRITE(0x5b01c, 0x401);
    
        /*
         *
         * 1. turn on CPU PLL, reg(0x560000), 0x305
         * 2. pll reset reg(0x50010), 0x03
         * 3. pll reset reg(0x50010), 0x01
         *
         * - after enabling CPU PLL, left the interface pll setting
         *   be done in each interface
         *
         * e.g usb_init we mdid
         * 4. usb divide reg(0x56008), 0x0808
         * 5. clear register reg(0x50010), bit0, bit3, bit4
         * 6. set register reg(0x50010), bit0, bit3, bit4
         * 7. clear register reg(0x50010), bit0, bit3, bit4
         *
         *  - wait for 200ms for usb phy 30mhz stable -
         *
         * 8. usb clock up, proceed reset of things
         */

    	/* reset_temp = HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR); */
        /* A_PRINTF("reset temp is %x \n",reset_temp); */
        /* HAL_WORD_REG_WRITE( MAGPIE_REG_RST_RESET_ADDR, 0); */
        

    /*! move the whole cpu pll setup to host interface specific 
     *  since when bootup, we have an external clock source
     */
    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x2;

    hostif = A_IS_HOST_PRESENT();

/*!
 *   GPIO_FUNCTION(0x28) - config uart (sin, sout) pair, 
 *
 *   pci host interface will only have (GPIO1, GPIO0), other hif (usb, pcie, gmac)
 *   will use (GPIO5, GPIO4)
 *
 *   BIT8 --> (9,8)
 *   BIT7 --> (7,6)
 *   BIT6 --> (5,4)
 *   BIT5 --> (3,2)
 *   BIT4 --> (1,0)
 *   
 */
    {
        HAL_WORD_REG_WRITE( MAGPIE_REG_GPIO_FUNCTION, (HAL_WORD_REG_READ(MAGPIE_REG_GPIO_FUNCTION)&(~(BIT4|BIT5|BIT6|BIT7|BIT8))) );
        HAL_WORD_REG_WRITE( MAGPIE_REG_GPIO_FUNCTION, (HAL_WORD_REG_READ(MAGPIE_REG_GPIO_FUNCTION)|(BIT8)) );
    }

    change_magpie_clk(200, 2);

    // power on self test
    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x5;
	A_PUTS("\n - Boot from SFLASH - \n\r");

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x9;

    /*!
     * check the host interface type,
     */
    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x15;
    hostif = A_IS_HOST_PRESENT();

    retEEP = A_EEP_IS_EXIST();

    turn_off_rc();

    if( hostif == HIF_USB )
    {
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0xb;
#if 0
        if( retEEP == RET_SUCCESS)
        {
            A_EEP_INIT();
            /* read the usb descriptor information from rom to ram */
            read_usb_conf();
            
            turn_off_rc();
        }    
#endif
        A_USB_INIT();

        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0xd;
        bootload();
    }

}


int main(void)
{
    *(unsigned long *)0x52000 = 0x7ebff;    // set bit10/bit12 output mode
    *(unsigned long *)0x0053fff8 = 0x0;
    
    // for debug purpose in case we don't know where we are
    // keep this address update, so that we could trace the where is is
    DEBUG_SYSTEM_STATE = 0x0;

    bootentry();

    A_PRINTF("FLASH_READ_COMP, jump to firmware\n");
 
	led_on(10);
    led_on(12);

    return 0;
}

