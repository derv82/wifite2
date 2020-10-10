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
/*  Module Name : reg_defs.h                                             */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains the register addr and marco definition.       */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/
#ifndef _REG_DEFS_H_
#define _REG_DEFS_H_

#include "dt_defs.h"

#define BIT_SET(bit)	(1<<bit)
#define BIT_CLR(bit)	(0<<bit)

/***** REGISTER BASE ADDRESS DEFINITION *****/
#define RESET_VECTOR_ADDRESS        0x8e0000
/********************************************/

/***** REGISTER BASE ADDRESS DEFINITION *****/
#define USB_CTRL_BASE_ADDRESS     	0x00010000
#define RST_BASE_ADDRESS          	0x00050000
#define UART_BASE_ADDRESS       	0x00051000
#define HOST_DMA_BASE_ADDRESS   	0x00053000
#define USB_DMA_BASE_ADDRESS            0x00055000
#define SPI_REG_BASE_ADDRESS		0x0005B000
#define WLAN_BASE_ADDRESS           0x10000000
#define MAC_REG_BASE_ADDRESS        WLAN_BASE_ADDRESS
/*******************************************************************************/
/* Reset Register*/
#define MAGPEI_REG_RST_BASE_ADDR                    RST_BASE_ADDRESS

#define REG_GENERAL_TIMER_OFFSET                    0x0
#define REG_GENERAL_TIMER_RELOAD_OFFSET             0x4
#define REG_WATCHDOG_TIMER_CONTROL_OFFSET           0x8
#define REG_WATCHDOG_TIMER_OFFSET                   0xC
#define REG_RESET_OFFSET                            0x10
#define REG_BOOTSTRAP                               0x14
#define REG_AHB_ARB                                 0x18
#define REG_WATCHDOG_INTR_OFFSET                    0x1C
#define REG_GENERAL_TIMER_INTR_OFFSET               0x20
#define REG_REVISION_ID                             0x90
#define REG_CLOCK_CONTROL_OFFSET                    0x40
#define REG_RST_PWDN_CONTROL_OFFSET                 0x44
#define REG_USB_PLL_OFFSET                          0x48
#define REG_RST_STATUS_OFFSET                       0x4C


#define MAGPEI_REG_RST_GENERAL_TIMER_ADDR       (RST_BASE_ADDRESS+REG_GENERAL_TIMER_OFFSET)
#define MAGPIE_REG_RST_GENERAL_TIMER_RLD_ADDR   (RST_BASE_ADDRESS+REG_GENERAL_TIMER_RELOAD_OFFSET)
#define MAGPIE_REG_RST_WDT_TIMER_CTRL_ADDR      (RST_BASE_ADDRESS+REG_WATCHDOG_TIMER_CONTROL_OFFSET)
#define MAGPIE_REG_RST_WDT_TIMER_ADDR           (RST_BASE_ADDRESS+REG_WATCHDOG_TIMER_OFFSET)
#define MAGPIE_REG_RST_RESET_ADDR               (RST_BASE_ADDRESS+REG_RESET_OFFSET)
#define MAGPIE_REG_RST_BOOTSTRAP_ADDR           (RST_BASE_ADDRESS+REG_BOOTSTRAP)
#define MAGPIE_REG_AHB_ARB_ADDR                 (RST_BASE_ADDRESS+REG_AHB_ARB)
#define MAGPIE_REG_RST_WDT_INTR_ADDR            (RST_BASE_ADDRESS+REG_WATCHDOG_INTR_OFFSET)
#define MAGPIE_REG_RST_GENERAL_TIMER_INTR_ADDR  (RST_BASE_ADDRESS+REG_GENERAL_TIMER_INTR_OFFSET)
#define MAGPIE_REG_REVISION_ID_ADDR             (RST_BASE_ADDRESS+REG_REVISION_ID)
#define MAGPIE_REG_CLOCK_CTRL_ADDR              (RST_BASE_ADDRESS+REG_CLOCK_CONTROL_OFFSET)
#define MAGPIE_REG_RST_PWDN_CTRL_ADDR           (RST_BASE_ADDRESS+REG_RST_PWDN_CONTROL_OFFSET)
#define MAGPIE_REG_USB_PLL_ADDR                 (RST_BASE_ADDRESS+REG_USB_PLL_OFFSET)
#define MAGPIE_REG_RST_STATUS_ADDR              (RST_BASE_ADDRESS+REG_RST_STATUS_OFFSET)

