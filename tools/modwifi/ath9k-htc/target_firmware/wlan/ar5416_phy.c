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

#include "ah.h"
#include "ah_internal.h"
#include "ar5416.h"

#ifdef MAGPIE_MERLIN

#define	OFDM	IEEE80211_T_OFDM
#define	CCK	IEEE80211_T_CCK
#define	TURBO	IEEE80211_T_TURBO
#define	XR	ATHEROS_T_XR
#define HT      IEEE80211_T_HT

HAL_RATE_TABLE ar5416_11a_table = {
	8,  /* number of rates */
	{ 0 },
	{
		/*                                                  short            ctrl  */
		/*                valid                 rateCode Preamble  dot11Rate Rate */
		/*   6 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,   6000,     0x0b,    0x00, (0x80|12),   0 },
		/*   9 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,   9000,     0x0f,    0x00,        18,   0 },
		/*  12 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  12000,     0x0a,    0x00, (0x80|24),   2 },
		/*  18 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  18000,     0x0e,    0x00,        36,   2 },
		/*  24 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  24000,     0x09,    0x00, (0x80|48),   4 },
		/*  36 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  36000,     0x0d,    0x00,        72,   4 },
		/*  48 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  48000,     0x08,    0x00,        96,   4 },
		/*  54 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  54000,     0x0c,    0x00,       108,   4 }
	},
};

HAL_RATE_TABLE ar5416_11b_table = {
	4,  /* number of rates */
	{ 0 },
	{
		/*                                                 short            ctrl  */
		/*                valid                rateCode Preamble  dot11Rate Rate */
		/*   1 Mb */ {  AH_TRUE,  CCK, 60, 60, 60,  1000,    0x1b,    0x00, (0x80| 2),   0 },
		/*   2 Mb */ {  AH_TRUE,  CCK, 60, 60, 60,  2000,    0x1a,    0x04, (0x80| 4),   1 },
		/* 5.5 Mb */ {  AH_TRUE,  CCK, 60, 60, 60,  5500,    0x19,    0x04, (0x80|11),   1 },
		/*  11 Mb */ {  AH_TRUE,  CCK, 60, 60, 60, 11000,    0x18,    0x04, (0x80|22),   1 }
	},
};

HAL_RATE_TABLE ar5416_11g_table = {
	12,  /* number of rates */
	{ 0 },
	{
	/*                                                 short            ctrl  */
	/*                valid                rateCode Preamble  dot11Rate Rate */
		/*   1 Mb */ {  AH_TRUE, CCK,  60,  60,  60, 1000,    0x1b,    0x00, (0x80| 2),   0 },
		/*   2 Mb */ {  AH_TRUE, CCK,  60,  60,  60, 2000,    0x1a,    0x04, (0x80| 4),   1 },
		/* 5.5 Mb */ {  AH_TRUE, CCK,  60,  60,  60, 5500,    0x19,    0x04, (0x80|11),   2 },
		/*  11 Mb */ {  AH_TRUE, CCK,  60,  60,  60, 11000,   0x18,    0x04, (0x80|22),   3 },
		/* Hardware workaround - remove rates 6, 9 from rate ctrl */
		/*   6 Mb */ { AH_FALSE, OFDM, 60,  60, 60,  6000,    0x0b,    0x00,        12,   4 },
		/*   9 Mb */ { AH_FALSE, OFDM, 60,  60, 60,  9000,    0x0f,    0x00,        18,   4 },
		/*  12 Mb */ {  AH_TRUE, OFDM, 60,  60, 60, 12000,    0x0a,    0x00,        24,   6 },
		/*  18 Mb */ {  AH_TRUE, OFDM, 60,  60, 60, 18000,    0x0e,    0x00,        36,   6 },
		/*  24 Mb */ {  AH_TRUE, OFDM, 60,  60, 60, 24000,    0x09,    0x00,        48,   8 },
		/*  36 Mb */ {  AH_TRUE, OFDM, 60,  60, 60, 36000,    0x0d,    0x00,        72,   8 },
		/*  48 Mb */ {  AH_TRUE, OFDM, 60,  60, 60, 48000,    0x08,    0x00,        96,   8 },
		/*  54 Mb */ {  AH_TRUE, OFDM, 60,  60, 60, 54000,    0x0c,    0x00,       108,   8 }
	},
};

HAL_RATE_TABLE ar5416_11ng_table = {

	28,  /* number of rates */
	{ -1 },
	{
		/*                                                 short            ctrl  */
		/*                valid                rateCode Preamble  dot11Rate Rate */
		/*   1 Mb */ {  AH_TRUE, CCK,  60, 60, 60,  1000,    0x1b,    0x00, (0x80| 2),   0 },
		/*   2 Mb */ {  AH_TRUE, CCK,  60, 60, 60,   2000,    0x1a,    0x04, (0x80| 4),   1 },
		/* 5.5 Mb */ {  AH_TRUE, CCK,  60, 60, 60,   5500,    0x19,    0x04, (0x80|11),   2 },
		/*  11 Mb */ {  AH_TRUE, CCK,  60, 60, 60,  11000,    0x18,    0x04, (0x80|22),   3 },
		/* Hardware workaround - remove rates 6, 9 from rate ctrl */
		/*   6 Mb */ { AH_FALSE, OFDM, 60, 60, 60,  6000,    0x0b,    0x00,        12,   4 },
		/*   9 Mb */ { AH_FALSE, OFDM, 60, 60, 60,  9000,    0x0f,    0x00,        18,   4 },
		/*  12 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  12000,    0x0a,    0x00,        24,   6 },
		/*  18 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 18000,    0x0e,    0x00,        36,   6 },
		/*  24 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  24000,    0x09,    0x00,        48,   8 },
		/*  36 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  36000,    0x0d,    0x00,        72,   8 },
		/*  48 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  48000,    0x08,    0x00,        96,   8 },
		/*  54 Mb */ {  AH_TRUE, OFDM, 60, 60, 60,  54000,    0x0c,    0x00,       108,   8 },
		/* 6.5 Mb */ {  AH_TRUE, HT,   60,60, 60,   6500,    0x80,    0x00,         0,   4 },
		/*  13 Mb */ {  AH_TRUE, HT,   60, 60, 60,  13000,   0x81,    0x00,         1,   6 },
		/*19.5 Mb */ {  AH_TRUE, HT,   60,60, 60,   19500,  0x82,    0x00,         2,   6 },
		/*  26 Mb */ {  AH_TRUE, HT,   60, 60, 60,  26000,  0x83,    0x00,         3,   8 },
		/*  39 Mb */ {  AH_TRUE, HT,   60, 60, 60,  39000,  0x84,    0x00,         4,   8 },
		/*  52 Mb */ {  AH_TRUE, HT,   60, 60, 60,  52000,  0x85,    0x00,         5,   8 },
		/*58.5 Mb */ {  AH_TRUE, HT,   60,60,60,  58500,  0x86,    0x00,         6,   8 },
		/*  65 Mb */ {  AH_TRUE, HT,   60, 60, 60,  65000,  0x87,    0x00,         7,   8 },
		/*  13 Mb */ {  AH_TRUE, HT,   60, 60, 60,  13000,  0x88,    0x00,         8,   4 },
		/*  26 Mb */ {  AH_TRUE, HT,   60, 60, 60,   26000,  0x89,    0x00,         9,   6 },
		/*  39 Mb */ {  AH_TRUE, HT,   60, 60, 60,   39000,  0x8a,    0x00,        10,   6 },
		/*  52 Mb */ {  AH_TRUE, HT,   60, 60, 60,   52000,  0x8b,    0x00,        11,   8 },
		/*  78 Mb */ {  AH_TRUE, HT,   60, 60, 60,   78000,  0x8c,    0x00,        12,   8 },
		/* 104 Mb */ {  AH_TRUE, HT,   60, 60, 60,  104000,  0x8d,    0x00,        13,   8 },
		/* 117 Mb */ {  AH_TRUE, HT,   60, 60, 60,  117000,  0x8e,    0x00,        14,   8 },
		/* 130 Mb */ {  AH_TRUE, HT,   60, 60, 60,  130000,  0x8f,    0x00,        15,   8 },
	},
};

HAL_RATE_TABLE ar5416_11na_table = {

	24,  /* number of rates */
	{ -1 },
	{
		/*                                                 short            ctrl  */
		/*                valid                rateCode Preamble  dot11Rate Rate */
		/*   6 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 6000,    0x0b,    0x00, (0x80|12),   0 },
		/*   9 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 9000,    0x0f,    0x00,        18,   0 },
		/*  12 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 12000,    0x0a,    0x00, (0x80|24),   2 },
		/*  18 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 18000,    0x0e,    0x00,        36,   2 },
		/*  24 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 24000,    0x09,    0x00, (0x80|48),   4 },
		/*  36 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 36000,    0x0d,    0x00,        72,   4 },
		/*  48 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 48000,    0x08,    0x00,        96,   4 },
		/*  54 Mb */ {  AH_TRUE, OFDM, 60, 60, 60, 54000,    0x0c,    0x00,       108,   4 },
		/* 6.5 Mb */ {  AH_TRUE, HT,   60, 60, 60, 6500,    0x80,    0x00,         0,    0 },
		/*  13 Mb */ {  AH_TRUE, HT,   60, 60, 60, 13000,    0x81,    0x00,         1,   2 },
		/*19.5 Mb */ {  AH_TRUE, HT,   60, 60, 60, 19500,    0x82,    0x00,         2,   2 },
		/*  26 Mb */ {  AH_TRUE, HT,   60, 60, 60, 26000,    0x83,    0x00,         3,   4 },
		/*  39 Mb */ {  AH_TRUE, HT,   60, 60, 60, 39000,    0x84,    0x00,         4,   4 },
		/*  52 Mb */ {  AH_TRUE, HT,   60, 60, 60, 52000,    0x85,    0x00,         5,   4 },
		/*58.5 Mb */ {  AH_TRUE, HT,   60, 60, 60, 58500,    0x86,    0x00,         6,   4 },
		/*  65 Mb */ {  AH_TRUE, HT,   60, 60, 60, 65000,    0x87,    0x00,         7,   4 },
		/*  13 Mb */ {  AH_TRUE, HT,   60, 60, 60, 13000,    0x88,    0x00,         8,   0 },
		/*  26 Mb */ {  AH_TRUE, HT,   60, 60, 60, 26000,    0x89,    0x00,         9,   2 },
		/*  39 Mb */ {  AH_TRUE, HT,   60, 60, 60, 39000,    0x8a,    0x00,        10,   2 },
		/*  52 Mb */ {  AH_TRUE, HT,   60, 60, 60, 52000,    0x8b,    0x00,        11,   4 },
		/*  78 Mb */ {  AH_TRUE, HT,   60, 60, 60, 78000,    0x8c,    0x00,        12,   4 },
		/* 104 Mb */ {  AH_TRUE, HT,   60, 60, 60, 104000,    0x8d,    0x00,       13,   4 },
		/* 117 Mb */ {  AH_TRUE, HT,   60, 60, 60, 117000,    0x8e,    0x00,       14,   4 },
		/* 130 Mb */ {  AH_TRUE, HT,   60, 60, 60, 130000,    0x8f,    0x00,       15,   4 },
	},
};

#undef  OFDM
#undef  CCK
#undef  TURBO
#undef  XR
#undef  HT
#undef  HT_HGI

const HAL_RATE_TABLE *
ar5416GetRateTable(struct ath_hal *ah, a_uint32_t mode)
{
	HAL_RATE_TABLE *rt;
	switch (mode) {
	case HAL_MODE_11A:
		rt = &ar5416_11a_table;
		break;
	case HAL_MODE_11B:
		rt = &ar5416_11b_table;
		break;
	case HAL_MODE_11G:
		rt =  &ar5416_11g_table;
		break;
	case HAL_MODE_11NG:
		rt = &ar5416_11ng_table;
		break;
	case HAL_MODE_11NA:
		rt = &ar5416_11na_table;
		break;
	default:
		return AH_NULL;
	}

	return rt;
}

#else

#define	OFDM	IEEE80211_T_OFDM
#define	CCK	IEEE80211_T_CCK
#define	TURBO	IEEE80211_T_TURBO
#define	XR	ATHEROS_T_XR
#define HT      IEEE80211_T_HT

HAL_RATE_TABLE ar5416_11ng_table = {

	33,  /* number of rates */
	{ -1 },
	{
		/*                                                 short            ctrl  */
		/*                valid                rateCode Preamble  dot11Rate Rate */
		/*[ 0]   1 Mb */ {  AH_TRUE, CCK,     1000,    0x1b,    0x00, (0x80| 2),   0 },
		/*[ 1]   2 Mb */ {  AH_TRUE, CCK,     2000,    0x1a,    0x04, (0x80| 4),   1 },
		/*[ 2] 5.5 Mb */ {  AH_TRUE, CCK,     5500,    0x19,    0x04, (0x80|11),   2 },
		/*[ 3]  11 Mb */ {  AH_TRUE, CCK,    11000,    0x18,    0x04, (0x80|22),   3 },
		/* Hardware workaround - remove rates 6, 9 from rate ctrl */
		/*[ 4]   6 Mb */ { AH_FALSE, OFDM,    6000,    0x0b,    0x00,        12,   4 },
		/*[ 5]   9 Mb */ { AH_FALSE, OFDM,    9000,    0x0f,    0x00,        18,   4 },
		/*[ 6]  12 Mb */ {  AH_TRUE, OFDM,   12000,    0x0a,    0x00,        24,   6 },
		/*[ 7]  18 Mb */ {  AH_TRUE, OFDM,   18000,    0x0e,    0x00,        36,   6 },
		/*[ 8]  24 Mb */ {  AH_TRUE, OFDM,   24000,    0x09,    0x00,        48,   8 },
		/*[ 9]  36 Mb */ {  AH_TRUE, OFDM,   36000,    0x0d,    0x00,        72,   8 },
		/*[10]  48 Mb */ {  AH_TRUE, OFDM,   48000,    0x08,    0x00,        96,   8 },
		/*[11]  54 Mb */ {  AH_TRUE, OFDM,   54000,    0x0c,    0x00,       108,   8 },
		/*[12] 6.5 Mb */ {  AH_TRUE, HT,      6500,    0x80,    0x00,      	  0,   4 },
		/*[13]  13 Mb */ {  AH_TRUE, HT,	 13000,    0x81,    0x00,      	  1,   6 },
		/*[14]19.5 Mb */ {  AH_TRUE, HT,         19500,    0x82,    0x00,         2,   6 },
		/*[15]  26 Mb */ {  AH_TRUE, HT,  	 26000,    0x83,    0x00,         3,   8 },
		/*[16]  39 Mb */ {  AH_TRUE, HT,  	 39000,    0x84,    0x00,         4,   8 },
		/*[17]  39 Mb */ {  AH_TRUE, HT,  	 39000,    0x84,    0x00,         4,   8 },
		/*[18]  52 Mb */ {  AH_TRUE, HT,   	 52000,    0x85,    0x00,         5,   8 },
		/*[19]  52 Mb */ {  AH_TRUE, HT,   	 52000,    0x85,    0x00,         5,   8 },
		/*[20]58.5 Mb */ {  AH_TRUE, HT,  	 58500,    0x86,    0x00,         6,   8 },
		/*[21]58.5 Mb */ {  AH_TRUE, HT,  	 58500,    0x86,    0x00,         6,   8 },
		/*[22]  65 Mb */ {  AH_TRUE, HT,  	 65000,    0x87,    0x00,         7,   8 },
		/*[23]  65 Mb */ {  AH_TRUE, HT,  	 65000,    0x87,    0x00,         7,   8 },
		/*[24]  52 Mb */ {  AH_TRUE, HT,  	 52000,    0x8b,    0x00,        11,   8 },
		/*[25]  78 Mb */ {  AH_TRUE, HT,  	 78000,    0x8c,    0x00,        12,   8 },
		/*[26]  78 Mb */ {  AH_TRUE, HT,  	 78000,    0x8c,    0x00,        12,   8 },
		/*[27] 104 Mb */ {  AH_TRUE, HT, 	104000,    0x8d,    0x00,        13,   8 },
		/*[28] 104 Mb */ {  AH_TRUE, HT, 	104000,    0x8d,    0x00,        13,   8 },
		/*[29] 117 Mb */ {  AH_TRUE, HT, 	117000,    0x8e,    0x00,        14,   8 },
		/*[30] 117 Mb */ {  AH_TRUE, HT, 	117000,    0x8e,    0x00,        14,   8 },
		/*[31] 130 Mb */ {  AH_TRUE, HT, 	130000,    0x8f,    0x00,        15,   8 },
		/*[32] 130 Mb */ {  AH_TRUE, HT, 	130000,    0x8f,    0x00,        15,   8 },
	},
};

#ifdef ATH_SUPPORT_A_MODE

HAL_RATE_TABLE ar5416_11na_table = {

	28,  /* number of rates */
	{ -1 },
	{
		/*                                                 short            ctrl  */
		/*                valid                rateCode Preamble  dot11Rate Rate */
		/*[ 0]   6 Mb */ {  AH_TRUE, OFDM,    6000,    0x0b,    0x00, (0x80|12),   0 },
		/*[ 1]   9 Mb */ {  AH_TRUE, OFDM,    9000,    0x0f,    0x00,        18,   0 },
		/*[ 2]  12 Mb */ {  AH_TRUE, OFDM,   12000,    0x0a,    0x00, (0x80|24),   2 },
		/*[ 3]  18 Mb */ {  AH_TRUE, OFDM,   18000,    0x0e,    0x00,        36,   2 },
		/*[ 4]  24 Mb */ {  AH_TRUE, OFDM,   24000,    0x09,    0x00, (0x80|48),   4 },
		/*[ 5]  36 Mb */ {  AH_TRUE, OFDM,   36000,    0x0d,    0x00,        72,   4 },
		/*[ 6]  48 Mb */ {  AH_TRUE, OFDM,   48000,    0x08,    0x00,        96,   4 },
		/*[ 7]  54 Mb */ {  AH_TRUE, OFDM,   54000,    0x0c,    0x00,       108,   4 },
		/*[ 8] 6.5 Mb */ {  AH_TRUE, HT,      6500,    0x80,    0x00,         0,   0 },
		/*[ 9]  13 Mb */ {  AH_TRUE, HT,  	 13000,    0x81,    0x00,         1,   2 },
		/*[10]19.5 Mb */ {  AH_TRUE, HT,         19500,    0x82,    0x00,         2,   2 },
		/*[11]  26 Mb */ {  AH_TRUE, HT,  	 26000,    0x83,    0x00,         3,   4 },
		/*[12]  39 Mb */ {  AH_TRUE, HT,  	 39000,    0x84,    0x00,         4,   4 },
		/*[13]  39 Mb */ {  AH_TRUE, HT,  	 39000,    0x84,    0x00,         4,   4 },
		/*[14]  52 Mb */ {  AH_TRUE, HT,   	 52000,    0x85,    0x00,         5,   4 },
		/*[15]  52 Mb */ {  AH_TRUE, HT,   	 52000,    0x85,    0x00,         5,   4 },
		/*[16]58.5 Mb */ {  AH_TRUE, HT,  	 58500,    0x86,    0x00,         6,   4 },
		/*[17]58.5 Mb */ {  AH_TRUE, HT,  	 58500,    0x86,    0x00,         6,   4 },
		/*[18]  65 Mb */ {  AH_TRUE, HT,  	 65000,    0x87,    0x00,         7,   4 },
		/*[19]  65 Mb */ {  AH_TRUE, HT,  	 65000,    0x87,    0x00,         7,   4 },
		/*[20]  52 Mb */ {  AH_TRUE, HT,  	 52000,    0x8b,    0x00,        11,   4 },
		/*[21]  78 Mb */ {  AH_TRUE, HT,  	 78000,    0x8c,    0x00,        12,   4 },
		/*[22]  78 Mb */ {  AH_TRUE, HT,  	 78000,    0x8c,    0x00,        12,   4 },
		/*[23] 104 Mb */ {  AH_TRUE, HT, 	104000,    0x8d,    0x00,        13,   4 },
		/*[24] 104 Mb */ {  AH_TRUE, HT, 	104000,    0x8d,    0x00,        13,   4 },
		/*[25] 117 Mb */ {  AH_TRUE, HT, 	117000,    0x8e,    0x00,        14,   4 },
		/*[26] 117 Mb */ {  AH_TRUE, HT, 	117000,    0x8e,    0x00,        14,   4 },
		/*[27] 130 Mb */ {  AH_TRUE, HT, 	130000,    0x8f,    0x00,        15,   4 },
	},
};
#endif

#undef	OFDM
#undef	CCK
#undef	TURBO
#undef	XR
#undef	HT
#undef	HT_HGI

const HAL_RATE_TABLE *
ar5416GetRateTable(struct ath_hal *ah, a_uint32_t mode)
{
	HAL_RATE_TABLE *rt;
	switch (mode) {
	case HAL_MODE_11NG:
		rt = &ar5416_11ng_table;
		break;
#ifdef ATH_SUPPORT_A_MODE
	case HAL_MODE_11NA:
		rt = &ar5416_11na_table;
		break;
#endif
	default:
		return AH_NULL;
	}

	return rt;
}

#endif
