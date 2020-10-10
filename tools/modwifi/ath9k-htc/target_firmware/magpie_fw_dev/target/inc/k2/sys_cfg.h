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
/*  Module Name : sys_cfg.h                                              */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains definition of platform and sysmte config   .  */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/

#ifndef _SYS_CFG_H_
#define _SYS_CFG_H_

/************************** FPGA version **************************/
#define MAGPIE_FPGA_RAM_256K         0

/************************** ROM DEFINE ***************************/

#if defined(_ROM_)
#include "rom_cfg.h"

#if MAGPIE_FPGA_RAM_256K == 1 
#undef  MAX_BUF_NUM 
#define MAX_BUF_NUM                100
#endif

#elif defined(_RAM_)

#include "rom_cfg.h"
#include <wlan_cfg.h>

/************************* Resource DEFS ***********************/
#define MAX_DESC_NUM               100

#ifdef RX_SCATTER
#define MAX_BUF_NUM                100
#else
#define MAX_BUF_NUM                60
#endif

#undef 	SYSTEM_MODULE_DBG
#undef  MOVE_PRINT_TO_RAM 
#ifdef _DEBUG_BUILD_
#define SYSTEM_MODULE_DBG               1
#define MOVE_PRINT_TO_RAM               1
#else
#define SYSTEM_MODULE_DBG               0
#define MOVE_PRINT_TO_RAM               1 
#endif
#undef SYSTEM_MODULE_SFLASH
#define SYSTEM_MODULE_SFLASH		    0

/************************* WLAN DEFS ***************************/
#define MAGPIE_ENABLE_WLAN              1
#define MAGPIE_ENABLE_PCIE              0
#define MAGPIE_ENABLE_WLAN_IN_TARGET    0
#define MAGPIE_ENABLE_WLAN_SELF_TX      0
#define MAGPIE_ENABLE_WLAN_RATE_CTRL    1

/****************************** WATCH DOG *******************************/
#define WDT_DEFAULT_TIMEOUT_VALUE   3*ONE_MSEC*1000 // Initial value is 3 seconds, firmware changes it to 65 milliseconds

#endif


#endif /* _SYS_CFG_H_ */