#define MAGPEI_REG_RST_GENERAL_TIMER            (*((volatile u32_t*)(MAGPEI_REG_RST_GENERAL_TIMER_ADDR)))
#define MAGPIE_REG_RST_GENERAL_TIMER_RLD        (*((volatile u32_t*)(MAGPIE_REG_RST_GENERAL_TIMER_RLD_ADDR)))
#define MAGPIE_REG_RST_WDT_TIMER_CTRL           (*((volatile u32_t*)(MAGPIE_REG_RST_WDT_TIMER_CTRL_ADDR)))
#define MAGPIE_REG_RST_WDT_TIMER                (*((volatile u32_t*)(MAGPIE_REG_RST_WDT_TIMER_ADDR)))
#define MAGPIE_REG_RST_RESET                    (*((volatile u32_t*)(MAGPIE_REG_RST_RESET_ADDR)))
#define MAGPIE_REG_RST_BOOTSTRAP                (*((volatile u32_t*)(MAGPIE_REG_RST_BOOTSTRAP_ADDR)))
#define MAGPIE_REG_AHB_ARB                      (*((volatile u32_t*)(MAGPIE_REG_AHB_ARB_ADDR)))
#define MAGPIE_REG_REVISION_ID                  (*((volatile u32_t*)(MAGPIE_REG_REVISION_ID_ADDR)))
#define MAGPIE_REG_CLOCK_CTRL                   (*((volatile u32_t*)(MAGPIE_REG_CLOCK_CTRL_ADDR)))
#define MAGPIE_REG_RST_PWDN_CTRL                (*((volatile u32_t*)(MAGPIE_REG_RST_PWDN_CTRL_ADDR)))
#define MAGPIE_REG_USB_PLL                      (*((volatile u32_t*)(MAGPIE_REG_USB_PLL_ADDR)))
#define MAGPIE_REG_RST_STATUS                   (*((volatile u32_t*)(MAGPIE_REG_RST_STATUS_ADDR)))


/*******************************************************************************/
/* USB DMA Register*/

#define MAGPIE_REG_USB_INTERRUPT_ADDR           USB_DMA_BASE_ADDRESS
#define MAGPIE_REG_USB_INTERRUPT_MASK_ADDR      (USB_DMA_BASE_ADDRESS + 0x4)

#define MAGPIE_REG_USB_RX0_DESC_START_ADDR      (USB_DMA_BASE_ADDRESS + 0x800)
#define MAGPIE_REG_USB_RX0_DMA_START_ADDR       (USB_DMA_BASE_ADDRESS + 0x804)
#define MAGPIE_REG_USB_RX0_BURST_SIZE_ADDR      (USB_DMA_BASE_ADDRESS + 0x808)
#define MAGPIE_REG_USB_RX0_STATE_ADDR           (USB_DMA_BASE_ADDRESS + 0x814)
#define MAGPIE_REG_USB_RX0_CUR_TRACE_ADDR       (USB_DMA_BASE_ADDRESS + 0x818)
#define MAGPIE_REG_USB_RX0_SWAP_DATA_ADDR       (USB_DMA_BASE_ADDRESS + 0x81C)

#define MAGPIE_REG_USB_RX1_DESC_START_ADDR      (USB_DMA_BASE_ADDRESS + 0x900)
#define MAGPIE_REG_USB_RX1_DMA_START_ADDR       (USB_DMA_BASE_ADDRESS + 0x904)
#define MAGPIE_REG_USB_RX1_BURST_SIZE_ADDR      (USB_DMA_BASE_ADDRESS + 0x908)
#define MAGPIE_REG_USB_RX1_STATE_ADDR           (USB_DMA_BASE_ADDRESS + 0x914)
#define MAGPIE_REG_USB_RX1_CUR_TRACE_ADDR       (USB_DMA_BASE_ADDRESS + 0x918)
#define MAGPIE_REG_USB_RX1_SWAP_DATA_ADDR       (USB_DMA_BASE_ADDRESS + 0x91C)

