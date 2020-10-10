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
#include "usb_type.h"
#include "usb_table.h"
#include "sys_cfg.h"

#if SYSTEM_MODULE_USB

//#if defined(_ROM_)
//const uint16_t UsbDeviceDescriptor[] __attribute__ ((section(".dport0.usb_in_rom"))) = 
//#else
uint16_t UsbDeviceDescriptor[] =
//#endif
{
    m2BYTE(USB_DEVICE_DESC_LEN, USB_DEVICE_DESC_TYPE),
    USB_SPEC_VERSION,
    m2BYTE(USB_DEVICE_CLASS, USB_DEVICE_SUB_CLASS),
    m2BYTE(USB_DEVICE_PROTOCOL, USB_MAX_PKT_SIZE),
    USB_VENDOR_ID,
    USB_PRODUCT_ID,
    USB_DEVICE_BCD,
    m2BYTE(USB_MANUFACTURER_INDEX, USB_PRODUCT_INDEX),
    m2BYTE(USB_SERIAL_INDEX, USB_CONFIGURATION_NUM)
};

//#if defined(_ROM_)
//const uint16_t u8HSConfigDescriptor01[] __attribute__ ((section(".dport0.usb_in_rom"))) =
//#else
uint16_t u8HSConfigDescriptor01[] =
//#endif
{
    m2BYTE(USB_CONFIG_DESC_LEN, USB_CONFIG_DESC_TYPE),
    USB_TOTAL_DESC_LEN,
    m2BYTE(USB_INTERFACE_NUM, USB_CONFIG_NUM),
    m2BYTE(USB_STRING_INDEX, USB_ATTRIBUTE),
    m2BYTE(USB_MAX_POWER, USB_INTERFACE_DESC_LEN),
    m2BYTE(USB_INTERFACE_DESC_TYPE, USB_INTERFACE_INDEX_NUM),
    m2BYTE(USB_INTERFACE_ALT_SETTING, USB_INTERFACE_EP_NUM),
    m2BYTE(USB_INTERFACE_CLASS, USB_INTERFACE_SUB_CLASS),
    m2BYTE(USB_INTERFACE_PROTOCOL, USB_INTERFACE_STRING_INDEX),
    m2BYTE(USB_EP_DESC_LEN, USB_EP_DESC_TYPE),                      // EP 1
    m2BYTE(USB_HS_EP1_ADDRESS, USB_HS_EP1_ATTRIBUTE),
    USB_HS_EP1_MAX_PACKET_SIZE, 
    m2BYTE(USB_HS_EP1_INTERVAL, USB_EP_DESC_LEN),                   // EP 2
    m2BYTE(USB_EP_DESC_TYPE, USB_HS_EP2_ADDRESS),
    m2BYTE(USB_HS_EP2_ATTRIBUTE, USB_HS_EP2_MAX_PACKET_SIZE),
    m2BYTE(mHIGH_BYTE(USB_HS_EP2_MAX_PACKET_SIZE), USB_HS_EP2_INTERVAL),
    m2BYTE(USB_EP_DESC_LEN, USB_EP_DESC_TYPE),                      // EP 3
    m2BYTE(USB_HS_EP3_ADDRESS, USB_HS_EP3_ATTRIBUTE),
    USB_HS_EP3_MAX_PACKET_SIZE,
    m2BYTE(USB_HS_EP3_INTERVAL, USB_EP_DESC_LEN),                   // EP 4
    m2BYTE(USB_EP_DESC_TYPE, USB_HS_EP4_ADDRESS),
    m2BYTE(USB_HS_EP4_ATTRIBUTE, USB_HS_EP4_MAX_PACKET_SIZE),
    m2BYTE(mHIGH_BYTE(USB_HS_EP4_MAX_PACKET_SIZE), USB_HS_EP4_INTERVAL),
    m2BYTE(USB_EP_DESC_LEN, USB_EP_DESC_TYPE),                      // EP 5
    m2BYTE(USB_HS_EP5_ADDRESS, USB_HS_EP5_ATTRIBUTE),
    USB_HS_EP5_MAX_PACKET_SIZE,
    m2BYTE(USB_HS_EP5_INTERVAL, USB_EP_DESC_LEN),                 // EP 6
    m2BYTE(USB_EP_DESC_TYPE, USB_HS_EP6_ADDRESS),
    m2BYTE(USB_HS_EP6_ATTRIBUTE, USB_HS_EP6_MAX_PACKET_SIZE),
    m2BYTE(mHIGH_BYTE(USB_HS_EP6_MAX_PACKET_SIZE), USB_HS_EP6_INTERVAL)
};


