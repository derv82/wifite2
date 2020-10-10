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
#ifndef USB_DEFS_H
#define USB_DEFS_H

#include "usb_table.h"
#include "dt_defs.h"
#include "reg_defs.h"

#define CHECK_SWITCH_BY_BOOTCODE         1   //to be verified for ZD1215, OK for ZD1211
#define VERIFY_CHECKSUM_BY_BOOTCODE      1

/***********************************************************************/
/*  for SEEPROM  Boot                                                  */
/***********************************************************************/
#define WLAN_BOOT_SIGNATURE         (0x19710303)

#define WLAN_SIGNATURE_ADDR         (0x102000)

#define cMAX_ADDR               	0x10000

#define cEEPROM_SIZE            	0x800       // 2k word (4k byte)

#define cRESERVE_LOAD_SPACE     	0

// start addr. of boot code
#define cBOOT_CODE_ADDR         	(cMAX_ADDR - cEEPROM_SIZE)  // 0xF800

/************************** Register Addr Process *********************/
#define mpADDR(addr)            				((volatile uint16_t*) (addr))
#define mADDR(addr)             				(*mpADDR(addr))
#define muADDR(addr)            				((uint16_t) (&(addr)))

#define USB_BYTE_REG_WRITE(addr, val)		iowrite8_usb(addr, val)
#define USB_BYTE_REG_READ(addr)			ioread8_usb(addr)

#define USB_HALF_WORD_REG_WRITE(addr, val)	iowrite16_usb(addr, val)
#define USB_HALF_WORD_REG_READ(addr)		ioread16_usb(addr)

#define USB_WORD_REG_WRITE(addr, val)		iowrite32_usb(addr, val)
#define USB_WORD_REG_READ(addr)			ioread32_usb(addr)


/************************** Register Deinition ***************************/
//#define USB_BASE_ADDR_SOC                0x8000

//#define SOC_Reg                          mpADDR(USB_BASE_ADDR_SOC)

#define cSOC_USB_OFST                    (0x100)

#define ZM_CBUS_FIFO_SIZE_OFFSET    (cSOC_USB_OFST)     //OFFSET 0

#define cSOC_CBUS_CTL_OFFSET             0xF0

#define ZM_FUSB_BASE                     USB_CTRL_BASE_ADDRESS

#define ZM_MAIN_CTRL_OFFSET              0x00
#define ZM_DEVICE_ADDRESS_OFFSET         0x01
#define ZM_TEST_OFFSET                   0x02
#define ZM_PHY_TEST_SELECT_OFFSET        0x08
#define ZM_VDR_SPECIFIC_MODE_OFFSET       0x0A
#define ZM_CX_CONFIG_STATUS_OFFSET       0x0B
#define ZM_EP0_DATA1_OFFSET              0x0C
#define ZM_EP0_DATA2_OFFSET              0x0D
#define ZM_EP0_DATA_OFFSET               0x0C

#define ZM_INTR_MASK_BYTE_0_OFFSET       0x11
#define ZM_INTR_MASK_BYTE_1_OFFSET       0x12
#define ZM_INTR_MASK_BYTE_2_OFFSET       0x13
#define ZM_INTR_MASK_BYTE_3_OFFSET       0x14
#define ZM_INTR_MASK_BYTE_4_OFFSET       0x15
#define ZM_INTR_MASK_BYTE_5_OFFSET       0x16
#define ZM_INTR_MASK_BYTE_6_OFFSET       0x17
#define ZM_INTR_MASK_BYTE_7_OFFSET       0x18

#define ZM_INTR_GROUP_OFFSET             0x20
#define ZM_INTR_SOURCE_0_OFFSET          0x21
#define ZM_INTR_SOURCE_1_OFFSET          0x22
#define ZM_INTR_SOURCE_2_OFFSET          0x23
#define ZM_INTR_SOURCE_3_OFFSET          0x24
#define ZM_INTR_SOURCE_4_OFFSET          0x25
#define ZM_INTR_SOURCE_5_OFFSET          0x26
#define ZM_INTR_SOURCE_6_OFFSET          0x27
#define ZM_INTR_SOURCE_7_OFFSET          0x28

#define ZM_EP_IN_MAX_SIZE_HIGH_OFFSET    0x3F
#define ZM_EP_IN_MAX_SIZE_LOW_OFFSET     0x3E

#define ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET   0x5F
#define ZM_EP_OUT_MAX_SIZE_LOW_OFFSET    0x5E

#define ZM_EP3_BYTE_COUNT_HIGH_OFFSET    0xAE
#define ZM_EP3_BYTE_COUNT_LOW_OFFSET     0xBE
#define ZM_EP4_BYTE_COUNT_HIGH_OFFSET    0xAF
#define ZM_EP4_BYTE_COUNT_LOW_OFFSET     0xBF

#define ZM_EP3_DATA_OFFSET               0xF8
#define ZM_EP4_DATA_OFFSET               0xFC

#define ZM_SOC_USB_MODE_CTRL_OFFSET      0x108
#define ZM_SOC_USB_MAX_AGGREGATE_OFFSET  0x110
#define ZM_SOC_USB_TIME_CTRL_OFFSET      0x114
#define ZM_SOC_USB_DMA_RESET_OFFSET      0x118

#define ZM_ADDR_CONV                     0x0

#define ZM_CBUS_FIFO_SIZE_REG			(ZM_CBUS_FIFO_SIZE_OFFSET^ZM_ADDR_CONV)
                                		
#define ZM_CBUS_CTRL_REG				(cSOC_USB_OFST+cSOC_CBUS_CTL_OFFSET^ZM_ADDR_CONV)

#define ZM_MAIN_CTRL_REG				(ZM_MAIN_CTRL_OFFSET^ZM_ADDR_CONV)

#define ZM_DEVICE_ADDRESS_REG			(ZM_DEVICE_ADDRESS_OFFSET^ZM_ADDR_CONV)

#define ZM_TEST_REG						(ZM_TEST_OFFSET^ZM_ADDR_CONV)

#define ZM_PHY_TEST_SELECT_REG     		(ZM_PHY_TEST_SELECT_OFFSET^ZM_ADDR_CONV)))

#define ZM_CX_CONFIG_STATUS_REG			(ZM_CX_CONFIG_STATUS_OFFSET^ZM_ADDR_CONV)

#define ZM_EP0_DATA1_REG				(ZM_EP0_DATA1_OFFSET^ZM_ADDR_CONV)))

#define ZM_EP0_DATA2_REG				(ZM_EP0_DATA2_OFFSET^ZM_ADDR_CONV)

#define ZM_EP0_DATA_REG					(ZM_EP0_DATA_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_0_REG			(ZM_INTR_MASK_BYTE_0_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_1_REG			(ZM_INTR_MASK_BYTE_1_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_2_REG			(ZM_INTR_MASK_BYTE_2_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_3_REG			(ZM_INTR_MASK_BYTE_3_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_4_REG			(ZM_INTR_MASK_BYTE_4_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_5_REG			(ZM_INTR_MASK_BYTE_5_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_6_REG			(ZM_INTR_MASK_BYTE_6_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_MASK_BYTE_7_REG			(ZM_INTR_MASK_BYTE_7_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_0_REG			(ZM_INTR_SOURCE_0_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_1_REG			(ZM_INTR_SOURCE_1_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_2_REG			(ZM_INTR_SOURCE_2_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_3_REG			(ZM_INTR_SOURCE_3_OFFSET^ZM_ADDR_CONV)
    
#define ZM_INTR_SOURCE_4_REG			(ZM_INTR_SOURCE_4_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_5_REG			(ZM_INTR_SOURCE_5_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_6_REG			(ZM_INTR_SOURCE_6_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_SOURCE_7_REG 			(ZM_INTR_SOURCE_7_OFFSET^ZM_ADDR_CONV)

#define ZM_INTR_GROUP_REG				(ZM_INTR_GROUP_OFFSET^ZM_ADDR_CONV)))

#define ZM_EP3_BYTE_COUNT_HIGH_REG		(ZM_EP3_BYTE_COUNT_HIGH_OFFSET^ZM_ADDR_CONV)

#define ZM_EP3_BYTE_COUNT_LOW_REG		(ZM_EP3_BYTE_COUNT_LOW_OFFSET^ZM_ADDR_CONV)

#define ZM_EP4_BYTE_COUNT_HIGH_REG		(ZM_EP4_BYTE_COUNT_HIGH_OFFSET^ZM_ADDR_CONV)

#define ZM_EP4_BYTE_COUNT_LOW_REG		(ZM_EP4_BYTE_COUNT_LOW_OFFSET^ZM_ADDR_CONV)