#define MAGPIE_REG_USB_RX2_DESC_START_ADDR      (USB_DMA_BASE_ADDRESS + 0xa00)
#define MAGPIE_REG_USB_RX2_DMA_START_ADDR       (USB_DMA_BASE_ADDRESS + 0xa04)
#define MAGPIE_REG_USB_RX2_BURST_SIZE_ADDR      (USB_DMA_BASE_ADDRESS + 0xa08)
#define MAGPIE_REG_USB_RX2_STATE_ADDR           (USB_DMA_BASE_ADDRESS + 0xa14)
#define MAGPIE_REG_USB_RX2_CUR_TRACE_ADDR       (USB_DMA_BASE_ADDRESS + 0xa18)
#define MAGPIE_REG_USB_RX2_SWAP_DATA_ADDR       (USB_DMA_BASE_ADDRESS + 0xa1C)

#define MAGPIE_REG_USB_TX0_DESC_START_ADDR      (USB_DMA_BASE_ADDRESS + 0xC00)
#define MAGPIE_REG_USB_TX0_DMA_START_ADDR       (USB_DMA_BASE_ADDRESS + 0xC04)
#define MAGPIE_REG_USB_TX0_BURST_SIZE_ADDR      (USB_DMA_BASE_ADDRESS + 0xC08)
#define MAGPIE_REG_USB_TX0_STATE_ADDR           (USB_DMA_BASE_ADDRESS + 0xC10)
#define MAGPIE_REG_USB_TX0_CUR_TRACE_ADDR       (USB_DMA_BASE_ADDRESS + 0xC14)
#define MAGPIE_REG_USB_TX0_SWAP_DATA_ADDR       (USB_DMA_BASE_ADDRESS + 0xC18)

#define MAGPIE_REG_USB_INTERRUPT_TX0_END         (1<<24) //0x1000000
#define MAGPIE_REG_USB_INTERRUPT_TX0_COMPL       (1<<16) //0x10000
#define MAGPIE_REG_USB_INTERRUPT_RX2_END         (1<<10) //0x00400
#define MAGPIE_REG_USB_INTERRUPT_RX1_END         (1<<9) //0x00200
#define MAGPIE_REG_USB_INTERRUPT_RX0_END         (1<<8)  //0x0100
#define MAGPIE_REG_USB_INTERRUPT_RX2_COMPL       (1<<2) //0x00004

#define MAGPIE_REG_USB_INTERRUPT_RX1_COMPL       (1<<1) //0x00002
#define MAGPIE_REG_USB_INTERRUPT_RX0_COMPL       (1<<0)  //0x00001


#define MAGPIE_REG_USB_INTERRUPT                (*((volatile u32_t*)(MAGPIE_REG_USB_INTERRUPT_ADDR)))
#define MAGPIE_REG_USB_INTERRUPT_MASK           (*((volatile u32_t*)(MAGPIE_REG_USB_INTERRUPT_MASK_ADDR)))

#define MAGPIE_REG_USB_RX0_DESC_START           (*((volatile u32_t*)(MAGPIE_REG_USB_RX0_DESC_START_ADDR)))
#define MAGPIE_REG_USB_RX0_DMA_START            (*((volatile u32_t*)(MAGPIE_REG_USB_RX0_DMA_START_ADDR)))
#define MAGPIE_REG_USB_RX0_BURST_SIZE           (*((volatile u32_t*)(MAGPIE_REG_USB_RX0_BURST_SIZE_ADDR)))
#define MAGPIE_REG_USB_RX0_STATE                    (*((volatile u32_t*)(MAGPIE_REG_USB_RX0_STATE_ADDR)))
#define MAGPIE_REG_USB_RX0_CUR_TRACE            (*((volatile u32_t*)(MAGPIE_REG_USB_RX0_CUR_TRACE_ADDR)))
#define MAGPIE_REG_USB_RX0_SWAP_DATA            (*((volatile u32_t*)(MAGPIE_REG_USB_RX0_SWAP_DATA_ADDR)))


#define MAGPIE_REG_USB_RX1_DESC_START           (*((volatile u32_t*)(MAGPIE_REG_USB_RX1_DESC_START_ADDR)))
#define MAGPIE_REG_USB_RX1_DMA_START            (*((volatile u32_t*)(MAGPIE_REG_USB_RX1_DMA_START_ADDR)))
#define MAGPIE_REG_USB_RX1_BURST_SIZE           (*((volatile u32_t*)(MAGPIE_REG_USB_RX1_BURST_SIZE_ADDR)))
#define MAGPIE_REG_USB_RX1_STATE                    (*((volatile u32_t*)(MAGPIE_REG_USB_RX1_STATE_ADDR)))
#define MAGPIE_REG_USB_RX1_CUR_TRACE            (*((volatile u32_t*)(MAGPIE_REG_USB_RX1_CUR_TRACE_ADDR)))
#define MAGPIE_REG_USB_RX1_SWAP_DATA            (*((volatile u32_t*)(MAGPIE_REG_USB_RX1_SWAP_DATA_ADDR)))

