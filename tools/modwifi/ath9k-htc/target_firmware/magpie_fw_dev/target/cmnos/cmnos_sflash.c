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
#include "sys_cfg.h"
#include "athos_api.h"

#if SYSTEM_MODULE_SFLASH

#include "adf_os_io.h"

#include "reg_defs.h"
#include "sflash_api.h"

/*******************************************
 * Definitions of module internal constant *
 *******************************************/

/* Definitions of base address and Flash sise -> Project dependent */
#define ZM_SPI_REGISTER_BASE            SPI_REG_BASE_ADDRESS    /* 0x0005B000 */
#define ZM_SPI_FLASH_BASE               SPI_FLASH_BASE          /* 0x0F000000 */
#define ZM_SPI_FLASH_MAX_ADDR           SPI_FLASH_MAX_ADDR      /* 0x0FFFFFFF */
#define ZM_SPI_FLASH_MAX_SIZE           SPI_FLASH_MAX_SIZE      /* 0x01000000 */

/*
 * Base address of Clock and Reset Control Registers is 0x00050000
 * Offset of Clock Control Register is 0x40
 * SPI_SEL (bit 8) : Switch the function of I/O pin 19~22 between GPIO and SPI.
 *                   0 -> act as GPIO5~8;
 *                   1 -> act as SPI pins.
 */
#define ZM_SPI_CLK_CTRL_ADDR            0x00050040
#define ZM_SPI_SPI_SEL_BIT              0x100

/* Definitions of Serial Flash constants -> According to standard or vendor dependent */
#define ZM_SFLASH_PAGE_SIZE             256

/* Definitions of OP Code -> According to standard or vendor dependent */
#define ZM_SFLASH_OP_READ               0x03    /* Read Data Bytes */
#define ZM_SFLASH_OP_FAST_READ          0x0B    /* Read Data Bytes at Higher Speed */
/*
 * For MXIC,     sector erase : Command 0x20, size 4K bytes
 *               block erase  : Command 0xD8, size 64K bytes
 *               chip earse   : command 0x60 or 0xC7
 * For Spansion, sector erase : Command 0x20 or 0xD8, size 64K bytes (For 64 KB sector devices, either command is valid and performs the same function.)
 *               block erase  : Command 0xD8, size 256K bytes
 *               chip earse   : command 0x60 or 0xC7, Uniform 64 KB Sector Product (For 64 KB sector devices, either command is valid and performs the same function.)
 *                                      0xC7, Uniform 256 KB Sector Product
 */
#define ZM_SFLASH_OP_SE                 0x20    /* Sector Erase */
#define ZM_SFLASH_OP_BE                 0xD8    /* Block Erase */
#define ZM_SFLASH_OP_CE                 0xC7    /* Chip Erase */
#define ZM_SFLASH_OP_PP                 0x02    /* Page Program */
#define ZM_SFLASH_OP_RDSR               0x05    /* Read from Status Register */
#define ZM_SFLASH_OP_WRSR               0x01    /* Write to Status Register */
#define ZM_SFLASH_OP_WREN               0x06    /* Write Enable */
#define ZM_SFLASH_OP_WRDI               0x04    /* Write Disable */
#define ZM_SFLASH_OP_RDID               0x9F    /* Read Identification */
#define ZM_SFLASH_OP_DP                 0xB9    /* Deep Power Down */
#define ZM_SFLASH_OP_RES                0xAB    /* Release from Deep Power Down, Release from Deep Power Down and Read Electronic Signature */

/* Definitions of Status Register -> According to standard or vendor dependent */
/* Write in progress bit
 *  1 = Device Busy. A Write Status Register, program, or erase operation is in progress
 *  0 = Ready. Device is in standby mode and can accept commands.
 */
#define ZM_SFLASH_STATUS_REG_WIP        (1<<0)
/* Write enable latch bit
 *  1 = Device accepts Write Status Register, program, or erase commands
 *  0 = Ignores Write Status Register, program, or erase commands
 */
#define ZM_SFLASH_STATUS_REG_WEL        (1<<1)
/* Status register write disable bit
 *  1 = Protects when WP#/ACC is low
 *  0 = No protection, even when WP#/ACC is low
 */
#define ZM_SFLASH_STATUS_REG_SRWD       (1<<7)