#define ZM_EP3_DATA_REG					(ZM_EP3_DATA_OFFSET)

#define ZM_EP4_DATA_REG					(ZM_EP4_DATA_OFFSET)

#define ZM_SOC_USB_MODE_CTRL_REG		(ZM_SOC_USB_MODE_CTRL_OFFSET)

#define ZM_SOC_USB_MAX_AGGREGATE_REG	(ZM_SOC_USB_MAX_AGGREGATE_OFFSET)

#define ZM_SOC_USB_TIME_CTRL_REG		(ZM_SOC_USB_TIME_CTRL_OFFSET)

#define bmHIGH_SPEED                	BIT6
#define bmCWR_BUF_END               	BIT1

#define mUsbEP0DataRd1()            	(USB_BYTE_REG_READ(ZM_EP0_DATA1_OFFSET))
//#define mUsbEP0DataRd2()            	ZM_EP0_DATA2_REG
//#define mUsbEP0DataRd3()            	ZM_EP0_DATA3_REG
//#define mUsbEP0DataRd4()            	ZM_EP0_DATA4_REG
#define mUsbEP0DataWr1(data)        	(USB_BYTE_REG_WRITE(ZM_EP0_DATA1_OFFSET, data))
#define mUsbEP0DataWr2(data)        	(USB_BYTE_REG_WRITE(ZM_EP0_DATA2_OFFSET, data))

#define mGetByte0(data)             	( data & 0xff )
#define mGetByte1(data)             	( (data >> 8) & 0xff )
#define mGetByte2(data)             	( (data >> 16) & 0xff )
#define mGetByte3(data)             	( (data >> 24) & 0xff )

//#define mUsbHighSpeedST()           	(ZM_MAIN_CTRL_REG & BIT6)
//#define mUsbCfgST()                 	(ZM_DEVICE_ADDRESS_REG & BIT7)
//#define mUsbApWrEnd()               	(ZM_CBUS_CTRL_REG = bmCWR_BUF_END)
//#define mUsbApRdEnd()               	(ZM_CBUS_CTRL_REG = bmCWR_BUF_END)

#define mUsbHighSpeedST()           	(USB_BYTE_REG_READ(ZM_MAIN_CTRL_OFFSET) & BIT6)
#define mUsbCfgST()                 	(USB_BYTE_REG_READ(ZM_DEVICE_ADDRESS_OFFSET) & BIT7)
#define mUsbApWrEnd()               	(USB_BYTE_REG_WRITE((cSOC_USB_OFST+cSOC_CBUS_CTL_OFFSET), bmCWR_BUF_END)
#define mUsbApRdEnd()               	(USB_BYTE_REG_WRITE((cSOC_USB_OFST+cSOC_CBUS_CTL_OFFSET), bmCWR_BUF_END)

#define mUsbRmWkupST()              	USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, \
											USB_BYTE_REG_READ(ZM_MAIN_CTRL_OFFSET)&BIT0)
#define mUsbRmWkupClr()             	USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, \
											USB_BYTE_REG_READ(ZM_MAIN_CTRL_OFFSET)&~BIT0)
#define mUsbRmWkupSet()             	USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, \
											USB_BYTE_REG_READ(ZM_MAIN_CTRL_OFFSET)|BIT0)
                                    	                                         
#define mUsbGlobIntEnable()         	USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, \
											USB_BYTE_REG_READ(ZM_MAIN_CTRL_OFFSET)|BIT2)

#define mUSB_REG_OUT_INT_ENABLE()    	USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_4_OFFSET, \
											USB_BYTE_REG_READ(ZM_INTR_MASK_BYTE_4_OFFSET)&0x3f)
#define mUSB_REG_OUT_INT_DISABLE()   	USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_4_OFFSET, \
											USB_BYTE_REG_READ(ZM_INTR_MASK_BYTE_4_OFFSET)|0xc0)
#define mUSB_STATUS_IN_INT_ENABLE()  	USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_6_OFFSET, \
											USB_BYTE_REG_READ(ZM_INTR_MASK_BYTE_6_OFFSET)&0xbf)
#define mUSB_STATUS_IN_INT_DISABLE() 	USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_6_OFFSET, \
											USB_BYTE_REG_READ(ZM_INTR_MASK_BYTE_6_OFFSET)|0xc0)
//											USB_BYTE_REG_READ(ZM_INTR_MASK_BYTE_6_OFFSET)|0x40)

#define mUSB_EP3_XFER_DONE()         	USB_BYTE_REG_WRITE(ZM_EP3_BYTE_COUNT_HIGH_OFFSET, \
											USB_BYTE_REG_READ(ZM_EP3_BYTE_COUNT_HIGH_OFFSET)|0x08)



#define HS_C1_I0_A0_EP1_MAX_PACKET		MX_PA_SZ_512
#define HS_C1_I0_A0_EP1_bInterval       00

#define HS_C1_I0_A0_EP_NUMBER           0x06
#define HS_C1_I0_A0_EP_LENGTH           (EP_LENGTH * HS_C1_I0_A0_EP_NUMBER)
#define HS_C1_I0_ALT_LENGTH             (HS_C1_I0_A0_EP_LENGTH)
#define HS_C1_INTERFACE_LENGTH          (HS_C1_I0_ALT_LENGTH)

#define HS_C1_CONFIG_TOTAL_LENGTH       (CONFIG_LENGTH + INTERFACE_LENGTH +  HS_C1_INTERFACE_LENGTH)
#define FS_C1_CONFIG_TOTAL_LENGTH       (CONFIG_LENGTH + INTERFACE_LENGTH +  FS_C1_INTERFACE_LENGTH)

#define FS_C1_I0_A0_EP1_MAX_PACKET      MX_PA_SZ_64
//#define FS_C1_I0_A0_EP1_bInterval       HS_C1_I0_A0_EP1_bInterval

#define HS_CONFIGURATION_NUMBER         1
#define FS_CONFIGURATION_NUMBER         1

#define fDOUBLE_BUF                     1
#define fDOUBLE_BUF_IN                  1

#define fFLASH_DISK                     0
#define fENABLE_ISO                     0

