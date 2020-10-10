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
/*************************************************************************/
/*  Copyright (c) 2006 Atheros Communications, Inc., All Rights Reserved */
/*                                                                       */
/*  Module Name : rom_cfg.h                                              */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains definition of platform and sysmte config   .  */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/

#ifndef _ROM_CFG_H_
#define _ROM_CFG_H_

/************************** FPGA version **************************/
#define MAGPIE_FPGA_RAM_256K         1

/************************** SYSTEM WIDE ***************************/
/* Release Code :
 * D : Daily build (Development)
 * R : Official Release
 */
#define ATH_VER_RELEASE_CODE        "D"
#define ATH_VER_PLATFORM_NUMBER     "0"
#define ATH_VER_MAJOR_NUMBER        "0"
#define ATH_VER_MINOR_NUMBER        "0"
#define ATH_VER_BUILD_NUMBER        "3"

#define ATH_VER_DATES               __DATE__" "__TIME__

#define ATH_VERSION_STR             "["ATH_VER_RELEASE_CODE       "." \
                                    ATH_VER_PLATFORM_NUMBER "." \
                                    ATH_VER_MAJOR_NUMBER    "." \
                                    ATH_VER_MINOR_NUMBER    "." \
                                    ATH_VER_BUILD_NUMBER    "] " \
                                    ATH_VER_DATES

/* ROM Code Version (16 bit)
 * Bit 15   : 0 means ASIC, 1 means FPGA
 * Bit 14   : 0 means ROM, 1 means FLASH
 * Bit 13-8 : Major Version Number
 * Bit 7-0  : Minor Version Number
 */
#if defined(MAGPIE_FPGA)
#define ROM_PLATFORM             (1)
#else
#define ROM_PLATFORM             (0)
#endif

/* Define ROM Code Version Number here */
#define ROM_MAJOR_VER_NUM        (1)
#define ROM_MINOR_VER_NUM        (11)

#define BOOTROM_VER              ( (ROM_PLATFORM<<15) | (ROM_MAJOR_VER_NUM<<8) | ROM_MINOR_VER_NUM )


#define SYSTEM_FREQ                 40

#define SYSTEM_CLK                  SYSTEM_FREQ*1000*1000    //40mhz

#define ONE_MSEC                    (SYSTEM_FREQ*1000)

/////////////////////////////////////////////////////////////////
/*
 * Supported reference clock speeds.
 *
 * Note: MAC HAL code has multiple tables indexed by these values,
 * so do not rearrange them.  Add any new refclk values at the end.
 */
typedef enum {
    SYS_CFG_REFCLK_UNKNOWN      = -1, /* Unsupported ref clock -- use PLL Bypass */
    SYS_CFG_REFCLK_10_MHZ       = 0,
    SYS_CFG_REFCLK_20_MHZ       = 1,
    SYS_CFG_REFCLK_40_MHZ       = 2,
} A_refclk_speed_t;

/////////////////////////////////////////////////////////////////


/////////////////////////////////////////////////////////////////
// cmnos interface

    #define SYSTEM_MODULE_MEM           1

    #define SYSTEM_MODULE_MISC          1

    #define SYSTEM_MODULE_USB           1

    #if SYSTEM_MODULE_USB
        #define SYSTEM_MODULE_HP_EP1    1
        #define SYSTEM_MODULE_HP_EP5    1
        #define SYSTEM_MODULE_HP_EP6    1
    #endif

    #define SYSTEM_MODULE_INTR          1

    #define SYSTEM_MODULE_CLOCK         1

	#define SYSTEM_MODULE_DESC      	0

    #define SYSTEM_MODULE_ALLOCRAM      1

    #define SYSTEM_MODULE_UART          1              //uart module to dump the dbg message

    #define SYSTEM_MODULE_TIMER         1               // a virtual timer, before we don't have the real timer

    #define SYSTEM_MODULE_WDT           1                 // a watchdog timer

    #define SYSTEM_MODULE_EEPROM        1           // a eeprom interface (pcie_rc's eeprom not apb eeprom)

    #if SYSTEM_MODULE_UART
        #define SYSTEM_MODULE_PRINT     1   // dependency on UART module
        #define SYSTEM_MODULE_DBG       0  // dependency on PRINT & UART module
    #endif

    #define SYSTEM_MODULE_ROM_PATCH     1           // patch install module