/* Definitions of SPI Flash Controller -> SPI Flash Controller dependent */
/* SPI Flash Controller used in K2 project is part of Falcon's "Driver Support Logic" (DSL) block */
/*
 *  Offset				Register
 *  ======	==========================================================
 *  0x0000	SPI control/status register (SPI_CS)
 *  0x0004	SPI address/opcode register (SPI_AO)
 *  0x0008	SPI data register (SPI_D)
 */

/*
 *  SPI control/status register (SPI_CS)
 *  Access: R/W
 *  Cold reset: (See field descriptions)
 *  Warm reset: (Same as cold reset)
 *  Notes:
 *
 *  3:0   - Transmit byte count.  Determines the number of bytes
 *      transmitted from Falcon to the SPI device.  Values of 1-8 are
 *      valid; other values are illegal.  See the 'Notes' section below
 *      for details on how to use this field.  Resets to an undefined
 *      value.
 *  7:4   - Receive byte count.  Determines the number of bytes received
 *      from the SPI device into Falcon.  Values of 0-8 are valid;
 *      other values are illegal.  See the 'Notes' section below for
 *      details on how to use this field.  Resets to an undefined
 *      value.
 *  8	  - SPI transaction start.  Only writes to this field are
 *      meaningful; reads always return 0.  Resets to 0x0.  For writes:
 *        * A write of '1' starts the SPI transaction defined by the
 *          transmit byte count, receive byte count, SPI_AO, and SPI_D
 *          registers.
 *        * A write of '0' has no effect
 *  9     - SPI chip select 1 enable.  Resets to 0x0.  See bug 12540.
 *            0 - SP0 is enabled and SP1 is forced inactive.
 *            1 - SP1 is enabled and SP0 is forced inactive.
 *  15:10 - Reserved
 *  16    - Transaction busy indication.  Read-only; writes to this bit are
 *      ignored.  Resets to 0x0.
 *        0 - No SPI transaction is ongoing.  Software may start a new
 *        SPI transaction by writing to the 'SPI transaction start'
 *        bit within this register.
 *        1 - An SPI transaction presently is underway.  Software must
 *        not try to start a new SPI transaction, nor may software
 *        alter the value of any field of the SPI_CS, SPI_AO, or
 *        SPI_D registers.
 *  18:17 - Automatically-determined SPI address size.  Read-only; writes
 *      to this bit are ignored.  Resets to an undefined value, but
 *      then is updated after the autosizing process completes.
 *        0 - SPI address size was determined to be 16 bits
 *        1 - SPI address size was determined to be 24 bits
 *        2 - Reserved
 *        3 - Automatic SPI address size determination failed.  Typical
 *        causes of this result:
 *          * The SPI device is missing
 *          * The SPI device is unprogrammed
 *          * The SPI device is programmed with an incorrect
 *            SPI_MAGIC value
 *  20:19 - SPI autosize override.  Resets to 0x0.
 *        0 - Use automatically-determined SPI address size (see bits
 *        [18:17] of this register)
 *        1 - Force SPI address size to 16 bits
 *        2 - Force SPI address size to 24 bits
 *        3 - Reserved
 *  31:21 - Reserved
 */

#define SPI_CS_ADDRESS                      MAGPIE_REG_SPI_CS_ADDR //(ZM_SPI_REGISTER_BASE + 0x00000000)
/* 3:0 - Transmit byte count, values of 1-8 are valid */
#define SPI_CS_TXBCNT_MSB                   3
#define SPI_CS_TXBCNT_LSB                   0
#define SPI_CS_TXBCNT_MASK                  0x0000000f
#define SPI_CS_TXBCNT_GET(x)                (((x) & SPI_CS_TXBCNT_MASK) >> SPI_CS_TXBCNT_LSB)
#define SPI_CS_TXBCNT_SET(x)                (((0x0 | (x)) << SPI_CS_TXBCNT_LSB) & SPI_CS_TXBCNT_MASK)

/* 7:4 - Receive byte count, values of 1-8 are valid */
#define SPI_CS_RXBCNT_MSB                   7
#define SPI_CS_RXBCNT_LSB                   4
#define SPI_CS_RXBCNT_MASK                  0x000000f0
#define SPI_CS_RXBCNT_GET(x)                (((x) & SPI_CS_RXBCNT_MASK) >> SPI_CS_RXBCNT_LSB)
#define SPI_CS_RXBCNT_SET(x)                (((0x0 | (x)) << SPI_CS_RXBCNT_LSB) & SPI_CS_RXBCNT_MASK)