#define MAGPIE_REG_USB_RX2_DESC_START           (*((volatile u32_t*)(MAGPIE_REG_USB_RX2_DESC_START_ADDR)))
#define MAGPIE_REG_USB_RX2_DMA_START            (*((volatile u32_t*)(MAGPIE_REG_USB_RX2_DMA_START_ADDR)))
#define MAGPIE_REG_USB_RX2_BURST_SIZE           (*((volatile u32_t*)(MAGPIE_REG_USB_RX2_BURST_SIZE_ADDR)))
#define MAGPIE_REG_USB_RX2_STATE                    (*((volatile u32_t*)(MAGPIE_REG_USB_RX2_STATE_ADDR)))
#define MAGPIE_REG_USB_RX2_CUR_TRACE            (*((volatile u32_t*)(MAGPIE_REG_USB_RX2_CUR_TRACE_ADDR)))
#define MAGPIE_REG_USB_RX2_SWAP_DATA            (*((volatile u32_t*)(MAGPIE_REG_USB_RX2_SWAP_DATA_ADDR)))


#define MAGPIE_REG_USB_TX0_DESC_START           (*((volatile u32_t*)(MAGPIE_REG_USB_TX0_DESC_START_ADDR)))
#define MAGPIE_REG_USB_TX0_DMA_START            (*((volatile u32_t*)(MAGPIE_REG_USB_TX0_DMA_START_ADDR)))
#define MAGPIE_REG_USB_TX0_BURST_SIZE           (*((volatile u32_t*)(MAGPIE_REG_USB_TX0_BURST_SIZE_ADDR)))
#define MAGPIE_REG_USB_TX0_STATE                    (*((volatile u32_t*)(MAGPIE_REG_USB_TX0_STATE_ADDR)))
#define MAGPIE_REG_USB_TX0_CUR_TRACE            (*((volatile u32_t*)(MAGPIE_REG_USB_TX0_CUR_TRACE_ADDR)))
#define MAGPIE_REG_USB_TX0_SWAP_DATA            (*((volatile u32_t*)(MAGPIE_REG_USB_TX0_SWAP_DATA_ADDR)))

/*******************************************************************************/
/***************************/
#define MAGPIE_REG_SPI_BASE_ADDR	SPI_REG_BASE_ADDRESS

#define REG_SPI_CS_OFFSET		0x0
#define REG_SPI_AO_OFFSET                           0x4
#define REG_SPI_D_OFFSET                            0x8
#define REG_SPI_CLKDIV_OFFSET                       0x1C


#define MAGPIE_REG_SPI_CS_ADDR		            (SPI_REG_BASE_ADDRESS + REG_SPI_CS_OFFSET)
#define MAGPIE_REG_SPI_AO_ADDR                      (SPI_REG_BASE_ADDRESS + REG_SPI_AO_OFFSET)
#define MAGPIE_REG_SPI_D_ADDR                       (SPI_REG_BASE_ADDRESS + REG_SPI_D_OFFSET)
#define MAGPIE_REG_SPI_CLKDIV_ADDR                  (SPI_REG_BASE_ADDRESS + REG_SPI_CLKDIV_OFFSET)

/*******************************************************************************/
#define K2_REG_MAC_BASE_ADDR                        MAC_REG_BASE_ADDRESS

#define REG_PLL_CONTROL_OFFSET                      0x7014
#define REG_RTC_FORCE_OFFSET                        0x7040
#define REG_RTC_STATUS_OFFSET                       0x7044

#define K2_REG_PLL_CONTROL_ADDR                     (MAC_REG_BASE_ADDRESS + REG_PLL_CONTROL_OFFSET)
#define K2_REG_RTC_FORCE_ADDR                       (MAC_REG_BASE_ADDRESS + REG_RTC_FORCE_OFFSET)
#define K2_REG_RTC_STATUS_ADDR                      (MAC_REG_BASE_ADDRESS + REG_RTC_STATUS_OFFSET)
#endif
