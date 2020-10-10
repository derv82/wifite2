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
#ifndef USB_TYPE_H
#define USB_TYPE_H

#include "dt_defs.h"

/*********************** for Faraday USB controller *******************/
typedef enum
{
    CMD_VOID,                   // No command
    CMD_GET_DESCRIPTOR,         // Get_Descriptor command
    CMD_SET_DESCRIPTOR          // Set_Descriptor command
} CommandType;

typedef enum
{
    ACT_IDLE,
    ACT_DONE,
    ACT_STALL
} Action;

typedef struct Setup_Packet
{
    uint8_t Direction;          /* Data transfer direction: IN, OUT */
    uint8_t Type;               /* Request Type: Standard, Class, Vendor */
    uint8_t Object;             /* Recipient: Device, Interface, Endpoint,other */
    uint16_t Request;           /* Refer to Table 9-3 */
    uint16_t Value;
    uint16_t Index;
    uint16_t Length;
} SetupPacket;

#define mBIT(b)                 (1 << (b))
#define mMASK(w)                (mBIT(w) - 1)

#define mWORD_IDX(bsize)        ((bsize) >> 1)
#define mWORD_SIZE(bsize)       (((bsize) + 1) >> 1)

#define mTABLE_WID              mWORD_SIZE
#define mTABLE_IDX              mWORD_IDX
#define mTABLE_LEN              mLOW_BYTE

#define mLOW_MASK(u16)          ((uint8_t) ((u16) & mMASK(8)))
#define mHIGH_MASK(u16)         ((uint8_t) ((u16) & ~mMASK(8)))
#define mLOW2HIGH(u16)          (((uint8_t) (u16)) << 8)

/* (1234) -> 0034 */
//#define mLOW_BYTE(u16)          ((U_8)(u16))
#define mLOW_BYTE(u16)          mLOW_MASK(u16)
/* (1234) -> 0012 */
#define mHIGH_BYTE(u16)         ((uint8_t) (((uint16_t) (u16)) >> 8))

#define mGET_REG1(var0, reg0)       { var0 = reg0; }

/* (1234, 5678) -> 7834 */
#define m2BYTE(ch1L, ch2H)      (mLOW_MASK(ch1L) | mLOW2HIGH(ch2H))

#define mREAD_WORD(var0, reg0, reg1)    \
    { var0 = reg0; var0 += mLOW2HIGH(reg1); }

#endif