/* 8 - SPI transaction start */
#define SPI_CS_XCNSTART_MSB                 8
#define SPI_CS_XCNSTART_LSB                 8
#define SPI_CS_XCNSTART_MASK                0x00000100
#define SPI_CS_XCNSTART_GET(x)              0x0
#define SPI_CS_XCNSTART_SET(x)              (((0x0 | (x)) << SPI_CS_XCNSTART_LSB) & SPI_CS_XCNSTART_MASK)
#define SPI_CS_XCNSTART_RESET               0x0

/* 9 - SPI chip select */
#define SPI_CS_CS_MSB                       9
#define SPI_CS_CS_LSB                       9
#define SPI_CS_CS_MASK                      0x00000200
#define SPI_CS_CS_GET(x)                    (((x) & SPI_CS_CS_MASK) >> SPI_CS_CS_LSB)
#define SPI_CS_CS_SET(x)                    (((0x0 | (x)) << SPI_CS_CS_LSB) & SPI_CS_CS_MASK)
#define SPI_CS_CS_RESET                     0x0

/* 16 - Transaction busy indication */
#define SPI_CS_BUSY_MSB                     16
#define SPI_CS_BUSY_LSB                     16
#define SPI_CS_BUSY_MASK                    0x00010000
#define SPI_CS_BUSY_GET(x)                  (((x) & SPI_CS_BUSY_MASK) >> SPI_CS_BUSY_LSB)
#define SPI_CS_BUSY_SET(x)                  (((0x0 | (x)) << SPI_CS_BUSY_LSB) & SPI_CS_BUSY_MASK)
#define SPI_CS_BUSY_RESET                   0x0

/* 18:17 - Automatically-determined SPI address size */
#define SPI_CS_AUTOSIZ_MSB                  18
#define SPI_CS_AUTOSIZ_LSB                  17
#define SPI_CS_AUTOSIZ_MASK                 0x00060000
#define SPI_CS_AUTOSIZ_GET(x)               (((x) & SPI_CS_AUTOSIZ_MASK) >> SPI_CS_AUTOSIZ_LSB)
#define SPI_CS_AUTOSIZ_SET(x)               (((0x0 | (x)) << SPI_CS_AUTOSIZ_LSB) & SPI_CS_AUTOSIZ_MASK)

/* 20:19 - SPI autosize override */
#define SPI_CS_AUTOSIZ_OVR_MSB              20
#define SPI_CS_AUTOSIZ_OVR_LSB              19
#define SPI_CS_AUTOSIZ_OVR_MASK             0x00180000
#define SPI_CS_AUTOSIZ_OVR_GET(x)           (((x) & SPI_CS_AUTOSIZ_OVR_MASK) >> SPI_CS_AUTOSIZ_OVR_LSB)
#define SPI_CS_AUTOSIZ_OVR_SET(x)           (((0x0 | (x)) << SPI_CS_AUTOSIZ_OVR_LSB) & SPI_CS_AUTOSIZ_OVR_MASK)
#define SPI_CS_AUTOSIZ_OVR_RESET            0x0

#define SPI_CS_RESET                        (0x0 | \
                                            SPI_CS_AUTOSIZ_OVR_SET(SPI_CS_AUTOSIZ_OVR_RESET) | \
                                            SPI_CS_BUSY_SET(SPI_CS_BUSY_RESET) | \
                                            SPI_CS_CS_SET(SPI_CS_CS_RESET) | \
                                            SPI_CS_XCNSTART_SET(SPI_CS_XCNSTART_RESET))

/*
 *  SPI address/opcode register (SPI_AO)
 *  Access: R/W
 *  Cold reset: (See field descriptions)
 *  Warm reset: (Same as cold reset)
 *  Notes:
 *
 *  7:0   - SPI opcode.  Usually this field specifies the 8-bit opcode
 *      (aka "instruction") to transmit to the SPI device as the first
 *      part of an SPI transaction.  See the 'Notes' section below for
 *      more details. Resets to an undefined value.
 *  31:8  - Address.  Usually this field specifies the 24-bit address to
 *      transmit to the SPI device. See the 'Notes' section below for
 *      more details. Resets to an undefined value.
 */