//#if defined(_ROM_)
//const uint16_t u8FSConfigDescriptor01[] __attribute__ ((section(".dport0.usb_in_rom"))) =
//#else
uint16_t u8FSConfigDescriptor01[] =
//#endif
{
    m2BYTE(USB_CONFIG_DESC_LEN, USB_CONFIG_DESC_TYPE),
    USB_TOTAL_DESC_LEN,
    m2BYTE(USB_INTERFACE_NUM, USB_CONFIG_NUM),
    m2BYTE(USB_STRING_INDEX, USB_ATTRIBUTE),
    m2BYTE(USB_MAX_POWER, USB_INTERFACE_DESC_LEN),
    m2BYTE(USB_INTERFACE_DESC_TYPE, USB_INTERFACE_INDEX_NUM),
    m2BYTE(USB_INTERFACE_ALT_SETTING, USB_INTERFACE_EP_NUM),
    m2BYTE(USB_INTERFACE_CLASS, USB_INTERFACE_SUB_CLASS),
    m2BYTE(USB_INTERFACE_PROTOCOL, USB_INTERFACE_STRING_INDEX),
    m2BYTE(USB_EP_DESC_LEN, USB_EP_DESC_TYPE),                      // EP 1
    m2BYTE(USB_FS_EP1_ADDRESS, USB_FS_EP1_ATTRIBUTE),
    USB_FS_EP1_MAX_PACKET_SIZE,
    m2BYTE(USB_FS_EP1_INTERVAL, USB_EP_DESC_LEN),                   // EP 2
    m2BYTE(USB_EP_DESC_TYPE, USB_FS_EP2_ADDRESS),
    m2BYTE(USB_FS_EP2_ATTRIBUTE, USB_FS_EP2_MAX_PACKET_SIZE),
    m2BYTE(mHIGH_BYTE(USB_FS_EP2_MAX_PACKET_SIZE), USB_FS_EP2_INTERVAL),
    m2BYTE(USB_EP_DESC_LEN, USB_EP_DESC_TYPE),                      // EP 3
    m2BYTE(USB_FS_EP3_ADDRESS, USB_FS_EP3_ATTRIBUTE),
    USB_FS_EP3_MAX_PACKET_SIZE, 
    m2BYTE(USB_FS_EP3_INTERVAL, USB_EP_DESC_LEN),                   // EP 4
    m2BYTE(USB_EP_DESC_TYPE, USB_FS_EP4_ADDRESS),
    m2BYTE(USB_FS_EP4_ATTRIBUTE, USB_FS_EP4_MAX_PACKET_SIZE),
    m2BYTE(mHIGH_BYTE(USB_FS_EP4_MAX_PACKET_SIZE), USB_FS_EP4_INTERVAL),
    m2BYTE(USB_EP_DESC_LEN, USB_EP_DESC_TYPE),                      // EP 5
    m2BYTE(USB_FS_EP5_ADDRESS, USB_FS_EP5_ATTRIBUTE),
    USB_FS_EP5_MAX_PACKET_SIZE, 
    m2BYTE(USB_FS_EP5_INTERVAL, USB_EP_DESC_LEN),                   // EP 6
    m2BYTE(USB_EP_DESC_TYPE, USB_FS_EP6_ADDRESS),
    m2BYTE(USB_FS_EP6_ATTRIBUTE, USB_FS_EP6_MAX_PACKET_SIZE),
    m2BYTE(mHIGH_BYTE(USB_FS_EP6_MAX_PACKET_SIZE), USB_FS_EP6_INTERVAL)
};