#if (HS_CONFIGURATION_NUMBER >= 1)
    // Configuration 0X01
    #define HS_C1_INTERFACE_NUMBER  	0x01
    #define HS_C1                   	0x01
    #define HS_C1_iConfiguration    	0x00
    #define HS_C1_bmAttribute       	0x80
    #if !(fFLASH_DISK && !fFLASH_BOOT)
    #define HS_C1_iMaxPower         	0xFA
    #else
    #define HS_C1_iMaxPower         	0x32
    #endif

    #if (HS_C1_INTERFACE_NUMBER >= 1)
        // Interface 0
        #define HS_C1_I0_ALT_NUMBER    	0X01
        #if (HS_C1_I0_ALT_NUMBER >= 1) 
            // AlternateSetting 0X00
            #define HS_C1_I0_A0_bInterfaceNumber   0X00
            #define HS_C1_I0_A0_bAlternateSetting  0X00
        //JWEI 2003/07/14
            //#if fINDEPEND_REG_RW && !(fFLASH_DISK && !fFLASH_BOOT)
            #define HS_C1_I0_A0_EP_NUMBER          0x06
            //#else
            //#define HS_C1_I0_A0_EP_NUMBER          0X03
            //#endif
            #if !(fFLASH_DISK && !fFLASH_BOOT)
            #define HS_C1_I0_A0_bInterfaceClass    0XFF
            #define HS_C1_I0_A0_bInterfaceSubClass 0X00
            #define HS_C1_I0_A0_bInterfaceProtocol 0X00
            #else
            #define HS_C1_I0_A0_bInterfaceClass    0X08
            #define HS_C1_I0_A0_bInterfaceSubClass 0X06
            #define HS_C1_I0_A0_bInterfaceProtocol 0X50
            #endif
            #define HS_C1_I0_A0_iInterface         0X00

            #if (HS_C1_I0_A0_EP_NUMBER >= 1)
                //EP0X01
                #define HS_C1_I0_A0_EP1_BLKSIZE    BLK512BYTE
            //JWEI 2003/05/19
                #if fDOUBLE_BUF
                #define HS_C1_I0_A0_EP1_BLKNO      DOUBLE_BLK
                #else
                #define HS_C1_I0_A0_EP1_BLKNO      SINGLE_BLK
                #endif
                #define HS_C1_I0_A0_EP1_DIRECTION  DIRECTION_OUT
                #define HS_C1_I0_A0_EP1_TYPE       TF_TYPE_BULK
            //JWEI 2003/05/07
                #define HS_C1_I0_A0_EP1_MAX_PACKET MX_PA_SZ_512
                #define HS_C1_I0_A0_EP1_bInterval  00
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 2)
                //EP0X02
                #define HS_C1_I0_A0_EP2_BLKSIZE    BLK512BYTE
            //JWEI 2003/08/20
                #if fDOUBLE_BUF_IN
                #define HS_C1_I0_A0_EP2_BLKNO      DOUBLE_BLK
                #else
                #define HS_C1_I0_A0_EP2_BLKNO      SINGLE_BLK
                #endif
                #define HS_C1_I0_A0_EP2_DIRECTION  DIRECTION_IN
                #define HS_C1_I0_A0_EP2_TYPE       TF_TYPE_BULK
                #define HS_C1_I0_A0_EP2_MAX_PACKET MX_PA_SZ_512
                #define HS_C1_I0_A0_EP2_bInterval  00
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 3)
                //EP0X03
                #define HS_C1_I0_A0_EP3_BLKSIZE    BLK64BYTE
                #define HS_C1_I0_A0_EP3_BLKNO      SINGLE_BLK
                #define HS_C1_I0_A0_EP3_DIRECTION  DIRECTION_IN
                #define HS_C1_I0_A0_EP3_TYPE       TF_TYPE_INTERRUPT
                #define HS_C1_I0_A0_EP3_MAX_PACKET 0x0040
                #define HS_C1_I0_A0_EP3_bInterval  01
            #endif
        // Note: HS Bulk type require max pkt size = 512
        //       ==> must use Interrupt type for max pkt size = 64
            #if (HS_C1_I0_A0_EP_NUMBER >= 4) || fFLASH_DISK
                //EP0X04
                #define HS_C1_I0_A0_EP4_BLKSIZE    BLK64BYTE
                #define HS_C1_I0_A0_EP4_BLKNO      SINGLE_BLK
                #define HS_C1_I0_A0_EP4_DIRECTION  DIRECTION_OUT
                #define HS_C1_I0_A0_EP4_TYPE       TF_TYPE_INTERRUPT
                #define HS_C1_I0_A0_EP4_MAX_PACKET 0x0040
                #define HS_C1_I0_A0_EP4_bInterval  01
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 5)
                //EP0X04
                #define HS_C1_I0_A0_EP5_BLKSIZE    BLK512BYTE
                #if fDOUBLE_BUF
                #define HS_C1_I0_A0_EP5_BLKNO      DOUBLE_BLK
                #else
                #define HS_C1_I0_A0_EP5_BLKNO      SINGLE_BLK
                #endif
                #define HS_C1_I0_A0_EP5_DIRECTION  DIRECTION_OUT
                #define HS_C1_I0_A0_EP5_TYPE       TF_TYPE_BULK
                #define HS_C1_I0_A0_EP5_MAX_PACKET MX_PA_SZ_512
                #define HS_C1_I0_A0_EP5_bInterval  00
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 6)
                //EP0X04
                #define HS_C1_I0_A0_EP6_BLKSIZE    BLK512BYTE
                #if fDOUBLE_BUF
                #define HS_C1_I0_A0_EP6_BLKNO      DOUBLE_BLK
                #else
                #define HS_C1_I0_A0_EP6_BLKNO      SINGLE_BLK
                #endif
                #define HS_C1_I0_A0_EP6_DIRECTION  DIRECTION_OUT
                #define HS_C1_I0_A0_EP6_TYPE       TF_TYPE_BULK
                #define HS_C1_I0_A0_EP6_MAX_PACKET MX_PA_SZ_512
                #define HS_C1_I0_A0_EP6_bInterval  00
            #endif
        #endif
    #endif
#endif