#define SPI_AO_ADDRESS                      MAGPIE_REG_SPI_AO_ADDR //(ZM_SPI_REGISTER_BASE + 0x00000004)
/* 7:0 - SPI opcode */
#define SPI_AO_OPC_MSB                      7
#define SPI_AO_OPC_LSB                      0
#define SPI_AO_OPC_MASK                     0x000000ff
#define SPI_AO_OPC_GET(x)                   (((x) & SPI_AO_OPC_MASK) >> SPI_AO_OPC_LSB)
#define SPI_AO_OPC_SET(x)                   (((0x0 | (x)) << SPI_AO_OPC_LSB) & SPI_AO_OPC_MASK)
/* 31:8 - Address */
#define SPI_AO_ADDR_MSB                     31
#define SPI_AO_ADDR_LSB                     8
#define SPI_AO_ADDR_MASK                    0xffffff00
#define SPI_AO_ADDR_GET(x)                  (((x) & SPI_AO_ADDR_MASK) >> SPI_AO_ADDR_LSB)
#define SPI_AO_ADDR_SET(x)                  (((0x0 | (x)) << SPI_AO_ADDR_LSB)& SPI_AO_ADDR_MASK)

/*
 *  SPI data register (SPI_D)
 *  Access: R/W
 *  Cold reset: (See field descriptions)
 *  Warm reset: (Same as cold reset)
 *  Notes:
 *
 *  31:0  - SPI data.  Usually this register specifies a series of up to
 *      four data bytes to transmit to or receive from the SPI device.
 *      See the 'Notes' section below for more details.  Resets to an
 *      undefined value.
 */

#define SPI_D_ADDRESS                       MAGPIE_REG_SPI_D_ADDR //(ZM_SPI_REGISTER_BASE + 0x00000008)
/* 31:0 - SPI data */
#define SPI_D_DATA_MSB                      31
#define SPI_D_DATA_LSB                      0
#define SPI_D_DATA_MASK                     0xffffffff
#define SPI_D_DATA_GET(x)                   (((x) & SPI_D_DATA_MASK) >> SPI_D_DATA_LSB)
#define SPI_D_DATA_SET(x)                   (((0x0 | (x)) << SPI_D_DATA_LSB) & SPI_D_DATA_MASK)

/*
 *  SPI clock division register (SPI_CLKDIV)
 *  Access: R/W
 *  Cold reset: (See field descriptions)
 *  Warm reset: (Same as cold reset)
 *  Notes:
 *
 *  17:16  - 0b00(fastest), 0b01, 0b10, 0b11(slowest)
 */
#define SPI_CLKDIV_ADDRESS                  MAGPIE_REG_SPI_CLKDIV_ADDR //SPI_BASE_ADDRESS + 0x0000001c
#define SPI_CLKDIV_MSB                      17
#define SPI_CLKDIV_LSB                      16
#define SPI_CLKDIV_MASK                     0x00030000
#define SPI_CLKDIV_GET(x)                   (((x) & SPI_CLKDIV_MASK) >> SPI_CLKDIV_LSB)
#define SPI_CLKDIV_SET(x)                   (((0x0 | (x)) << SPI_CLKDIV_LSB) & SPI_CLKDIV_MASK) // read-then-write
#define SPI_CLKDIV_RESET                    0x3

