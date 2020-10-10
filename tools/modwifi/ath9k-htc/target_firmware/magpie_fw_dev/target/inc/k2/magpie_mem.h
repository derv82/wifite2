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
/*  Module Name : mem_addrs.h                                            */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains definition of the memory related information. */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/

#ifndef _MEM_ADDRS_H_
#define _MEM_ADDRS_H_

#define SYS_ROM_BLOCK_SIZE         	(32*1024)
#if MAGPIE_FPGA_RAM_256K == 1   
#define SYS_ROM_BLOCK_NUM                   2         //ram 256K version is also rom 64k version
#else
#define SYS_ROM_BLOCK_NUM               3
#endif
#define SYS_ROM_SIZE                    (SYS_ROM_BLOCK_SIZE*SYS_ROM_BLOCK_NUM)
                                        
#if MAGPIE_FPGA_RAM_256K == 1
#define SYS_RAM_BLOCK_SIZE                  64*1024
#else                                       
#define SYS_RAM_BLOCK_SIZE                  40*1024
#endif

#define SYS_RAM_BLOCK_NUM               4
#define SYS_RAM_SZIE                    (SYS_RAM_BLOCK_SIZE*SYS_RAM_BLOCK_NUM)

/* instruction port area */
#define SYS_I_R0M_REGION_0_BASE         0x8e0000
                                        
#define SYS_I_RAM_REGION_0_BASE         0x900000
#define SYS_I_RAM_REGION_1_BASE         (SYS_I_RAM_REGION_0_BASE+SYS_RAM_BLOCK_SIZE)
#define SYS_I_RAM_REGION_2_BASE         (SYS_I_RAM_REGION_1_BASE+SYS_RAM_BLOCK_SIZE)
#define SYS_I_RAM_REGION_3_BASE         (SYS_I_RAM_REGION_2_BASE+SYS_RAM_BLOCK_SIZE)
                                        
/* data port area */                    
#define SYS_D_R0M_REGION_0_BASE         0x4e0000
                                        
#define SYS_D_RAM_REGION_0_BASE         0x500000
#define SYS_D_RAM_REGION_1_BASE         (SYS_D_RAM_REGION_0_BASE+SYS_RAM_BLOCK_SIZE)
#define SYS_D_RAM_REGION_2_BASE         (SYS_D_RAM_REGION_1_BASE+SYS_RAM_BLOCK_SIZE)
#define SYS_D_RAM_REGION_3_BASE         (SYS_D_RAM_REGION_2_BASE+SYS_RAM_BLOCK_SIZE)

/* data and bss section */

#define SYS_D_RAM_DATA_BSS              SYS_D_RAM_REGION_0_BASE
#define SYS_D_RAM_DATA_BSS_SZ           SYS_RAM_BLOCK_SIZE
#define SYS_D_RAM_STACK_SIZE                (2*1024)

/////////////////////////////////////////////////////////////////////////////////////
#define EEPROM_CTRL_BASE                    0x10ff0000
#define EEPROM_ADDR_BASE                    (EEPROM_CTRL_BASE+0x2000)

#define EEPROM_SIZE                         0xfff   // 4K addressing space, each has 2 bytes, (a half word)
#define EEPROM_START_OFFSET                 0       // THIS SHOULD NOT MODIFY
#define EEPROM_END_OFFSET                   (EEPROM_START_OFFSET+EEPROM_SIZE)   // end of the eeprom offset

/////////////////////////////////////////////////////////////////////////////////////
#define EEPROM_USB_DESCRIPTOR_ADDR          ((uint32_t)&_bss_end)  // address at RAM to put descriptor data
#define USB_DESC_START_ADDR                 0x780
#define USB_DESCRIPTOR_ADDR                 USB_DESC_START_ADDR     // eeprom offset to sotre the descriptor data

#define USB_DESC_IN_EEPROM_SIZE             2                       // indicate eeprom is exist in eeprom
#define USB_DEVICE_DESCRIPTOR_SIZE          16                      // Device Descriptor
#define USB_STRING00_DESCRIPTOR_SIZE        6                       // 16 half word
#define USB_STRING10_DESCRIPTOR_SIZE        12                      // Manufacture data
#define USB_STRING20_DESCRIPTOR_SIZE        16                      // Product/Company data
#define USB_STRING30_DESCRIPTOR_SIZE        8                       // Serial Number

#define USB_DEVICE_PID_SIZE                 1                       // PID SIZE, 1 halfword offset
#define USB_DEVICE_VID_SIZE                 1                       // VID SIZE, 1 halfword offset
    
#define USB_DESC_IN_EEPROM_FLAG_OFFSET      USB_DESCRIPTOR_ADDR
#define USB_DEVICE_DESCRIPTOR_OFFSET        (USB_DESC_IN_EEPROM_FLAG_OFFSET+USB_DESC_IN_EEPROM_SIZE)
#define USB_STRING00_DESCRIPTOR_OFFSET      (USB_DEVICE_DESCRIPTOR_OFFSET+USB_DEVICE_DESCRIPTOR_SIZE)
#define USB_STRING10_DESCRIPTOR_OFFSET      (USB_STRING00_DESCRIPTOR_OFFSET+USB_STRING00_DESCRIPTOR_SIZE)
#define USB_STRING20_DESCRIPTOR_OFFSET      (USB_STRING10_DESCRIPTOR_OFFSET+USB_STRING10_DESCRIPTOR_SIZE)
#define USB_STRING30_DESCRIPTOR_OFFSET      (USB_STRING20_DESCRIPTOR_OFFSET+USB_STRING20_DESCRIPTOR_SIZE)

#define USB_DEVICE_VID_OFFSET               (USB_DEVICE_DESCRIPTOR_OFFSET+4)
#define USB_DEVICE_PID_OFFSET               (USB_DEVICE_VID_OFFSET+USB_DEVICE_VID_SIZE)

#define USB_DESC_IN_EEPROM_FLAG_ADDR        EEPROM_USB_DESCRIPTOR_ADDR
#define USB_DEVICE_DESCRIPTOR_ADDR          (USB_DESC_IN_EEPROM_FLAG_ADDR+(USB_DESC_IN_EEPROM_SIZE*2))
#define USB_STRING00_DESCRIPTOR_ADDR        (USB_DEVICE_DESCRIPTOR_ADDR+(USB_DEVICE_DESCRIPTOR_SIZE*2))
#define USB_STRING10_DESCRIPTOR_ADDR        (USB_STRING00_DESCRIPTOR_ADDR+(USB_STRING00_DESCRIPTOR_SIZE*2))
#define USB_STRING20_DESCRIPTOR_ADDR        (USB_STRING10_DESCRIPTOR_ADDR+(USB_STRING10_DESCRIPTOR_SIZE*2))
#define USB_STRING30_DESCRIPTOR_ADDR        (USB_STRING20_DESCRIPTOR_ADDR+(USB_STRING20_DESCRIPTOR_SIZE*2))

#define USB_DEVICE_VID_ADDR                 (USB_DEVICE_DESCRIPTOR_ADDR+4)
#define USB_DEVICE_PID_ADDR                 (USB_DEVICE_VID_ADDR+USB_DEVICE_VID_SIZE)

#define USB_DESC_IN_EEP_PATTERN             0x41544852  //ATHR

/****************************** patch in eeprom *****************************************/
#define ROM_PATCH_EEPROM_SIZE			2 			// 4 bytes

#define ROM_PATCH_EEPROM_OFFSET         0xfc
#define ROM_PATCH_BUF_ADDR              SYS_D_RAM_REGION_3_BASE

#endif /* _MEM_ADDRS_H_ */
