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
#ifndef _USB_TABLE_H_
#define _USB_TABLE_H_

// UsbDeviceDescriptor
#define USB_DEVICE_DESC_TYPE            0x01
#define USB_DEVICE_DESC_LEN             0x12
#define USB_SPEC_VERSION                0x0200
#define USB_DEVICE_CLASS                0xFF
#define USB_DEVICE_SUB_CLASS            0xFF
#define USB_DEVICE_PROTOCOL             0xFF
#define USB_MAX_PKT_SIZE                0x40
#define USB_VENDOR_ID                   0x0CF3
#define USB_PRODUCT_ID                  0x7010
#define USB_DEVICE_BCD                  BOOTROM_VER
#define USB_MANUFACTURER_INDEX          0x10
#define USB_PRODUCT_INDEX               0x20
#define USB_SERIAL_INDEX                0x30
#define USB_CONFIGURATION_NUM           0x01
// end UsbDeviceDescriptor

#define USB_CONFIG_DESC_TYPE            0x02
#define USB_CONFIG_DESC_LEN             0x09
//#define USB_TOTAL_DESC_LEN              0x002E // 4 ep
//#define USB_TOTAL_DESC_LEN              0x0035 // 5 ep
#define USB_TOTAL_DESC_LEN              0x003C  // 6 ep
#define USB_INTERFACE_NUM               0x01
#define USB_CONFIG_NUM                  0x01
#define USB_STRING_INDEX                0x00
#define USB_ATTRIBUTE                   0x80
#define USB_MAX_POWER                   0xFA

#define USB_INTERFACE_DESC_TYPE         0x04
#define USB_INTERFACE_DESC_LEN          0x09
#define USB_INTERFACE_INDEX_NUM         0x00
#define USB_INTERFACE_ALT_SETTING       0x00
//#define USB_INTERFACE_EP_NUM            0x04
//#define USB_INTERFACE_EP_NUM            0x05
#define USB_INTERFACE_EP_NUM            0x06
#define USB_INTERFACE_CLASS             0xFF
#define USB_INTERFACE_SUB_CLASS         0x00
#define USB_INTERFACE_PROTOCOL          0x00
#define USB_INTERFACE_STRING_INDEX      0x00

#define USB_EP_DESC_TYPE                0x05
#define USB_EP_DESC_LEN                 0x07

/* USB Endpoint attribute */
#define bUSB_EP1_NUM                    0x01
#define bUSB_EP2_NUM                    0x02
#define bUSB_EP3_NUM                    0x03
#define bUSB_EP4_NUM                    0x04
#define bUSB_EP5_NUM                    0x05
#define bUSB_EP6_NUM                    0x06

#define bUSB_EP_DIRECTION_IN            0x80
#define bUSB_EP_DIRECTION_OUT           0x00

#define bUSB_EP_TYPE_CONTROL            0x00
#define bUSB_EP_TYPE_ISOCHRONOUS        0x01
#define bUSB_EP_TYPE_BULK               0x02
#define bUSB_EP_TYPE_INTERRUPT          0x03

#define bUSB_EP_MAX_PKT_SIZE_64         0x0040
#define bUSB_EP_MAX_PKT_SIZE_512        0x0200

/* High Speed Endpoint */
#define USB_HS_EP1_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP1_NUM)
#define USB_HS_EP1_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_HS_EP1_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_512
#define USB_HS_EP1_INTERVAL             0x00

#define USB_HS_EP2_ADDRESS              (bUSB_EP_DIRECTION_IN | bUSB_EP2_NUM)
#define USB_HS_EP2_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_HS_EP2_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_512
#define USB_HS_EP2_INTERVAL             0x00

#define USB_HS_EP3_ADDRESS              (bUSB_EP_DIRECTION_IN | bUSB_EP3_NUM)
#define USB_HS_EP3_ATTRIBUTE            bUSB_EP_TYPE_INTERRUPT
#define USB_HS_EP3_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_HS_EP3_INTERVAL             0x01

#define USB_HS_EP4_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP4_NUM)
#define USB_HS_EP4_ATTRIBUTE            bUSB_EP_TYPE_INTERRUPT //bUSB_EP_TYPE_BULK
#define USB_HS_EP4_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_HS_EP4_INTERVAL             0x01 //0x00

#define USB_HS_EP5_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP5_NUM)
#define USB_HS_EP5_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_HS_EP5_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_512
#define USB_HS_EP5_INTERVAL             0x00

#define USB_HS_EP6_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP6_NUM)
#define USB_HS_EP6_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_HS_EP6_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_512
#define USB_HS_EP6_INTERVAL             0x00

/* Full Speed Endpoint */
#define USB_FS_EP1_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP1_NUM)
#define USB_FS_EP1_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_FS_EP1_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_FS_EP1_INTERVAL             0x00

#define USB_FS_EP2_ADDRESS              (bUSB_EP_DIRECTION_IN | bUSB_EP2_NUM)
#define USB_FS_EP2_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_FS_EP2_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_FS_EP2_INTERVAL             0x00

#define USB_FS_EP3_ADDRESS              (bUSB_EP_DIRECTION_IN | bUSB_EP3_NUM)
#define USB_FS_EP3_ATTRIBUTE            bUSB_EP_TYPE_INTERRUPT
#define USB_FS_EP3_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_FS_EP3_INTERVAL             0x01

#define USB_FS_EP4_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP4_NUM)
#define USB_FS_EP4_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_FS_EP4_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_FS_EP4_INTERVAL             0x00

#define USB_FS_EP5_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP5_NUM)
#define USB_FS_EP5_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_FS_EP5_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_FS_EP5_INTERVAL             0x00

#define USB_FS_EP6_ADDRESS              (bUSB_EP_DIRECTION_OUT | bUSB_EP6_NUM)
#define USB_FS_EP6_ATTRIBUTE            bUSB_EP_TYPE_BULK
#define USB_FS_EP6_MAX_PACKET_SIZE      bUSB_EP_MAX_PKT_SIZE_64
#define USB_FS_EP6_INTERVAL             0x00

//#define USB_QUALIFIER_DESC_ADDR         0x8cff00
//#define USB_OTHER_SPEED_DESC_ADDR       0x8cffA

#endif	// end of _USB_TABLE_H_