#if (HS_CONFIGURATION_NUMBER >= 1)
    // Configuration 1
    #if (HS_C1_INTERFACE_NUMBER >= 1)
        // Interface 0
        #if (HS_C1_I0_ALT_NUMBER >= 1)
            // AlternateSetting 0
            #define HS_C1_I0_A0_EP_LENGTH           (EP_LENGTH * HS_C1_I0_A0_EP_NUMBER)
            #if (HS_C1_I0_A0_EP_NUMBER >= 1)
                // EP1
                #define HS_C1_I0_A0_EP1_FIFO_START  FIFO0
                #define HS_C1_I0_A0_EP1_FIFO_NO     (HS_C1_I0_A0_EP1_BLKNO * HS_C1_I0_A0_EP1_BLKSIZE)
                #define HS_C1_I0_A0_EP1_FIFO_CONFIG (0x80 | ((HS_C1_I0_A0_EP1_BLKSIZE - 1) << 4) | ((HS_C1_I0_A0_EP1_BLKNO - 1) << 2) | HS_C1_I0_A0_EP1_TYPE)
                #define HS_C1_I0_A0_EP1_FIFO_MAP    (((1 - HS_C1_I0_A0_EP1_DIRECTION) << 4) | EP1)
                #define HS_C1_I0_A0_EP1_MAP         (HS_C1_I0_A0_EP1_FIFO_START |   (HS_C1_I0_A0_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A0_EP1_DIRECTION)))
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 2)
                // EP2
                #if fDOUBLE_BUF
                #define HS_C1_I0_A0_EP2_FIFO_START  (HS_C1_I0_A0_EP1_FIFO_START + HS_C1_I0_A0_EP1_FIFO_NO)
                #else
                #define HS_C1_I0_A0_EP2_FIFO_START  FIFO2
                #endif
                #define HS_C1_I0_A0_EP2_FIFO_NO     (HS_C1_I0_A0_EP2_BLKNO * HS_C1_I0_A0_EP2_BLKSIZE)
                #define HS_C1_I0_A0_EP2_FIFO_CONFIG (0x80 | ((HS_C1_I0_A0_EP2_BLKSIZE - 1) << 4) | ((HS_C1_I0_A0_EP2_BLKNO - 1) << 2) | HS_C1_I0_A0_EP2_TYPE)
                #define HS_C1_I0_A0_EP2_FIFO_MAP    (((1 - HS_C1_I0_A0_EP2_DIRECTION) << 4) | EP2)
                #define HS_C1_I0_A0_EP2_MAP         (HS_C1_I0_A0_EP2_FIFO_START |   (HS_C1_I0_A0_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A0_EP2_DIRECTION)))
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 3)
                // EP3
            //JWEI 2003/07/15
            //    #define HS_C1_I0_A0_EP3_FIFO_START  (HS_C1_I0_A0_EP2_FIFO_START + HS_C1_I0_A0_EP2_FIFO_NO)
                #define HS_C1_I0_A0_EP3_FIFO_START  FIFO14
                #define HS_C1_I0_A0_EP3_FIFO_NO     (HS_C1_I0_A0_EP3_BLKNO * HS_C1_I0_A0_EP3_BLKSIZE)
                #define HS_C1_I0_A0_EP3_FIFO_CONFIG (0x80 | ((HS_C1_I0_A0_EP3_BLKSIZE - 1) << 4) | ((HS_C1_I0_A0_EP3_BLKNO - 1) << 2) | HS_C1_I0_A0_EP3_TYPE)
                #define HS_C1_I0_A0_EP3_FIFO_MAP    (((1 - HS_C1_I0_A0_EP3_DIRECTION) << 4) | EP3)
                #define HS_C1_I0_A0_EP3_MAP         (HS_C1_I0_A0_EP3_FIFO_START |   (HS_C1_I0_A0_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A0_EP3_DIRECTION)))
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 4) || fFLASH_DISK
                // EP4
                #define HS_C1_I0_A0_EP4_FIFO_START  (HS_C1_I0_A0_EP3_FIFO_START + HS_C1_I0_A0_EP3_FIFO_NO)
                #define HS_C1_I0_A0_EP4_FIFO_NO     (HS_C1_I0_A0_EP4_BLKNO * HS_C1_I0_A0_EP4_BLKSIZE)
                #define HS_C1_I0_A0_EP4_FIFO_CONFIG (0x80 | ((HS_C1_I0_A0_EP4_BLKSIZE - 1) << 4) | ((HS_C1_I0_A0_EP4_BLKNO - 1) << 2) | HS_C1_I0_A0_EP4_TYPE)
                #define HS_C1_I0_A0_EP4_FIFO_MAP    (((1 - HS_C1_I0_A0_EP4_DIRECTION) << 4) | EP4)
                #define HS_C1_I0_A0_EP4_MAP         (HS_C1_I0_A0_EP4_FIFO_START |   (HS_C1_I0_A0_EP4_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A0_EP4_DIRECTION)))
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 5)
                // EP5
                #define HS_C1_I0_A0_EP5_FIFO_START  (HS_C1_I0_A0_EP2_FIFO_START + HS_C1_I0_A0_EP2_FIFO_NO)
                #define HS_C1_I0_A0_EP5_FIFO_NO     (HS_C1_I0_A0_EP5_BLKNO * HS_C1_I0_A0_EP5_BLKSIZE)
                #define HS_C1_I0_A0_EP5_FIFO_CONFIG (0x80 | ((HS_C1_I0_A0_EP5_BLKSIZE - 1) << 4) | ((HS_C1_I0_A0_EP5_BLKNO - 1) << 2) | HS_C1_I0_A0_EP5_TYPE)
                #define HS_C1_I0_A0_EP5_FIFO_MAP    (((1 - HS_C1_I0_A0_EP5_DIRECTION) << 4) | EP5)
                #define HS_C1_I0_A0_EP5_MAP         (HS_C1_I0_A0_EP5_FIFO_START |   (HS_C1_I0_A0_EP5_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A0_EP5_DIRECTION)))
            #endif
            #if (HS_C1_I0_A0_EP_NUMBER >= 6)
                // EP5
                #define HS_C1_I0_A0_EP6_FIFO_START  (HS_C1_I0_A0_EP5_FIFO_START + HS_C1_I0_A0_EP5_FIFO_NO)
                #define HS_C1_I0_A0_EP6_FIFO_NO     (HS_C1_I0_A0_EP6_BLKNO * HS_C1_I0_A0_EP6_BLKSIZE)
                #define HS_C1_I0_A0_EP6_FIFO_CONFIG (0x80 | ((HS_C1_I0_A0_EP6_BLKSIZE - 1) << 4) | ((HS_C1_I0_A0_EP6_BLKNO - 1) << 2) | HS_C1_I0_A0_EP6_TYPE)
                #define HS_C1_I0_A0_EP6_FIFO_MAP    (((1 - HS_C1_I0_A0_EP6_DIRECTION) << 4) | EP6)
                #define HS_C1_I0_A0_EP6_MAP         (HS_C1_I0_A0_EP6_FIFO_START |   (HS_C1_I0_A0_EP6_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A0_EP6_DIRECTION)))
            #endif
        #endif

        #if (HS_C1_I0_ALT_NUMBER >= 2)
            // AlternateSetting 1
            #define HS_C1_I0_A1_EP_LENGTH           (EP_LENGTH * HS_C1_I0_A1_EP_NUMBER)
            #if (HS_C1_I0_A1_EP_NUMBER >= 1)
                // EP1
                #define HS_C1_I0_A1_EP1_FIFO_START  FIFO0
                #define HS_C1_I0_A1_EP1_FIFO_NO     (HS_C1_I0_A1_EP1_BLKNO * HS_C1_I0_A1_EP1_BLKSIZE)
                #define HS_C1_I0_A1_EP1_FIFO_CONFIG (0x80 | ((HS_C1_I0_A1_EP1_BLKSIZE - 1) << 4) | ((HS_C1_I0_A1_EP1_BLKNO - 1) << 2) | HS_C1_I0_A1_EP1_TYPE)
                #define HS_C1_I0_A1_EP1_FIFO_MAP    (((1 - HS_C1_I0_A1_EP1_DIRECTION) << 4) | EP1)
                #define HS_C1_I0_A1_EP1_MAP         (HS_C1_I0_A1_EP1_FIFO_START |   (HS_C1_I0_A1_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A1_EP1_DIRECTION)))
            #endif
            #if (HS_C1_I0_A1_EP_NUMBER >= 2)
                // EP2
                #define HS_C1_I0_A1_EP2_FIFO_START  (HS_C1_I0_A1_EP1_FIFO_START + HS_C1_I0_A1_EP1_FIFO_NO)
                #define HS_C1_I0_A1_EP2_FIFO_NO     (HS_C1_I0_A1_EP2_BLKNO * HS_C1_I0_A1_EP2_BLKSIZE)
                #define HS_C1_I0_A1_EP2_FIFO_CONFIG (0x80 | ((HS_C1_I0_A1_EP2_BLKSIZE - 1) << 4) | ((HS_C1_I0_A1_EP2_BLKNO - 1) << 2) | HS_C1_I0_A1_EP2_TYPE)
                #define HS_C1_I0_A1_EP2_FIFO_MAP    (((1 - HS_C1_I0_A1_EP2_DIRECTION) << 4) | EP2)
                #define HS_C1_I0_A1_EP2_MAP         (HS_C1_I0_A1_EP2_FIFO_START |   (HS_C1_I0_A1_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A1_EP2_DIRECTION)))
            #endif
            #if (HS_C1_I0_A1_EP_NUMBER >= 3)
                // EP3
                #define HS_C1_I0_A1_EP3_FIFO_START  (HS_C1_I0_A1_EP2_FIFO_START + HS_C1_I0_A1_EP2_FIFO_NO)
                #define HS_C1_I0_A1_EP3_FIFO_NO     (HS_C1_I0_A1_EP3_BLKNO * HS_C1_I0_A1_EP3_BLKSIZE)
                #define HS_C1_I0_A1_EP3_FIFO_CONFIG (0x80 | ((HS_C1_I0_A1_EP3_BLKSIZE - 1) << 4) | ((HS_C1_I0_A1_EP3_BLKNO - 1) << 2) | HS_C1_I0_A1_EP3_TYPE)
                #define HS_C1_I0_A1_EP3_FIFO_MAP    (((1 - HS_C1_I0_A1_EP3_DIRECTION) << 4) | EP3)
                #define HS_C1_I0_A1_EP3_MAP         (HS_C1_I0_A1_EP3_FIFO_START |   (HS_C1_I0_A1_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I0_A1_EP3_DIRECTION)))
            #endif
        #endif

        #if (HS_C1_I0_ALT_NUMBER == 1)
            #define HS_C1_I0_ALT_LENGTH             (HS_C1_I0_A0_EP_LENGTH)
        #elif (HS_C1_I0_ALT_NUMBER == 2)
            #define HS_C1_I0_ALT_LENGTH             (HS_C1_I0_A0_EP_LENGTH + HS_C1_I0_A1_EP_LENGTH)
        #endif
    #endif

    #if (HS_C1_INTERFACE_NUMBER >= 2)
        // Interface 1
        #if (HS_C1_I1_ALT_NUMBER >= 1)
            // AlternateSetting 0
            #define HS_C1_I1_A0_EP_LENGTH           (EP_LENGTH * HS_C1_I1_A0_EP_NUMBER)
            #if (HS_C1_I1_A0_EP_NUMBER >= 1)
                // EP1
                #define HS_C1_I1_A0_EP1_FIFO_START  FIFO0
                #define HS_C1_I1_A0_EP1_FIFO_NO     (HS_C1_I1_A0_EP1_BLKNO * HS_C1_I1_A0_EP1_BLKSIZE)
                #define HS_C1_I1_A0_EP1_FIFO_CONFIG (0x80 | ((HS_C1_I1_A0_EP1_BLKSIZE - 1) << 4) | ((HS_C1_I1_A0_EP1_BLKNO - 1) << 2) | HS_C1_I1_A0_EP1_TYPE)
                #define HS_C1_I1_A0_EP1_FIFO_MAP    (((1 - HS_C1_I1_A0_EP1_DIRECTION) << 4) | EP1)
                #define HS_C1_I1_A0_EP1_MAP         (HS_C1_I1_A0_EP1_FIFO_START |   (HS_C1_I1_A0_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I1_A0_EP1_DIRECTION)))
            #endif
            #if (HS_C1_I1_A0_EP_NUMBER >= 2)
                // EP2
                #define HS_C1_I1_A0_EP2_FIFO_START  (HS_C1_I1_A0_EP1_FIFO_START + HS_C1_I1_A0_EP1_FIFO_NO)
                #define HS_C1_I1_A0_EP2_FIFO_NO     (HS_C1_I1_A0_EP2_BLKNO * HS_C1_I1_A0_EP2_BLKSIZE)
                #define HS_C1_I1_A0_EP2_FIFO_CONFIG (0x80 | ((HS_C1_I1_A0_EP2_BLKSIZE - 1) << 4) | ((HS_C1_I1_A0_EP2_BLKNO - 1) << 2) | HS_C1_I1_A0_EP2_TYPE)
                #define HS_C1_I1_A0_EP2_FIFO_MAP    (((1 - HS_C1_I1_A0_EP2_DIRECTION) << 4) | EP2)
                #define HS_C1_I1_A0_EP2_MAP         (HS_C1_I1_A0_EP2_FIFO_START |   (HS_C1_I1_A0_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I1_A0_EP2_DIRECTION)))
            #endif
            #if (HS_C1_I1_A0_EP_NUMBER >= 3)
                // EP3
                #define HS_C1_I1_A0_EP3_FIFO_START  (HS_C1_I1_A0_EP2_FIFO_START + HS_C1_I1_A0_EP2_FIFO_NO)
                #define HS_C1_I1_A0_EP3_FIFO_NO     (HS_C1_I1_A0_EP3_BLKNO * HS_C1_I1_A0_EP3_BLKSIZE)
                #define HS_C1_I1_A0_EP3_FIFO_CONFIG (0x80 | ((HS_C1_I1_A0_EP3_BLKSIZE - 1) << 4) | ((HS_C1_I1_A0_EP3_BLKNO - 1) << 2) | HS_C1_I1_A0_EP3_TYPE)
                #define HS_C1_I1_A0_EP3_FIFO_MAP    (((1 - HS_C1_I1_A0_EP3_DIRECTION) << 4) | EP3)
                #define HS_C1_I1_A0_EP3_MAP         (HS_C1_I1_A0_EP3_FIFO_START |   (HS_C1_I1_A0_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I1_A0_EP3_DIRECTION)))
            #endif
        #endif

        #if (HS_C1_I1_ALT_NUMBER >= 2)
            // AlternateSetting 1
            #define HS_C1_I1_A1_EP_LENGTH           (EP_LENGTH * HS_C1_I1_A1_EP_NUMBER)
            #if (HS_C1_I1_A1_EP_NUMBER >= 1)
                // EP1
                #define HS_C1_I1_A1_EP1_FIFO_START  FIFO0
                #define HS_C1_I1_A1_EP1_FIFO_NO     (HS_C1_I1_A1_EP1_BLKNO * HS_C1_I1_A1_EP1_BLKSIZE)
                #define HS_C1_I1_A1_EP1_FIFO_CONFIG (0x80 | ((HS_C1_I1_A1_EP1_BLKSIZE - 1) << 4) | ((HS_C1_I1_A1_EP1_BLKNO - 1) << 2) | HS_C1_I1_A1_EP1_TYPE)
                #define HS_C1_I1_A1_EP1_FIFO_MAP    (((1 - HS_C1_I1_A1_EP1_DIRECTION) << 4) | EP1)
                #define HS_C1_I1_A1_EP1_MAP         (HS_C1_I1_A1_EP1_FIFO_START |   (HS_C1_I1_A1_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I1_A1_EP1_DIRECTION)))
            #endif
            #if (HS_C1_I1_A1_EP_NUMBER >= 2)
                // EP2
                #define HS_C1_I1_A1_EP2_FIFO_START  (HS_C1_I1_A1_EP1_FIFO_START + HS_C1_I1_A1_EP1_FIFO_NO)
                #define HS_C1_I1_A1_EP2_FIFO_NO     (HS_C1_I1_A1_EP2_BLKNO * HS_C1_I1_A1_EP2_BLKSIZE)
                #define HS_C1_I1_A1_EP2_FIFO_CONFIG (0x80 | ((HS_C1_I1_A1_EP2_BLKSIZE - 1) << 4) | ((HS_C1_I1_A1_EP2_BLKNO - 1) << 2) | HS_C1_I1_A1_EP2_TYPE)
                #define HS_C1_I1_A1_EP2_FIFO_MAP    (((1 - HS_C1_I1_A1_EP2_DIRECTION) << 4) | EP2)
                #define HS_C1_I1_A1_EP2_MAP         (HS_C1_I1_A1_EP2_FIFO_START |   (HS_C1_I1_A1_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I1_A1_EP2_DIRECTION)))
            #endif
            #if (HS_C1_I1_A1_EP_NUMBER >= 3)
                // EP3
                #define HS_C1_I1_A1_EP3_FIFO_START  (HS_C1_I1_A1_EP2_FIFO_START + HS_C1_I1_A1_EP2_FIFO_NO)
                #define HS_C1_I1_A1_EP3_FIFO_NO     (HS_C1_I1_A1_EP3_BLKNO * HS_C1_I1_A1_EP3_BLKSIZE)
                #define HS_C1_I1_A1_EP3_FIFO_CONFIG (0x80 | ((HS_C1_I1_A1_EP3_BLKSIZE - 1) << 4) | ((HS_C1_I1_A1_EP3_BLKNO - 1) << 2) | HS_C1_I1_A1_EP3_TYPE)
                #define HS_C1_I1_A1_EP3_FIFO_MAP    (((1 - HS_C1_I1_A1_EP3_DIRECTION) << 4) | EP3)
                #define HS_C1_I1_A1_EP3_MAP         (HS_C1_I1_A1_EP3_FIFO_START |   (HS_C1_I1_A1_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*HS_C1_I1_A1_EP3_DIRECTION)))
            #endif
        #endif

        #if (HS_C1_I1_ALT_NUMBER == 1)
            #define HS_C1_I1_ALT_LENGTH             (HS_C1_I1_A0_EP_LENGTH)
        #elif (HS_C1_I1_ALT_NUMBER == 2)
            #define HS_C1_I1_ALT_LENGTH             (HS_C1_I1_A0_EP_LENGTH + HS_C1_I1_A1_EP_LENGTH)
        #endif
    #endif

    #if (HS_C1_INTERFACE_NUMBER == 1)
        #define HS_C1_INTERFACE_LENGTH              (HS_C1_I0_ALT_LENGTH)
    #elif (HS_C1_INTERFACE_NUMBER == 2)
        #define HS_C1_INTERFACE_LENGTH              (HS_C1_I0_ALT_LENGTH + HS_C1_I1_ALT_LENGTH)
    #endif
