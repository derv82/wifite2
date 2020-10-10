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
/*  Copyright (c) 2008 Atheros Communications, Inc., All Rights Reserved */
/*                                                                       */
/*  Module Name : romp_api.h     	                                 */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains definition of data structure and interface    */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/

#ifndef _ROMP_API_H_
#define _ROMP_API_H_

#include "dt_defs.h"

/******** hardware API table structure (API descriptions below) *************/

struct romp_api {
	void (*_romp_init)(void);
	BOOLEAN (*_romp_download)(uint16_t );
	BOOLEAN (*_romp_install)(void);
	BOOLEAN (*_romp_decode)(uint32_t );
};

#define _ROMP_MAGIC_ "[PaTcH]"

struct rom_patch_st {
	uint16_t crc16;		// crc filed to maintain the integrity
	uint16_t len;		// length of the patch code
	uint32_t ld_addr;	// load address of the patch code
	uint32_t fun_addr;  // entry address of the patch code
	uint8_t *pfun;		// patch code
};


struct eep_redir_addr {
	uint16_t offset;
	uint16_t size;
};

/************************* EXPORT function ***************************/
uint16_t cal_crc16(uint32_t sz, uint8_t *p);

#endif	// end of _UART_API_H_