#define SYSTEM_MODULE_PCI				1

#define SYSTEM_MODULE_GMAC				0

#define SYSTEM_MODULE_SFLASH           1 

#define SYSTEM_MODULE_TESTING           0               // backdoor test module

#if SYSTEM_MODULE_TESTING
#define SYSTEM_MODULE_MEMORY_TEST       0
#define SYSTEM_MODULE_DHRYSTONE_TEST    0

#define SYSTEM_MODULE_SYS_MONITOR       0
#define SYSTEM_MODULE_IDLE_TASK       	0

#endif /* SYSTEM_MODULE_TESTING */

/****************************** UART ******************************/
#define UART_INPUT_CLK                  SYSTEM_CLK
#define UART_DEFAULT_BAUD               115200
#define UART_RETRY_COUNT                10000

/****************************** USB *******************************/

/* Firmware Loopback */
#define ZM_FM_LOOPBACK                  0
#define ZM_SELF_TEST_MODE               1         // USB-IF Eye Pattern Test

#define ENABLE_SWAP_DATA_MODE           1       // byte swap function
#define ENABLE_SW_SWAP_DATA_MODE        1

#define ENABLE_STREAM_MODE              0       // stream mode

#define USB_STREAM_MODE_AGG_CNT         0         // 2 packets, 2: 3packets, 3: 4packets etc...
#define USB_STREAM_MODE_TIMEOUT_CTRL    0x0     // the unit is 32 USB (30Mhz) clock cycles
#define USB_STREAM_MODE_HOST_BUF_SZ     (BIT4)    // define the host dma buffer size (bit5,bit4)- 4096(0,0) 8192 (0,1) 16384(1,0) 32768(1,1) bytes

/************************* MEMORY DEFS ***************************/

#if defined(PROJECT_MAGPIE)
    #include "magpie_mem.h"
#elif defined(PROJECT_K2)
    #include "k2_mem.h"
#endif


// the end of 16 bytes are used to record some debug state and watchdog event and counter
#define WATCH_DOG_MAGIC_PATTERN_ADDR    (SYS_D_RAM_REGION_0_BASE+SYS_RAM_SZIE-0x4)        //  0x53fffc,magic pattern address
#define WATCH_DOG_RESET_COUNTER_ADDR    (SYS_D_RAM_REGION_0_BASE+SYS_RAM_SZIE-0x8)        //  0x53fff8,record the reset counter
#define DEBUG_SYSTEM_STATE_ADDR         (SYS_D_RAM_REGION_0_BASE+SYS_RAM_SZIE-0xc)        //  0x53fff4,record the state of system
#define CURRENT_PROGRAM_ADDR            (SYS_D_RAM_REGION_0_BASE+SYS_RAM_SZIE-0x10)       //  0x53fff0,reserved 

#define WATCH_DOG_MAGIC_PATTERN         (*((volatile u32_t*)(WATCH_DOG_MAGIC_PATTERN_ADDR)))
#define WATCH_DOG_RESET_COUNTER         (*((volatile u32_t*)(WATCH_DOG_RESET_COUNTER_ADDR)))
#define DEBUG_SYSTEM_STATE              (*((volatile u32_t*)(DEBUG_SYSTEM_STATE_ADDR)))
#define CURRENT_PROGRAM                 (*((volatile u32_t*)(CURRENT_PROGRAM_ADDR)))

#define WDT_MAGIC_PATTERN         		0x5F574454     	//_WDT
#define SUS_MAGIC_PATTERN         		0x5F535553      //_SUS

// move to sys_cfg.h
/************************* WLAN DEFS ***************************/
//#define MAGPIE_ENABLE_WLAN              1
//#define MAGPIE_ENABLE_PCIE              1
//#define MAGPIE_ENABLE_WLAN_IN_TARGET    0
//#define MAGPIE_ENABLE_WLAN_SELF_TX      0

/****************************** WATCH DOG *******************************/
#define WDT_DEFAULT_TIMEOUT_VALUE   3*ONE_MSEC*1000 // Initial value is 3 seconds, firmware changes it to 65 milliseconds

#endif /* _ROM_CFG_H_ */
