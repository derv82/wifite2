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
#ifndef __SFLASH_API_H__
#define __SFLASH_API_H__

/* Constant definition */
#define ZM_SFLASH_SECTOR_ERASE          1
#define ZM_SFLASH_BLOCK_ERASE           2
#define ZM_SFLASH_CHIP_ERASE            0

/*!- interface of eeprom access
 *
 */
struct sflash_api {
    /* Indispensable functions */
    void (* _sflash_init)(void);
    void (* _sflash_erase)(A_UINT32 erase_type, A_UINT32 addr);             /* 1. erase_type : chip/block/sector, 2. addr : no use for chip erase */
    void (* _sflash_program)(A_UINT32 addr, A_UINT32 len, A_UINT8 *buf);    /* 1. addr : spi flash address(start from 0x0), 2. len : bite number to write , 3. *buf : source memory address */
    void (* _sflash_read)(A_UINT32 fast, A_UINT32 addr, A_UINT32 len, A_UINT8 *buf);    /* 1. fast : 1 for fast read, 0 for read, 2. addr : spi flash address(start from 0x0), 3. len : bite number to read , 3. *buf : destination memory address */

    /* Dispensable functions */
    A_UINT32 (* _sflash_rdsr)(void); /* return the value of status register */
};

#endif /* __SFLASH_API_H__ */