uint16_t u8DeviceQualifierDescriptorEX[] =
{
    0x0000,
    0x0000,
    0x0000,
    0x0000,
    0x0000
};

uint16_t u8OtherSpeedConfigDescriptorEX[] =
{
    0x0709,             // 0
    0x0000,
    0x0000,
    0x0000,
    0x0000,
    0x0000,             // 5
    0x0000,
    0x0000,
    0x0000,
    0x0000,
    0x0000,             // 10
    0x0000,
    0x0000,
    0x0000,
    0x0000,
    0x0000,             // 15
    0x0000,
    0x0000,
    0x0000,
    0x0000,
    0x0000,             // 20
    0x0000,
    0x0000,
    0x0000,
    0x0000,
    0x0000,             // 25
    0x0000,
    0x0000,
    0x0000,
    0x0000
};

//#if defined(_ROM_)
//const uint16_t String00Descriptor[] __attribute__ ((section(".dport0.usb_in_rom"))) = 
//#else
uint16_t String00Descriptor[] = 
//#endif
{
	0x0304, 
	0x0409
};

//#if defined(_ROM_)
//const uint16_t String10Descriptor[] __attribute__ ((section(".dport0.usb_in_rom"))) = 
//#else
uint16_t String10Descriptor[] = 
//#endif
{
	0x0360,	    		//length
	0x0041, 			//A
	0x0054, 			//T
	0x0048, 			//H 
	0x0045, 			//E 
	0x0052, 			//R
	0x004f, 			//O
	0x0053,             //S
    0x002c,             //,
	0x0041, 			//A
	0x0054, 			//T
	0x0048, 			//H 
	0x0045, 			//E 
	0x0052, 			//R
	0x004f, 			//O
	0x0053,             //S
    0x002c,             //,
	0x0041, 			//A
	0x0054, 			//T
	0x0048, 			//H 
	0x0045, 			//E 
	0x0052, 			//R
	0x004f, 			//O
	0x0053,             //S
    0x002c,             //,
	0x0041, 			//A
	0x0054, 			//T
	0x0048, 			//H 
	0x0045, 			//E 
	0x0052, 			//R
	0x004f, 			//O
	0x0053,             //S
    0x002c,             //,
	0x0041, 			//A
	0x0054, 			//T
	0x0048, 			//H 
	0x0045, 			//E 
	0x0052, 			//R
	0x004f, 			//O
	0x0053,             //S
    0x002c,             //,
	0x0041, 			//A
	0x0054, 			//T
	0x0048, 			//H 
	0x0045, 			//E 
	0x0052, 			//R
	0x004f, 			//O
	0x0053,             //S	
};

//#if defined(_ROM_)
//const uint16_t String20Descriptor[] __attribute__ ((section(".dport0.usb_in_rom"))) = 
//#else
uint16_t String20Descriptor[] = 
//#endif
{
	0x0318,			 //length
	0x0055,          //'U' 
	0x0053,          //'S'
	0x0042,          //'B'
	0x0032,          //'2'
	0x002E,          //'.'
	0x0030,          //'0'
	0x0020,          //' '
	0x0057,          //'W'
	0x004C,          //'L'
	0x0041,          //'A'
	0x004E,          //'N'
};

//#if defined(_ROM_)
//const uint16_t String30Descriptor[] __attribute__ ((section(".dport0.usb_in_rom"))) = 
//#else
uint16_t String30Descriptor[] = 
//#endif
{
	0x030c,			 //length
	0x0031,          //;'1'
	0x0032,          //;'2'
	0x0033,          //;'3'
	0x0034,          //;'4'
	0x0035,          //;'5'
};

#endif