#endif

#if (FS_CONFIGURATION_NUMBER >= 1)
    // Configuration 0X01
    #define FS_C1_INTERFACE_NUMBER  0X01
    #define FS_C1                   0X01
    #define FS_C1_iConfiguration    0X00
    #define FS_C1_bmAttribute       0X80
    #define FS_C1_iMaxPower         0XFA

    #if (FS_C1_INTERFACE_NUMBER >= 1)
        // Interface 0
        #define FS_C1_I0_ALT_NUMBER    0X01
        #if (FS_C1_I0_ALT_NUMBER >= 1)
            // AlternateSetting 0X00
            #define FS_C1_I0_A0_bInterfaceNumber   0X00
            #define FS_C1_I0_A0_bAlternateSetting  0X00
        //JWEI 2003/07/14
            //#if fINDEPEND_REG_RW && !(fFLASH_DISK && !fFLASH_BOOT)
            #define FS_C1_I0_A0_EP_NUMBER          0x05
            //#else
            //#define FS_C1_I0_A0_EP_NUMBER          0X03
            //#endif
            #if !(fFLASH_DISK && !fFLASH_BOOT)
            #define FS_C1_I0_A0_bInterfaceClass    0XFF
            #define FS_C1_I0_A0_bInterfaceSubClass 0X00
            #define FS_C1_I0_A0_bInterfaceProtocol 0X00
            #else
            #define FS_C1_I0_A0_bInterfaceClass    0X08
            #define FS_C1_I0_A0_bInterfaceSubClass 0X06
            #define FS_C1_I0_A0_bInterfaceProtocol 0X50
            #endif
            #define FS_C1_I0_A0_iInterface         0X00

            #if (FS_C1_I0_A0_EP_NUMBER >= 1)
                //EP0X01
                #define FS_C1_I0_A0_EP1_BLKSIZE    BLK512BYTE
            //JWEI 2003/05/19
                #if fDOUBLE_BUF
                #define FS_C1_I0_A0_EP1_BLKNO      DOUBLE_BLK
                #else
                #define FS_C1_I0_A0_EP1_BLKNO      SINGLE_BLK
                #endif
                #define FS_C1_I0_A0_EP1_DIRECTION  DIRECTION_OUT
                #define FS_C1_I0_A0_EP1_TYPE       TF_TYPE_BULK
            //JWEI 2003/05/07
                #define FS_C1_I0_A0_EP1_MAX_PACKET MX_PA_SZ_64
                #define FS_C1_I0_A0_EP1_bInterval  00
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 2)
                //EP0X02
                #define FS_C1_I0_A0_EP2_BLKSIZE    BLK512BYTE
            //JWEI 2003/08/20
                #if fDOUBLE_BUF_IN
                #define FS_C1_I0_A0_EP2_BLKNO      DOUBLE_BLK
                #else
                #define FS_C1_I0_A0_EP2_BLKNO      SINGLE_BLK
                #endif
                #define FS_C1_I0_A0_EP2_DIRECTION  DIRECTION_IN
                #define FS_C1_I0_A0_EP2_TYPE       TF_TYPE_BULK
                #define FS_C1_I0_A0_EP2_MAX_PACKET MX_PA_SZ_64
                #define FS_C1_I0_A0_EP2_bInterval  00
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 3)
                //EP0X03
                #define FS_C1_I0_A0_EP3_BLKSIZE    BLK64BYTE
                #define FS_C1_I0_A0_EP3_BLKNO      SINGLE_BLK
                #define FS_C1_I0_A0_EP3_DIRECTION  DIRECTION_IN
                #define FS_C1_I0_A0_EP3_TYPE       TF_TYPE_INTERRUPT
                #define FS_C1_I0_A0_EP3_MAX_PACKET 0x0040
                #define FS_C1_I0_A0_EP3_bInterval  01
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 4) || fFLASH_DISK
                //EP0X04
                #define FS_C1_I0_A0_EP4_BLKSIZE    BLK64BYTE
                #define FS_C1_I0_A0_EP4_BLKNO      SINGLE_BLK
                #define FS_C1_I0_A0_EP4_DIRECTION  DIRECTION_OUT
                #define FS_C1_I0_A0_EP4_TYPE       TF_TYPE_BULK
                #define FS_C1_I0_A0_EP4_MAX_PACKET 0x0040
                #define FS_C1_I0_A0_EP4_bInterval  00
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 5)
                //EP0X04
                #define FS_C1_I0_A0_EP5_BLKSIZE    BLK512BYTE
                #if fDOUBLE_BUF_IN
                #define FS_C1_I0_A0_EP5_BLKNO      DOUBLE_BLK
                #else
                #define FS_C1_I0_A0_EP5_BLKNO      SINGLE_BLK
                #endif
                #define FS_C1_I0_A0_EP5_DIRECTION  DIRECTION_OUT
                #define FS_C1_I0_A0_EP5_TYPE       TF_TYPE_BULK
                #define FS_C1_I0_A0_EP5_MAX_PACKET 0x0040
                #define FS_C1_I0_A0_EP5_bInterval  00
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 6)
                //EP0X04
                #define FS_C1_I0_A0_EP6_BLKSIZE    BLK512BYTE
                #if fDOUBLE_BUF_IN
                #define FS_C1_I0_A0_EP6_BLKNO      DOUBLE_BLK
                #else
                #define FS_C1_I0_A0_EP6_BLKNO      SINGLE_BLK
                #endif
                #define FS_C1_I0_A0_EP6_DIRECTION  DIRECTION_OUT
                #define FS_C1_I0_A0_EP6_TYPE       TF_TYPE_BULK
                #define FS_C1_I0_A0_EP6_MAX_PACKET 0x0040
                #define FS_C1_I0_A0_EP6_bInterval  00
            #endif
        #endif
    #endif