/*
 *  Notes
 *  -----
 *  * Background
 *      An SPI transaction consists of three phases: an opcode transmit
 *      phase (always a single byte), followed by an optional address
 *      transmit phase of 0-3 bytes, followed by an optional data transmit
 *      or receive phase of 0-4 bytes.
 *
 *  Combined, then, an SPI transaction consists of a 1- to 8-byte
 *  transmit phase from Falcon to the SPI device, followed by a 0- to
 *  8-byte receive phase from the SPI device into Falcon.
 *
 *  The 'transmit byte count' field in the SPI_CS register controls the
 *  size (number of bytes) of the transmit phase.  The source of each
 *  of the bytes transmitted is fixed:
 *
 *    Byte	      Source
 *    ----  -----------------------------------------------------------
 *     0     SPI_AO[7:0] (the 'SPI opcode' field)
 *     1     SPI_AO[31:24] (the high byte of the 'SPI address' field)
 *     2     SPI_AO[23:16] (the middle byte of the 'SPI address' field)
 *     3     SPI_AO[15:8] (the low byte of the 'SPI address' field)
 *     4     SPI_D[7:0] (the low byte of the 'SPI data' register)
 *     5     SPI_D[15:8] (the next byte of the 'SPI data' register)
 *     6     SPI_D[23:16] (the next  byte of the 'SPI data' register)
 *     7     SPI_D[31:24] (the high byte of the 'SPI data' register)
 *
 *
 *  The 'receive byte count' field in the SPI_CS register controls the
 *  size (number of bytes) of the receive phase.  The destination of
 *  each of the bytes received is fixed:
 *
 *    Byte	       Destination
 *    ----  -----------------------------------------------------------
 *     0     SPI_D[7:0] (the low byte of the 'SPI data' register)
 *     1     SPI_D[15:8] (the next byte of the 'SPI data' register)
 *     2     SPI_D[23:16] (the next  byte of the 'SPI data' register)
 *     3     SPI_D[31:24] (the high byte of the 'SPI data' register)
 *     4     SPI_AO[7:0] (the 'SPI opcode' field)
 *     5     SPI_AO[15:8] (the low byte of the 'SPI address' field)
 *     6     SPI_AO[23:16] (the middle byte of the 'SPI address' field)
 *     7     SPI_AO[31:24] (the high byte of the 'SPI address' field)
 *
 *
 *  * To perform an SPI transaction:
 *    Write the appropriate values into the SPI_AO and SPI_D registers
 *  * Write the appropriate values into the 'transmit byte count' and
 *    'received byte count' fields of the SPI_CS register.
 *  * Write a '1' to the 'SPI transaction start' bit of the SPI_CS
 *    register (this step can be combined with the one above if desired
 *    so that only a single SPI_CS write is needed).
 *  * Poll the 'transaction busy indication' bit in the SPI_CS register
 *    until it is clear, indicating that the SPI transaction has
 *    completed.
 *  * If the transaction included a receive phase, then retrieve the
 *    received data by reading the appropriate bytes from the SPI_D and
 *    SPI_AO registers.
 *
 *
 *  * Examples:
 *      * A "write disable" (WRDI) transaction:
 *      * Opcode (SPI_AO[7:0]): 0x04 (for STMicro; varies by
 *        manufacturer and device type)
 *      * Address (SPI_AO[31:8]): don't care (not used)
 *      * Data (SPI_D[31:0]): don't care (not used)
 *      * Transmission byte count: 1
 *      * Receive byte count: 0
 *
 *      * A "read status register" (RDSR) transaction:
 *      * Opcode (SPI_AO[7:0]): 0x05 (for STMicro; varies by
 *        manufacturer and device type)
 *      * Address (SPI_AO[31:8]): don't care (not used)
 *      * Data (SPI_D[31:0]): don't care (not used)
 *      * Transmission byte count: 1
 *      * Receive byte count: 1
 *      * Read SPI_D[7:0] to retrieve status register value
 *
 *      * A "page program" (PP) transaction to write a value of 0xdeadbeef
 *        to address 0x123456:
 *      * Opcode (SPI_AO[7:0]): 0x02 (for STMicro; varies by
 *        manufacturer and device type)
 *      * Address (SPI_AO[31:8]): 0x123456
 *      * Data (SPI_D[31:0]): 0xdeadbeef
 *      * Transmission byte count: 8
 *      * Receive byte count: 0
 */

/* Wait till Transaction busy indication bit in SPI control/status register of Falcon's SPI Flash Controller is clear */
LOCAL void
_cmnos_sflash_WaitTillTransactionOver(void)
{
    A_UINT32        poldata;
    A_UINT32        flg;

    do
    {
        poldata = ioread32(SPI_CS_ADDRESS);

        flg = SPI_CS_BUSY_GET(poldata);
    } while (flg != 0x0);
}

