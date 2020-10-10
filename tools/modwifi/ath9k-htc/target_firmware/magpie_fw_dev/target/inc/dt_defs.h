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
/*  Module Name : dt_defs.h                                              */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains the common data structure definition.	     */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/

#ifndef _DT_DEFS_H_
#define _DT_DEFS_H_

#ifndef LOCAL
#define LOCAL	static
#endif

/* data type definition */
typedef unsigned long	uint32_t;
typedef unsigned short	uint16_t;
typedef unsigned char	uint8_t;

typedef signed long     int32_t;
typedef signed short    int16_t;
typedef signed char     int8_t;

typedef uint16_t		BOOLEAN;

// Ray for porting
/* Basic data type */
#define u32_t   unsigned long
#define s32_t   signed long
#define u16_t   unsigned short
#define s16_t   signed short
#define u8_t    unsigned char
#define s8_t    signed char

#define ptrData uint8_t *

/* marco definition */
//#define SIZE_HASH_BUFFER       128

#ifndef TRUE
#define TRUE    (0==0)
#endif

#ifndef FALSE
#define FALSE   (0!=0)
#endif

#ifndef NULL
#define NULL	0x0
#endif

#define BIT0    (1<<0)
#define BIT1    (1<<1)
#define BIT2    (1<<2)
#define BIT3    (1<<3)
#define BIT4    (1<<4)
#define BIT5    (1<<5)
#define BIT6    (1<<6)
#define BIT7    (1<<7)
#define BIT8    (1<<8)
#define BIT9    (1<<9)
#define BIT10   (1<<10)
#define BIT11   (1<<11)
#define BIT12   (1<<12)
#define BIT13   (1<<13)
#define BIT14   (1<<14)
#define BIT15   (1<<15)
#define BIT16    (1<<16)
#define BIT17    (1<<17)
#define BIT18    (1<<18)
#define BIT19    (1<<19)
#define BIT20    (1<<20)
#define BIT21    (1<<21)
#define BIT22    (1<<22)
#define BIT23    (1<<23)
#define BIT24    (1<<24)
#define BIT25    (1<<25)
#define BIT26   (1<<26)
#define BIT27   (1<<27)
#define BIT28   (1<<28)
#define BIT29   (1<<29)
#define BIT30   (1<<30)
#define BIT31   (1<<31)

#endif