#endif

#if (FS_CONFIGURATION_NUMBER >= 1)
    // Configuration 1
    #if (FS_C1_INTERFACE_NUMBER >= 1)
        // Interface 0
        #if (FS_C1_I0_ALT_NUMBER >= 1)
            // AlternateSetting 0
            #define FS_C1_I0_A0_EP_LENGTH           (EP_LENGTH * FS_C1_I0_A0_EP_NUMBER)
            #if (FS_C1_I0_A0_EP_NUMBER >= 1)
                // EP1
                #define FS_C1_I0_A0_EP1_FIFO_START  FIFO0
                #define FS_C1_I0_A0_EP1_FIFO_NO     (FS_C1_I0_A0_EP1_BLKNO * FS_C1_I0_A0_EP1_BLKSIZE)
                #define FS_C1_I0_A0_EP1_FIFO_CONFIG (0x80 | ((FS_C1_I0_A0_EP1_BLKSIZE - 1) << 4) | ((FS_C1_I0_A0_EP1_BLKNO - 1) << 2) | FS_C1_I0_A0_EP1_TYPE)
                #define FS_C1_I0_A0_EP1_FIFO_MAP    (((1 - FS_C1_I0_A0_EP1_DIRECTION) << 4) | EP1)
                #define FS_C1_I0_A0_EP1_MAP         (FS_C1_I0_A0_EP1_FIFO_START |   (FS_C1_I0_A0_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A0_EP1_DIRECTION)))
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 2)
                // EP2
                #define FS_C1_I0_A0_EP2_FIFO_START  (FS_C1_I0_A0_EP1_FIFO_START + FS_C1_I0_A0_EP1_FIFO_NO)
                #define FS_C1_I0_A0_EP2_FIFO_NO     (FS_C1_I0_A0_EP2_BLKNO * FS_C1_I0_A0_EP2_BLKSIZE)
                #define FS_C1_I0_A0_EP2_FIFO_CONFIG (0x80 | ((FS_C1_I0_A0_EP2_BLKSIZE - 1) << 4) | ((FS_C1_I0_A0_EP2_BLKNO - 1) << 2) | FS_C1_I0_A0_EP2_TYPE)
                #define FS_C1_I0_A0_EP2_FIFO_MAP    (((1 - FS_C1_I0_A0_EP2_DIRECTION) << 4) | EP2)
                #define FS_C1_I0_A0_EP2_MAP         (FS_C1_I0_A0_EP2_FIFO_START |   (FS_C1_I0_A0_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A0_EP2_DIRECTION)))
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 3)
                // EP3
            //JWEI 2003/07/15
            //    #define FS_C1_I0_A0_EP3_FIFO_START  (FS_C1_I0_A0_EP2_FIFO_START + FS_C1_I0_A0_EP2_FIFO_NO)
                #define FS_C1_I0_A0_EP3_FIFO_START  FIFO14
                #define FS_C1_I0_A0_EP3_FIFO_NO     (FS_C1_I0_A0_EP3_BLKNO * FS_C1_I0_A0_EP3_BLKSIZE)
                #define FS_C1_I0_A0_EP3_FIFO_CONFIG (0x80 | ((FS_C1_I0_A0_EP3_BLKSIZE - 1) << 4) | ((FS_C1_I0_A0_EP3_BLKNO - 1) << 2) | FS_C1_I0_A0_EP3_TYPE)
                #define FS_C1_I0_A0_EP3_FIFO_MAP    (((1 - FS_C1_I0_A0_EP3_DIRECTION) << 4) | EP3)
                #define FS_C1_I0_A0_EP3_MAP         (FS_C1_I0_A0_EP3_FIFO_START |   (FS_C1_I0_A0_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A0_EP3_DIRECTION)))
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 4) || fFLASH_DISK
                // EP4
                #define FS_C1_I0_A0_EP4_FIFO_START  (FS_C1_I0_A0_EP3_FIFO_START + FS_C1_I0_A0_EP3_FIFO_NO)
                #define FS_C1_I0_A0_EP4_FIFO_NO     (FS_C1_I0_A0_EP4_BLKNO * FS_C1_I0_A0_EP4_BLKSIZE)
                #define FS_C1_I0_A0_EP4_FIFO_CONFIG (0x80 | ((FS_C1_I0_A0_EP4_BLKSIZE - 1) << 4) | ((FS_C1_I0_A0_EP4_BLKNO - 1) << 2) | FS_C1_I0_A0_EP4_TYPE)
                #define FS_C1_I0_A0_EP4_FIFO_MAP    (((1 - FS_C1_I0_A0_EP4_DIRECTION) << 4) | EP4)
                #define FS_C1_I0_A0_EP4_MAP         (FS_C1_I0_A0_EP4_FIFO_START |   (FS_C1_I0_A0_EP4_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A0_EP4_DIRECTION)))
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 5)
                // EP5
                #define FS_C1_I0_A0_EP5_FIFO_START  (FS_C1_I0_A0_EP2_FIFO_START + FS_C1_I0_A0_EP2_FIFO_NO)
                #define FS_C1_I0_A0_EP5_FIFO_NO     (FS_C1_I0_A0_EP5_BLKNO * FS_C1_I0_A0_EP5_BLKSIZE)
                #define FS_C1_I0_A0_EP5_FIFO_CONFIG (0x80 | ((FS_C1_I0_A0_EP5_BLKSIZE - 1) << 4) | ((FS_C1_I0_A0_EP5_BLKNO - 1) << 2) | FS_C1_I0_A0_EP5_TYPE)
                #define FS_C1_I0_A0_EP5_FIFO_MAP    (((1 - FS_C1_I0_A0_EP5_DIRECTION) << 4) | EP5)
                #define FS_C1_I0_A0_EP5_MAP         (FS_C1_I0_A0_EP5_FIFO_START |   (FS_C1_I0_A0_EP5_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A0_EP5_DIRECTION)))
            #endif
            #if (FS_C1_I0_A0_EP_NUMBER >= 6)
                // EP5
                #define FS_C1_I0_A0_EP6_FIFO_START  (FS_C1_I0_A0_EP5_FIFO_START + FS_C1_I0_A0_EP5_FIFO_NO)
                #define FS_C1_I0_A0_EP6_FIFO_NO     (FS_C1_I0_A0_EP6_BLKNO * FS_C1_I0_A0_EP6_BLKSIZE)
                #define FS_C1_I0_A0_EP6_FIFO_CONFIG (0x80 | ((FS_C1_I0_A0_EP6_BLKSIZE - 1) << 4) | ((FS_C1_I0_A0_EP6_BLKNO - 1) << 2) | FS_C1_I0_A0_EP6_TYPE)
                #define FS_C1_I0_A0_EP6_FIFO_MAP    (((1 - FS_C1_I0_A0_EP6_DIRECTION) << 4) | EP6)
                #define FS_C1_I0_A0_EP6_MAP         (FS_C1_I0_A0_EP6_FIFO_START |   (FS_C1_I0_A0_EP6_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A0_EP6_DIRECTION)))
            #endif
        #endif

        #if (FS_C1_I0_ALT_NUMBER >= 2)
            // AlternateSetting 1
            #define FS_C1_I0_A1_EP_LENGTH           (EP_LENGTH * FS_C1_I0_A1_EP_NUMBER)
            #if (FS_C1_I0_A1_EP_NUMBER >= 1)
                // EP1
                #define FS_C1_I0_A1_EP1_FIFO_START  FIFO0
                #define FS_C1_I0_A1_EP1_FIFO_NO     (FS_C1_I0_A1_EP1_BLKNO * FS_C1_I0_A1_EP1_BLKSIZE)
                #define FS_C1_I0_A1_EP1_FIFO_CONFIG (0x80 | ((FS_C1_I0_A1_EP1_BLKSIZE - 1) << 4) | ((FS_C1_I0_A1_EP1_BLKNO - 1) << 2) | FS_C1_I0_A1_EP1_TYPE)
                #define FS_C1_I0_A1_EP1_FIFO_MAP    (((1 - FS_C1_I0_A1_EP1_DIRECTION) << 4) | EP1)
                #define FS_C1_I0_A1_EP1_MAP         (FS_C1_I0_A1_EP1_FIFO_START |   (FS_C1_I0_A1_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A1_EP1_DIRECTION)))
            #endif
            #if (FS_C1_I0_A1_EP_NUMBER >= 2)
                // EP2
                #define FS_C1_I0_A1_EP2_FIFO_START  (FS_C1_I0_A1_EP1_FIFO_START + FS_C1_I0_A1_EP1_FIFO_NO)
                #define FS_C1_I0_A1_EP2_FIFO_NO     (FS_C1_I0_A1_EP2_BLKNO * FS_C1_I0_A1_EP2_BLKSIZE)
                #define FS_C1_I0_A1_EP2_FIFO_CONFIG (0x80 | ((FS_C1_I0_A1_EP2_BLKSIZE - 1) << 4) | ((FS_C1_I0_A1_EP2_BLKNO - 1) << 2) | FS_C1_I0_A1_EP2_TYPE)
                #define FS_C1_I0_A1_EP2_FIFO_MAP    (((1 - FS_C1_I0_A1_EP2_DIRECTION) << 4) | EP2)
                #define FS_C1_I0_A1_EP2_MAP         (FS_C1_I0_A1_EP2_FIFO_START |   (FS_C1_I0_A1_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A1_EP2_DIRECTION)))
            #endif
            #if (FS_C1_I0_A1_EP_NUMBER >= 3)
                // EP3
                #define FS_C1_I0_A1_EP3_FIFO_START  (FS_C1_I0_A1_EP2_FIFO_START + FS_C1_I0_A1_EP2_FIFO_NO)
                #define FS_C1_I0_A1_EP3_FIFO_NO     (FS_C1_I0_A1_EP3_BLKNO * FS_C1_I0_A1_EP3_BLKSIZE)
                #define FS_C1_I0_A1_EP3_FIFO_CONFIG (0x80 | ((FS_C1_I0_A1_EP3_BLKSIZE - 1) << 4) | ((FS_C1_I0_A1_EP3_BLKNO - 1) << 2) | FS_C1_I0_A1_EP3_TYPE)
                #define FS_C1_I0_A1_EP3_FIFO_MAP    (((1 - FS_C1_I0_A1_EP3_DIRECTION) << 4) | EP3)
                #define FS_C1_I0_A1_EP3_MAP         (FS_C1_I0_A1_EP3_FIFO_START |   (FS_C1_I0_A1_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I0_A1_EP3_DIRECTION)))
            #endif
        #endif

        #if (FS_C1_I0_ALT_NUMBER == 1)
            #define FS_C1_I0_ALT_LENGTH             (FS_C1_I0_A0_EP_LENGTH)
        #elif (FS_C1_I0_ALT_NUMBER == 2)
            #define FS_C1_I0_ALT_LENGTH             (FS_C1_I0_A0_EP_LENGTH + FS_C1_I0_A1_EP_LENGTH)
        #endif
    #endif

    #if (FS_C1_INTERFACE_NUMBER >= 2)
        // Interface 1
        #if (FS_C1_I1_ALT_NUMBER >= 1)
            // AlternateSetting 0
            #define FS_C1_I1_A0_EP_LENGTH           (EP_LENGTH * FS_C1_I1_A0_EP_NUMBER)
            #if (FS_C1_I1_A0_EP_NUMBER >= 1)
                // EP1
                #define FS_C1_I1_A0_EP1_FIFO_START  FIFO0
                #define FS_C1_I1_A0_EP1_FIFO_NO     (FS_C1_I1_A0_EP1_BLKNO * FS_C1_I1_A0_EP1_BLKSIZE)
                #define FS_C1_I1_A0_EP1_FIFO_CONFIG (0x80 | ((FS_C1_I1_A0_EP1_BLKSIZE - 1) << 4) | ((FS_C1_I1_A0_EP1_BLKNO - 1) << 2) | FS_C1_I1_A0_EP1_TYPE)
                #define FS_C1_I1_A0_EP1_FIFO_MAP    (((1 - FS_C1_I1_A0_EP1_DIRECTION) << 4) | EP1)
                #define FS_C1_I1_A0_EP1_MAP         (FS_C1_I1_A0_EP1_FIFO_START |   (FS_C1_I1_A0_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I1_A0_EP1_DIRECTION)))
            #endif
            #if (FS_C1_I1_A0_EP_NUMBER >= 2)
                // EP2
                #define FS_C1_I1_A0_EP2_FIFO_START  (FS_C1_I1_A0_EP1_FIFO_START + FS_C1_I1_A0_EP1_FIFO_NO)
                #define FS_C1_I1_A0_EP2_FIFO_NO     (FS_C1_I1_A0_EP2_BLKNO * FS_C1_I1_A0_EP2_BLKSIZE)
                #define FS_C1_I1_A0_EP2_FIFO_CONFIG (0x80 | ((FS_C1_I1_A0_EP2_BLKSIZE - 1) << 4) | ((FS_C1_I1_A0_EP2_BLKNO - 1) << 2) | FS_C1_I1_A0_EP2_TYPE)
                #define FS_C1_I1_A0_EP2_FIFO_MAP    (((1 - FS_C1_I1_A0_EP2_DIRECTION) << 4) | EP2)
                #define FS_C1_I1_A0_EP2_MAP         (FS_C1_I1_A0_EP2_FIFO_START |   (FS_C1_I1_A0_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I1_A0_EP2_DIRECTION)))
            #endif
            #if (FS_C1_I1_A0_EP_NUMBER >= 3)
                // EP3
                #define FS_C1_I1_A0_EP3_FIFO_START  (FS_C1_I1_A0_EP2_FIFO_START + FS_C1_I1_A0_EP2_FIFO_NO)
                #define FS_C1_I1_A0_EP3_FIFO_NO     (FS_C1_I1_A0_EP3_BLKNO * FS_C1_I1_A0_EP3_BLKSIZE)
                #define FS_C1_I1_A0_EP3_FIFO_CONFIG (0x80 | ((FS_C1_I1_A0_EP3_BLKSIZE - 1) << 4) | ((FS_C1_I1_A0_EP3_BLKNO - 1) << 2) | FS_C1_I1_A0_EP3_TYPE)
                #define FS_C1_I1_A0_EP3_FIFO_MAP    (((1 - FS_C1_I1_A0_EP3_DIRECTION) << 4) | EP3)
                #define FS_C1_I1_A0_EP3_MAP         (FS_C1_I1_A0_EP3_FIFO_START |   (FS_C1_I1_A0_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I1_A0_EP3_DIRECTION)))
            #endif
        #endif

        #if (FS_C1_I1_ALT_NUMBER >= 2)
            // AlternateSetting 1
            #define FS_C1_I1_A1_EP_LENGTH           (EP_LENGTH * FS_C1_I1_A1_EP_NUMBER)
            #if (FS_C1_I1_A1_EP_NUMBER >= 1)
                // EP1
                #define FS_C1_I1_A1_EP1_FIFO_START  FIFO0
                #define FS_C1_I1_A1_EP1_FIFO_NO     (FS_C1_I1_A1_EP1_BLKNO * FS_C1_I1_A1_EP1_BLKSIZE)
                #define FS_C1_I1_A1_EP1_FIFO_CONFIG (0x80 | ((FS_C1_I1_A1_EP1_BLKSIZE - 1) << 4) | ((FS_C1_I1_A1_EP1_BLKNO - 1) << 2) | FS_C1_I1_A1_EP1_TYPE)
                #define FS_C1_I1_A1_EP1_FIFO_MAP    (((1 - FS_C1_I1_A1_EP1_DIRECTION) << 4) | EP1)
                #define FS_C1_I1_A1_EP1_MAP         (FS_C1_I1_A1_EP1_FIFO_START |   (FS_C1_I1_A1_EP1_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I1_A1_EP1_DIRECTION)))
            #endif
            #if (FS_C1_I1_A1_EP_NUMBER >= 2)
                // EP2
                #define FS_C1_I1_A1_EP2_FIFO_START  (FS_C1_I1_A1_EP1_FIFO_START + FS_C1_I1_A1_EP1_FIFO_NO)
                #define FS_C1_I1_A1_EP2_FIFO_NO     (FS_C1_I1_A1_EP2_BLKNO * FS_C1_I1_A1_EP2_BLKSIZE)
                #define FS_C1_I1_A1_EP2_FIFO_CONFIG (0x80 | ((FS_C1_I1_A1_EP2_BLKSIZE - 1) << 4) | ((FS_C1_I1_A1_EP2_BLKNO - 1) << 2) | FS_C1_I1_A1_EP2_TYPE)
                #define FS_C1_I1_A1_EP2_FIFO_MAP    (((1 - FS_C1_I1_A1_EP2_DIRECTION) << 4) | EP2)
                #define FS_C1_I1_A1_EP2_MAP         (FS_C1_I1_A1_EP2_FIFO_START |   (FS_C1_I1_A1_EP2_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I1_A1_EP2_DIRECTION)))
            #endif
            #if (FS_C1_I1_A1_EP_NUMBER >= 3)
                // EP3
                #define FS_C1_I1_A1_EP3_FIFO_START  (FS_C1_I1_A1_EP2_FIFO_START + FS_C1_I1_A1_EP2_FIFO_NO)
                #define FS_C1_I1_A1_EP3_FIFO_NO     (FS_C1_I1_A1_EP3_BLKNO * FS_C1_I1_A1_EP3_BLKSIZE)
                #define FS_C1_I1_A1_EP3_FIFO_CONFIG (0x80 | ((FS_C1_I1_A1_EP3_BLKSIZE - 1) << 4) | ((FS_C1_I1_A1_EP3_BLKNO - 1) << 2) | FS_C1_I1_A1_EP3_TYPE)
                #define FS_C1_I1_A1_EP3_FIFO_MAP    (((1 - FS_C1_I1_A1_EP3_DIRECTION) << 4) | EP3)
                #define FS_C1_I1_A1_EP3_MAP         (FS_C1_I1_A1_EP3_FIFO_START |   (FS_C1_I1_A1_EP3_FIFO_START << 4)   | (MASK_F0 >> (4*FS_C1_I1_A1_EP3_DIRECTION)))
            #endif
        #endif

        #if (FS_C1_I1_ALT_NUMBER == 1)
            #define FS_C1_I1_ALT_LENGTH             (FS_C1_I1_A0_EP_LENGTH)
        #elif (FS_C1_I1_ALT_NUMBER == 2)
            #define FS_C1_I1_ALT_LENGTH             (FS_C1_I1_A0_EP_LENGTH + FS_C1_I1_A1_EP_LENGTH)
        #endif
    #endif

    #if (FS_C1_INTERFACE_NUMBER == 1)
        #define FS_C1_INTERFACE_LENGTH              (FS_C1_I0_ALT_LENGTH)
    #elif (FS_C1_INTERFACE_NUMBER == 2)
        #define FS_C1_INTERFACE_LENGTH              (FS_C1_I0_ALT_LENGTH + HS_FS_C1_I1_ALT_LENGTH)
    #endif