/* Wait till Write In Progress bit in Status Register of Serial Flash is clear */
LOCAL void
_cmnos_sflash_WaitTillNotWriteInProcess(void)
{
    A_UINT32        flg;

    do
    {
        _cmnos_sflash_WaitTillTransactionOver();

        iowrite32(SPI_AO_ADDRESS, SPI_AO_OPC_SET(ZM_SFLASH_OP_RDSR));
        iowrite32(SPI_CS_ADDRESS, SPI_CS_TXBCNT_SET(1) | SPI_CS_RXBCNT_SET(1) | SPI_CS_XCNSTART_SET(1));

        _cmnos_sflash_WaitTillTransactionOver();

        flg = ioread32(SPI_D_ADDRESS) & ZM_SFLASH_STATUS_REG_WIP;

    } while (flg != 0x0);
}

/************************************************************************/
/* Function to Send WREN(Write Enable) Operation                        */
/************************************************************************/
LOCAL void
_cmnos_sflash_WriteEnable()
{
    _cmnos_sflash_WaitTillNotWriteInProcess();

    iowrite32(SPI_AO_ADDRESS, SPI_AO_OPC_SET(ZM_SFLASH_OP_WREN));
    iowrite32(SPI_CS_ADDRESS, SPI_CS_TXBCNT_SET(1) | SPI_CS_RXBCNT_SET(0) | SPI_CS_XCNSTART_SET(1));

    _cmnos_sflash_WaitTillTransactionOver();
}

/************************************************************************/
/* Function to Initialize SPI Flash Controller                          */
/************************************************************************/
LOCAL void
cmnos_sflash_init(void)
{
    /* Switch the function of I/O pin 19~22 to act as SPI pins */
	io32_set(MAGPIE_REG_CLOCK_CTRL_ADDR, BIT8);

    /* "Autosize-determination of the address size of serial flash" is obsolete according to Brian Yang's mail :
     *    The designers reached an conclusion that the spi master (the apb_spi interface control) will be
     *    modified as ¡§presuming the attached flash model to be 24-bit addressing¡¨, i.e., no more
     *    auto-size detection!
     *    Hence you are free to force the 24-bit addressing in the *.c test code.
     */

    /* Force SPI address size to 24 bits */
    iowrite32(SPI_CS_ADDRESS, SPI_CS_AUTOSIZ_OVR_SET(2));
}

/************************************************************************/
/* Function to Send Sector/Block/Chip Erase Operation                   */
/************************************************************************/
LOCAL void
cmnos_sflash_erase(A_UINT32 erase_type, A_UINT32 addr)
{
    A_UINT32    erase_opcode;
    A_UINT32    tx_len;

    if (erase_type == ZM_SFLASH_SECTOR_ERASE)
    {
        erase_opcode = ZM_SFLASH_OP_SE;
        tx_len = 4;
    }
    else if (erase_type == ZM_SFLASH_BLOCK_ERASE)
    {
        erase_opcode = ZM_SFLASH_OP_BE;
        tx_len = 4;
    }
    else
    {
        erase_opcode = ZM_SFLASH_OP_CE;
        tx_len = 1;
    }

    _cmnos_sflash_WriteEnable();
    _cmnos_sflash_WaitTillNotWriteInProcess();

    iowrite32(SPI_AO_ADDRESS, SPI_AO_OPC_SET(erase_opcode) | SPI_AO_ADDR_SET(addr));
    iowrite32(SPI_CS_ADDRESS, SPI_CS_TXBCNT_SET(tx_len) | SPI_CS_RXBCNT_SET(0) | SPI_CS_XCNSTART_SET(1));

#if 0
    /* Do not wait(let it be completed in background) */
    _cmnos_sflash_WaitTillTransactionOver();
#else
    /* Wait till completion */
    _cmnos_sflash_WaitTillNotWriteInProcess(); /* Chip Erase takes 80 - 200 seconds to complete */
#endif
}

