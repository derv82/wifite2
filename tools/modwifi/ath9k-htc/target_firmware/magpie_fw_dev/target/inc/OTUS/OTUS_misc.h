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
#ifndef __AR6K_MISC_H__
#define __AR6K_MISC_H__

/*
 * AR6001: CIS Tuple 0x82, "Board Hardware Configuration Information",
 * is set at chip reset according to board configuration.  Bits in this
 * register indicate what type of Host connection is in use. We don't
 * have proper header files to describe tuples, so the offset and layout
 * for the one tuple that firmwware needs is defined here.
 *
 * AR6002: The RESET_TUPLE_STATUS register in the GPIO block holds
 * Board Hardware Configuration Information.
 *
 * If the interface is SDIO, then the "INFO_MASK" must be "SDIO_NORMAL".
 * For debug purposes, a Target with the KeepAlive jumper may be booted
 * before the Host.  In this case, INFO_MASK is 0.
 *
 * For NON-SDIO Host interfaces, the INFO_MASK may hold board information.
 *
 * By convention, hostless boards set INTERFACE to SDIO, and INFO to
 * something OTHER than SDIO_NORMAL or 0.
 * 
 * Layout of Board HW Cfg Info is below.  These values are captured at
 * reset and made available to software.
 *
 * These 3 bits are available on AR6002 via RESET_TUPLE_STATUS_ADDRESS;
 * they are NOT available on AR6001.
 * bit 10: rftest               ???
 * bit  9: cmode[1]             Bits 9..8 indicate modes as follows:
 * bit  8: cmode[0]             0-->normal
 *                              1-->rftest
 *                              2-->functional test (ATE)
 *                              3-->ATPG/MBIST
 *
 * These 8 bits are available on AR6002 through RESET_TUPLE_STATUS_ADDRESS
 * and on both AR6001 and AR6002 through CIS Tuple 0x82.
 * bit  7: gpio9 (aka hmode0)    Bits 7..6 are the "Interface Config bits"
 * bit  6: tdo   (aka hmode1)
 * bit  5: clk_req
 * bit  4: sdio_cmd
 * bit  3: sdio_dat[3]
 * bit  2: sdio_dat[2]
 * bit  1: sdio_dat[1]
 * bit  0: sdio_dat[0]
 */

#if defined(RESET_TUPLE_STATUS_ADDRESS)
#define AR6K_BOARD_HWCFG_CMODE_MASK 0x300
#define AR6K_BOARD_HWCFG_CMODE_ATE  0x200
#else
/*
 * CIS Tuple 0x82 happens to be located at offset 0x13c into CIS registers.
 * This may change across tapeouts, if CIS tuple information changes.
 */
#define AR6K_BOARD_HWCFG_TUPLE_OFFSET    0x13c
#endif

#define AR6K_BOARD_HWCFG_INTERFACE_MASK  0xc0
#define AR6K_BOARD_HWCFG_KEEP_ALIVE_MASK 0x20
#define AR6K_BOARD_HWCFG_INFO_MASK       0x1f

/* Values for INTERFACE_MASK indicate type of interface */
#define AR6K_BOARD_HWCFG_SPI             0x00
#define AR6K_BOARD_HWCFG_SDIO            0x40
#define AR6K_BOARD_HWCFG_LBCF            0x80
#define AR6K_BOARD_HWCFG_MSIO            0xc0

#define AR6K_BOARD_HWCFG_SDIO_NORMAL     0x1f

#endif /* __AR6K_MISC_H__ */