#endif

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#define USB_ENABLE_UP_DMA()  USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,    \
                                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT0)) // upstream DMA enable
                                                    
#define USB_DISABLE_UP_DMA()  USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,    \
                                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT0))) // upstream DMA disable

#define USB_UP_STREAM_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT3)))   // upQ stream mode

#define USB_UP_PACKET_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT3))          // upQ packet mode

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#define USB_ENABLE_LP_DN_DMA()  USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,    \
                                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT1))    // lp downstream DMA enable

#define USB_DISABLE_LP_DN_DMA()  USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,    \
                                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT1)))   // lp downstream DMA disable

#define USB_LP_DN_PACKET_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT6)))   // lpQ packet mode

#define USB_LP_DN_STREAM_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT6))          // lpQ stream mode

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#define USB_ENABLE_HP_DN_DMA() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,  \
                                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT8))    // hp downstream DMA enable 

#define USB_DISABLE_HP_DN_DMA() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,  \
                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT8)))  // hp downstream DMA disable 

#define USB_HP_DN_PACKET_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT7)))   // hpQ packet mode

#define USB_HP_DN_STREAM_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT7))          // hpQ stream mode

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#define USB_ENABLE_MP_DN_DMA() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT9))    // mp downstream DMA enable 

#define USB_DISABLE_MP_DN_DMA() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT9)))    // mp downstream DMA disable 