/************************************************************************/
/* Function to Perform Page Program Operation                           */
/*      Notes:                                                          */
/*      Serial Flash has the following characteristics :                */
/*      1) In datasheet, 1-256 data bytes can be sent at a time, but    */
/*         Falcon supports only 4 bytes at a time.                      */
/*      2) If the eight least significant address bits(A7-A0) are not   */
/*         all 0, all transmitted data which goes beyond the end of the */
/*         current page are programmed from the start address in the    */
/*         same page.                                                   */
/*      This API hides the complexity of the above.                     */
/************************************************************************/
LOCAL void
cmnos_sflash_program(A_UINT32 addr, A_UINT32 len, A_UINT8 *buf)
{
    A_UINT32    s_addr, e_addr;
    A_UINT32    reminder, write_byte;
    A_UINT32    data_offset;
    A_UINT32    next_page_base;
    A_UINT32    t_word_data;

    e_addr = addr + len;
    for (s_addr = addr; s_addr < e_addr; )
    {
        next_page_base  = (s_addr - s_addr%ZM_SFLASH_PAGE_SIZE) + ZM_SFLASH_PAGE_SIZE;

        reminder = e_addr - s_addr;

        write_byte = next_page_base - s_addr;

        if (write_byte >= 4)
            write_byte = 4;

        if (write_byte > reminder)
            write_byte = reminder;

        data_offset = s_addr - addr;

        A_MEMCPY(&t_word_data, buf + data_offset, write_byte);

        _cmnos_sflash_WriteEnable();
        _cmnos_sflash_WaitTillNotWriteInProcess();

        iowrite32(SPI_AO_ADDRESS, SPI_AO_OPC_SET(ZM_SFLASH_OP_PP) | SPI_AO_ADDR_SET(s_addr));
        iowrite32(SPI_D_ADDRESS, SPI_D_DATA_SET(t_word_data));
        iowrite32(SPI_CS_ADDRESS, SPI_CS_TXBCNT_SET(4 + write_byte) | SPI_CS_RXBCNT_SET(0) | SPI_CS_XCNSTART_SET(1));

        _cmnos_sflash_WaitTillTransactionOver();

        s_addr += write_byte;
    }
}

/************************************************************************/
/* Function to Send Read/Fast Read Data Operation                       */
/************************************************************************/
LOCAL void
cmnos_sflash_read(A_UINT32 fast, A_UINT32 addr, A_UINT32 len, A_UINT8 *buf)
{
    A_UINT32    read_opcode;
    A_UINT32    i;
    A_UINT32    read_cnt, remainder;
    A_UINT32    write_byte, read_byte;

    if (fast)
    {
        read_opcode = ZM_SFLASH_OP_FAST_READ;
        write_byte  = 5;
    }
    else
    {
        read_opcode = ZM_SFLASH_OP_READ;
        write_byte  = 4;
    }

    read_cnt  = len/4;
    remainder = len%4;
    if (remainder)
        read_cnt++;

    read_byte = 4;
    for (i = 0; i < read_cnt; i ++)
    {
        if (i == read_cnt-1 && remainder)
            read_byte = remainder;

        _cmnos_sflash_WaitTillNotWriteInProcess();

        iowrite32(SPI_AO_ADDRESS, SPI_AO_OPC_SET(read_opcode) | SPI_AO_ADDR_SET(addr + i*4));
        iowrite32(SPI_CS_ADDRESS, SPI_CS_TXBCNT_SET(write_byte) | SPI_CS_RXBCNT_SET(read_byte) | SPI_CS_XCNSTART_SET(1));

        _cmnos_sflash_WaitTillTransactionOver();

        A_MEMCPY(buf + i*4, (A_UINT8 *)(SPI_D_ADDRESS), read_byte);
    }
}

/************************************************************************/
/* Function to Read Flash Status Register                               */
/************************************************************************/
LOCAL A_UINT32
cmnos_sflash_rdsr(void)
{
    A_UINT32    word_data;

    _cmnos_sflash_WaitTillTransactionOver();

    iowrite32(SPI_AO_ADDRESS, SPI_AO_OPC_SET(ZM_SFLASH_OP_RDSR));
    iowrite32(SPI_CS_ADDRESS, SPI_CS_TXBCNT_SET(1) | SPI_CS_RXBCNT_SET(1) | SPI_CS_XCNSTART_SET(1));

    _cmnos_sflash_WaitTillTransactionOver();

    word_data = ioread32(SPI_D_ADDRESS) & 0x000000FF;

    return word_data;
}

void
cmnos_sflash_module_install(struct sflash_api *tbl)
{
    /* Indispensable functions */
    tbl->_sflash_init       = cmnos_sflash_init;
    tbl->_sflash_erase      = cmnos_sflash_erase;
    tbl->_sflash_program    = cmnos_sflash_program;
    tbl->_sflash_read       = cmnos_sflash_read;

    /* Dispensable functions */
    tbl->_sflash_rdsr       = cmnos_sflash_rdsr;
}

#endif /* SYSTEM_MODULE_SFLASH */

