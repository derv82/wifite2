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
/************************************************************************/
/*  Copyright (c) 2013 Qualcomm Atheros, All Rights Reserved.           */
/*                                                                      */
/*  Module Name : desc_def.h                                            */
/*                                                                      */
/*  Abstract                                                            */
/*      This module contains DMA descriptor related definitions.        */
/*                                                                      */
/*  NOTES                                                               */
/*      None                                                            */
/*                                                                      */
/************************************************************************/

#ifndef _DESC_DEFS_H
#define _DESC_DEFS_H

#if 0
#define BIG_ENDIAN

struct zsDmaDesc
{
#ifdef BIG_ENDIAN

    volatile u16_t      ctrl;       // Descriptor control
    volatile u16_t      status;     // Descriptor status

    volatile u16_t      totalLen;   // Total length
    volatile u16_t      dataSize;   // Data size

#else
    volatile u16_t      status;     // Descriptor status
    volatile u16_t      ctrl;       // Descriptor control
    volatile u16_t      dataSize;   // Data size
    volatile u16_t      totalLen;   // Total length
#endif
    struct zsDmaDesc*   lastAddr;   // Last address of this chain
    volatile u32_t      dataAddr;   // Data buffer address
    struct zsDmaDesc*   nextAddr;   // Next TD address
};
#endif

/* Tx5 Dn Rx Up Int */
#if 0
#define ZM_TERMINATOR_NUMBER_B  8

#if ZM_BAR_AUTO_BA == 1
#define ZM_TERMINATOR_NUMBER_BAR 	1
#else
#define ZM_TERMINATOR_NUMBER_BAR 	0
#endif

#if ZM_INT_USE_EP2 == 1
#define ZM_TERMINATOR_NUMBER_INT 	1
#else
#define ZM_TERMINATOR_NUMBER_INT 	0
#endif

#define ZM_TX_DELAY_DESC_NUM	16
#define ZM_TERMINATOR_NUMBER (8 + ZM_TERMINATOR_NUMBER_BAR + \
                                  ZM_TERMINATOR_NUMBER_INT + \
							      ZM_TX_DELAY_DESC_NUM)


#define ZM_BLOCK_SIZE           (256+64)
#define ZM_DESCRIPTOR_SIZE      (sizeof(struct zsDmaDesc))
#endif

//#define ZM_FRAME_MEMORY_BASE    0x100000
#if 0
#if 1
/* 64k */
//#define ZM_FRAME_MEMROY_SIZE    0xf000
/* 96k */
//#define ZM_FRAME_MEMROY_SIZE    0x17000

#else
/* fake phy */
/* 128k / 96k */
#define ZM_FRAME_MEMROY_SIZE    (ZM_BLOCK_SIZE+ZM_DESCRIPTOR_SIZE)*(160+60) + \
                                (ZM_DESCRIPTOR_SIZE*ZM_TERMINATOR_NUMBER)+64
#endif

#define ZM_BLOCK_NUMBER         ((ZM_FRAME_MEMROY_SIZE-(ZM_DESCRIPTOR_SIZE* \
                                ZM_TERMINATOR_NUMBER)-64)/(ZM_BLOCK_SIZE \
                                +ZM_DESCRIPTOR_SIZE))
#define ZM_DESC_NUMBER          (ZM_BLOCK_NUMBER + ZM_TERMINATOR_NUMBER)

#define ZM_DESCRIPTOR_BASE		ZM_FRAME_MEMORY_BASE
#define ZM_BLOCK_BUFFER_BASE	(((((ZM_BLOCK_NUMBER+ZM_TERMINATOR_NUMBER) \
                                *ZM_DESCRIPTOR_SIZE) >> 6) << 6) + 0x40 \
                                + ZM_FRAME_MEMORY_BASE)

#define ZM_DOWN_BLOCK_RATIO     2
#define ZM_RX_BLOCK_RATIO       1
/* Tx 16*2 = 32 packets => 32*(5*320) */
#define ZM_TX_BLOCK_NUMBER      ZM_BLOCK_NUMBER * ZM_DOWN_BLOCK_RATIO / \
                                (ZM_RX_BLOCK_RATIO + ZM_DOWN_BLOCK_RATIO)
#define ZM_RX_BLOCK_NUMBER      ZM_BLOCK_NUMBER-ZM_TX_BLOCK_NUMBER
                                //ZM_BLOCK_NUMBER * ZM_RX_BLOCK_RATIO / \
                                //(ZM_RX_BLOCK_RATIO + ZM_DOWN_BLOCK_RATIO)


#define ZM_TX_DELAY_DESC_BASE	ZM_FRAME_MEMORY_BASE + ZM_DESCRIPTOR_SIZE*(ZM_TERMINATOR_NUMBER-ZM_TX_DELAY_DESC_NUM)
#endif

/* Erro code */
#define ZM_ERR_FS_BIT           1
#define ZM_ERR_LS_BIT           2
#define ZM_ERR_OWN_BITS         3
#define ZM_ERR_DATA_SIZE        4
#define ZM_ERR_TOTAL_LEN        5
#define ZM_ERR_DATA             6
#define ZM_ERR_SEQ              7
#define ZM_ERR_LEN              8

/* Status bits definitions */
/* Own bits definitions */
#define ZM_OWN_BITS_MASK        0x3
#define ZM_OWN_BITS_SW          0x0
#define ZM_OWN_BITS_HW          0x1
#define ZM_OWN_BITS_SE          0x2

/* Control bits definitions */
/* First segament bit */
#define ZM_LS_BIT               0x100
/* Last segament bit */
#define ZM_FS_BIT               0x200

#if 0
struct zsDmaQueue
{
    struct zsDmaDesc* head;
    struct zsDmaDesc* terminator;
};
#endif

struct zsDmaQueue;
struct szDmaDesc;

extern struct zsDmaDesc* zfDmaGetPacket(struct zsDmaQueue* q);
extern void zfDmaReclaimPacket(struct zsDmaQueue* q, struct zsDmaDesc* desc);
extern void zfDmaPutPacket(struct zsDmaQueue* q, struct zsDmaDesc* desc);

#endif /* #ifndef _DESC_DEFS_H */