#define USB_MP_DN_PACKET_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT10)))   // hpQ packet mode

#define USB_MP_DN_STREAM_MODE() USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT10))          // hpQ stream mode

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

#define USB_ENABLE_UP_PACKET_MODE()     USB_DISABLE_UP_DMA();    \
                                            USB_UP_PACKET_MODE();   \
                                            USB_ENABLE_UP_DMA();

#define USB_ENABLE_LP_DN_PACKET_MODE()  USB_DISABLE_LP_DN_DMA();    \
                                            USB_LP_DN_PACKET_MODE();   \
                                            USB_ENABLE_LP_DN_DMA()

#define USB_ENABLE_MP_DN_PACKET_MODE()   USB_DISABLE_MP_DN_DMA();    \
                                            USB_MP_DN_PACKET_MODE();   \
                                            USB_ENABLE_MP_DN_DMA();

#define USB_ENABLE_HP_DN_PACKET_MODE()    USB_DISABLE_HP_DN_DMA();    \
                                            USB_HP_DN_PACKET_MODE();   \
                                            USB_ENABLE_HP_DN_DMA();

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#define USB_ENABLE_UP_STREAM_MODE()    USB_DISABLE_UP_DMA();    \
                                        USB_UP_STREAM_MODE();   \
                                        USB_ENABLE_UP_DMA();

#define USB_ENABLE_LP_DN_STREAM_MODE()    USB_DISABLE_LP_DN_DMA();    \
                                            USB_LP_DN_STREAM_MODE();   \
                                            USB_ENABLE_LP_DN_DMA()

#define USB_ENABLE_MP_DN_STREAM_MODE()    USB_DISABLE_MP_DN_DMA();    \
                                            USB_MP_DN_STREAM_MODE();   \
                                            USB_ENABLE_MP_DN_DMA();

#define USB_ENABLE_HP_DN_STREAM_MODE()    USB_DISABLE_HP_DN_DMA();    \
                                            USB_HP_DN_STREAM_MODE();   \
                                            USB_ENABLE_HP_DN_DMA();

#define USB_STREAM_HOST_BUF_SIZE(size)  USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                                                                            (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|(size)));   
#define USB_STREAM_TIMEOUT(time_cnt)    USB_WORD_REG_WRITE(ZM_SOC_USB_TIME_CTRL_OFFSET, time_cnt);  // set stream mode timeout critirea
#define USB_STREAM_AGG_PKT_CNT(cnt)     USB_WORD_REG_WRITE(ZM_SOC_USB_MAX_AGGREGATE_OFFSET, cnt); // set stream mode packet buffer critirea

#endif
